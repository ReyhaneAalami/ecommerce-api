from collections import defaultdict
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.data.models import (
    User,
    Vendor,
    Product,
    Order,
    VendorOrder,
    OrderItem,
    IdempotencyRecord,
    Wallet,
    WalletTransaction,
)
from src.repositories.order_repository import OrderRepository
from src.repositories.cart_repository import CartRepository
from src.repositories.wallet_repository import WalletRepository
from src.schemas.order import OrderCreate


class IdempotencyConflictError(ValueError):
    """The same idempotency key was reused for a different request."""


class OrderService:

    @staticmethod
    def _request_hash(items: list) -> str:
        normalized = {}
        for item in items:
            product_id = int(item.product_id)
            quantity = int(item.quantity)
            normalized[product_id] = normalized.get(product_id, 0) + quantity

        payload = [
            {"product_id": product_id, "quantity": normalized[product_id]}
            for product_id in sorted(normalized)
        ]
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _claim_idempotency(
        db: Session,
        customer_id: int,
        operation: str,
        key: str | None,
        items: list,
    ):
        if not key:
            return None, None

        request_hash = OrderService._request_hash(items)

        statement = (
            pg_insert(IdempotencyRecord)
            .values(
                user_id=customer_id,
                operation=operation,
                idempotency_key=key,
                request_hash=request_hash,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    "user_id",
                    "operation",
                    "idempotency_key",
                ]
            )
        )
        db.execute(statement)

        record = db.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.user_id == customer_id,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.idempotency_key == key,
            )
            .with_for_update()
        )

        if record is None:
            raise RuntimeError("Could not reserve idempotency key.")

        if record.request_hash != request_hash:
            raise IdempotencyConflictError(
                "Idempotency key was already used with different request data."
            )

        if record.order_id is not None:
            existing_order = OrderRepository.get_by_id(db, record.order_id)
            if existing_order is None:
                raise RuntimeError("Idempotency record points to a missing order.")
            return record, existing_order

        return record, None

    @staticmethod
    def _create_order_from_items(
        db: Session,
        customer_id: int,
        items: list,
        cart=None,
        idempotency_record=None,
    ) -> Order:
        try:
            customer = db.scalar(
                select(User).where(
                    User.id == customer_id,
                    User.is_active.is_(True),
                )
            )

            if not customer or customer.role != "customer":
                raise ValueError("Customer account is invalid or inactive.")

            if not items:
                raise ValueError("Cannot create an order with an empty cart.")

            quantities = defaultdict(int)
            for item in items:
                quantities[item.product_id] += item.quantity

            product_ids = sorted(quantities)
            products = list(
                db.scalars(
                    select(Product)
                    .where(Product.id.in_(product_ids))
                    .order_by(Product.id)
                    .with_for_update()
                ).all()
            )

            if len(products) != len(product_ids):
                raise ValueError("One or more products were not found.")

            vendor_ids = {product.vendor_id for product in products}
            vendors = list(
                db.scalars(
                    select(Vendor)
                    .where(Vendor.id.in_(vendor_ids))
                    .order_by(Vendor.id)
                ).all()
            )
            vendor_map = {vendor.id: vendor for vendor in vendors}

            grouped_items = defaultdict(list)
            order_total = 0

            for product in products:
                quantity = quantities[product.id]
                vendor = vendor_map.get(product.vendor_id)

                if not product.is_active:
                    raise ValueError(f"Product {product.name} is inactive.")
                if product.stock_quantity < quantity:
                    raise ValueError(
                        f"Insufficient stock for product {product.name}."
                    )
                if not vendor or not vendor.is_active:
                    raise ValueError("One or more vendors are inactive.")
                if vendor.status != "approved":
                    raise ValueError("One or more vendors are not approved.")

                grouped_items[product.vendor_id].append((product, quantity))
                order_total += product.price * quantity

            if order_total <= 0:
                raise ValueError("Invalid order total.")

            wallet = WalletRepository.get_by_user_id_for_update(
                db,
                customer_id,
            )
            if wallet is None:
                raise ValueError("Customer wallet not found.")
            if wallet.balance < order_total:
                raise ValueError("Insufficient wallet balance.")

            order = Order(
                customer_id=customer_id,
                status="pending",
                payment_status="paid",
                total_amount=order_total,
            )
            db.add(order)
            db.flush()

            if idempotency_record is not None:
                idempotency_record.order_id = order.id

            new_balance = wallet.balance - order_total
            WalletRepository.update_balance(db, wallet, new_balance)
            WalletRepository.create_transaction(
                db,
                {
                    "wallet_id": wallet.id,
                    "transaction_type": "order_payment",
                    "amount": order_total,
                    "balance_after": new_balance,
                    "reference_type": "order",
                    "reference_id": order.id,
                    "description": f"Payment for order #{order.id}",
                },
            )

            for vendor_id, vendor_items in grouped_items.items():
                vendor = vendor_map[vendor_id]
                vendor_order = VendorOrder(
                    order_id=order.id,
                    vendor_id=vendor_id,
                    vendor_name=vendor.store_name,
                    status="pending",
                    subtotal=0,
                    shipping_fee=0,
                    total_amount=0,
                )
                db.add(vendor_order)
                db.flush()

                vendor_subtotal = 0
                for product, quantity in vendor_items:
                    subtotal = product.price * quantity
                    db.add(
                        OrderItem(
                            vendor_order_id=vendor_order.id,
                            product_id=product.id,
                            product_name=product.name,
                            sku=product.sku,
                            quantity=quantity,
                            unit_price=product.price,
                            subtotal=subtotal,
                        )
                    )
                    product.stock_quantity -= quantity
                    vendor_subtotal += subtotal

                vendor_order.subtotal = vendor_subtotal
                vendor_order.total_amount = (
                    vendor_subtotal + vendor_order.shipping_fee
                )

            if cart is not None:
                CartRepository.clear(db, cart)

            db.commit()
            return OrderRepository.get_by_id(db, order.id)

        except ValueError:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create_order(
        db: Session,
        customer_id: int,
        order_data: OrderCreate,
        idempotency_key: str | None = None,
    ) -> Order:
        try:
            record, existing = OrderService._claim_idempotency(
                db,
                customer_id,
                "create_order",
                idempotency_key,
                order_data.items,
            )
            if existing is not None:
                return existing

            return OrderService._create_order_from_items(
                db=db,
                customer_id=customer_id,
                items=order_data.items,
                idempotency_record=record,
            )
        except ValueError:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def checkout(
        db: Session,
        customer_id: int,
        idempotency_key: str | None = None,
    ) -> Order:
        try:
            cart = CartRepository.get_by_customer_id_for_update(
                db,
                customer_id,
            )

            # A successful prior checkout clears the cart. On retry with the
            # same key, return the original order rather than reporting empty.
            if not cart or not cart.items:
                if idempotency_key:
                    record = db.scalar(
                        select(IdempotencyRecord).where(
                            IdempotencyRecord.user_id == customer_id,
                            IdempotencyRecord.operation == "checkout",
                            IdempotencyRecord.idempotency_key == idempotency_key,
                        ).with_for_update()
                    )
                    if record and record.order_id:
                        return OrderRepository.get_by_id(db, record.order_id)
                raise ValueError("Your cart is empty.")

            record, existing = OrderService._claim_idempotency(
                db,
                customer_id,
                "checkout",
                idempotency_key,
                cart.items,
            )
            if existing is not None:
                return existing

            return OrderService._create_order_from_items(
                db=db,
                customer_id=customer_id,
                items=cart.items,
                cart=cart,
                idempotency_record=record,
            )
        except ValueError:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def cancel_order(
        db: Session,
        order_id: int,
        customer_id: int,
    ) -> Order:
        try:
            order = db.scalar(
                select(Order)
                .where(
                    Order.id == order_id,
                    Order.customer_id == customer_id,
                )
                .with_for_update()
            )
            if order is None:
                raise ValueError("Order not found.")

            if order.status == "cancelled" and order.payment_status == "refunded":
                return OrderRepository.get_by_id(db, order.id)
            if order.status == "cancelled" or order.payment_status == "refunded":
                raise ValueError("Order cancellation state is inconsistent.")
            if order.payment_status != "paid":
                raise ValueError("Only paid orders can be cancelled.")

            vendor_orders = list(
                db.scalars(
                    select(VendorOrder)
                    .where(VendorOrder.order_id == order.id)
                    .order_by(VendorOrder.id)
                    .with_for_update()
                ).all()
            )
            if not vendor_orders:
                raise ValueError("Order has no vendor suborders.")
            if order.status != "pending" or any(
                vendor_order.status != "pending"
                for vendor_order in vendor_orders
            ):
                raise ValueError(
                    "This order cannot be cancelled directly because vendor processing has started."
                )

            vendor_order_ids = [item.id for item in vendor_orders]
            order_items = list(
                db.scalars(
                    select(OrderItem)
                    .where(OrderItem.vendor_order_id.in_(vendor_order_ids))
                    .order_by(OrderItem.product_id, OrderItem.id)
                ).all()
            )
            if not order_items:
                raise ValueError("Order has no items.")

            product_ids = sorted({item.product_id for item in order_items})
            products = list(
                db.scalars(
                    select(Product)
                    .where(Product.id.in_(product_ids))
                    .order_by(Product.id)
                    .with_for_update()
                ).all()
            )
            product_map = {product.id: product for product in products}
            if len(product_map) != len(product_ids):
                raise ValueError("One or more products could not be found.")

            wallet = WalletRepository.get_by_user_id_for_update(db, customer_id)
            if wallet is None:
                raise ValueError("Customer wallet not found.")
            if order.total_amount <= 0:
                raise ValueError("Invalid order refund amount.")

            for item in order_items:
                product_map[item.product_id].stock_quantity += item.quantity

            new_balance = wallet.balance + order.total_amount
            WalletRepository.update_balance(db, wallet, new_balance)
            WalletRepository.create_transaction(
                db,
                {
                    "wallet_id": wallet.id,
                    "transaction_type": "refund",
                    "amount": order.total_amount,
                    "balance_after": new_balance,
                    "reference_type": "order",
                    "reference_id": order.id,
                    "description": f"Refund for cancelled order #{order.id}",
                },
            )

            for vendor_order in vendor_orders:
                vendor_order.status = "cancelled"

            order.status = "cancelled"
            order.payment_status = "refunded"
            db.commit()
            return OrderRepository.get_by_id(db, order.id)

        except ValueError:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_customer_order(db: Session, order_id: int, customer_id: int):
        order = OrderRepository.get_by_id_for_customer(db, order_id, customer_id)
        if not order:
            raise ValueError("Order not found.")
        return order

    @staticmethod
    def get_customer_orders(db: Session, customer_id: int, skip: int = 0, limit: int = 20):
        if skip < 0 or limit < 1 or limit > 100:
            raise ValueError("Invalid pagination parameters.")
        return OrderRepository.get_customer_orders(db, customer_id, skip, limit)

    @staticmethod
    def get_vendor_orders(db: Session, vendor_id: int, skip: int = 0, limit: int = 20):
        if skip < 0 or limit < 1 or limit > 100:
            raise ValueError("Invalid pagination parameters.")
        return OrderRepository.get_vendor_orders(db, vendor_id, skip, limit)

    @staticmethod
    def get_vendor_order(db: Session, vendor_order_id: int, vendor_id: int):
        vendor_order = OrderRepository.get_vendor_order(db, vendor_order_id, vendor_id)
        if not vendor_order:
            raise ValueError("Suborder not found or does not belong to this vendor.")
        return vendor_order

    @staticmethod
    def update_vendor_order_status(
        db: Session,
        vendor_order_id: int,
        vendor_id: int,
        new_status: str,
    ):
        allowed_transitions = {
            "pending": "processing",
            "processing": "shipped",
            "shipped": "delivered",
        }

        try:
            initial = OrderRepository.get_vendor_order(
                db, vendor_order_id, vendor_id
            )
            if initial is None:
                raise ValueError(
                    "Suborder not found or does not belong to this vendor."
                )

            parent_order = db.scalar(
                select(Order)
                .where(Order.id == initial.order_id)
                .with_for_update()
            )
            if parent_order is None:
                raise ValueError("Parent order not found.")
            if parent_order.status == "cancelled" or parent_order.payment_status != "paid":
                raise ValueError("This order cannot be processed.")

            vendor_order = OrderRepository.get_vendor_order_for_update(
                db, vendor_order_id, vendor_id
            )
            if vendor_order is None:
                raise ValueError(
                    "Suborder not found or does not belong to this vendor."
                )

            expected = allowed_transitions.get(vendor_order.status)
            if expected is None:
                raise ValueError("This order is already in its final status.")
            if new_status != expected:
                raise ValueError(
                    f"Invalid status transition. Current status: {vendor_order.status}. "
                    f"Next allowed status: {expected}."
                )

            child_status_rows = list(
                db.execute(
                    select(VendorOrder.id, VendorOrder.status).where(
                        VendorOrder.order_id == parent_order.id
                    )
                ).all()
            )

            child_statuses = [
                new_status if child_id == vendor_order.id else status
                for child_id, status in child_status_rows
            ]

            priority = {
                "pending": 1,
                "processing": 2,
                "shipped": 3,
                "delivered": 4,
            }

            if not child_statuses or any(
                item not in priority for item in child_statuses
            ):
                raise ValueError(
                    "Order has missing or unsupported suborder statuses."
                )

            vendor_order.status = new_status
            parent_order.status = min(
                child_statuses,
                key=lambda item: priority[item],
            )

            # Vendor earnings become withdrawable only after this suborder is
            # marked delivered. The unique ledger index is the final exactly-once
            # guard; the wallet row lock serializes concurrent delivery callbacks.
            if new_status == "delivered":
                vendor = db.scalar(
                    select(Vendor).where(Vendor.id == vendor_id)
                )
                if vendor is None:
                    raise ValueError("Vendor not found.")
                vendor_wallet = db.scalar(
                    select(Wallet)
                    .where(Wallet.user_id == vendor.user_id)
                    .with_for_update()
                )
                if vendor_wallet is None:
                    raise ValueError("Vendor wallet not found.")
                existing_earning = db.scalar(
                    select(WalletTransaction.id).where(
                        WalletTransaction.transaction_type == "vendor_earning",
                        WalletTransaction.reference_type == "vendor_order",
                        WalletTransaction.reference_id == vendor_order.id,
                    )
                )
                if existing_earning is None:
                    vendor_wallet.balance += vendor_order.subtotal
                    db.add(
                        WalletTransaction(
                            wallet_id=vendor_wallet.id,
                            transaction_type="vendor_earning",
                            amount=vendor_order.subtotal,
                            balance_after=vendor_wallet.balance,
                            reference_type="vendor_order",
                            reference_id=vendor_order.id,
                            description=f"Earnings for delivered vendor order #{vendor_order.id}",
                        )
                    )
            db.commit()
            return OrderRepository.get_vendor_order(db, vendor_order_id, vendor_id)

        except ValueError:
            raise
        except Exception:
            db.rollback()
            raise
