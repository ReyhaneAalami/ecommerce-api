
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models import (
    User,
    Vendor,
    Product,
    Order,
    VendorOrder,
    OrderItem,
)
from src.repositories.order_repository import OrderRepository
from src.repositories.cart_repository import CartRepository
from src.repositories.wallet_repository import WalletRepository
from src.schemas.order import OrderCreate


class OrderService:

    @staticmethod
    def _create_order_from_items(
        db: Session,
        customer_id: int,
        items: list,
        cart=None,
    ) -> Order:
        try:
            customer = db.scalar(
                select(User).where(
                    User.id == customer_id,
                    User.is_active.is_(True),
                )
            )

            if not customer or customer.role != "customer":
                raise ValueError(
                    "Customer account is invalid or inactive."
                )

            if not items:
                raise ValueError(
                    "Cannot create an order with an empty cart."
                )

            quantities = defaultdict(int)

            for item in items:
                quantities[item.product_id] += item.quantity

            product_ids = sorted(quantities.keys())

            products = list(
                db.scalars(
                    select(Product)
                    .where(Product.id.in_(product_ids))
                    .order_by(Product.id)
                    .with_for_update()
                ).all()
            )

            if len(products) != len(product_ids):
                raise ValueError(
                    "One or more products were not found."
                )

            vendor_ids = {
                product.vendor_id for product in products
            }

            vendors = list(
                db.scalars(
                    select(Vendor).where(
                        Vendor.id.in_(vendor_ids)
                    )
                ).all()
            )

            vendor_map = {
                vendor.id: vendor for vendor in vendors
            }

            grouped_items = defaultdict(list)
            order_total = 0

            for product in products:
                quantity = quantities[product.id]
                vendor = vendor_map.get(product.vendor_id)

                if not product.is_active:
                    raise ValueError(
                        f"Product {product.name} is inactive."
                    )

                if product.stock_quantity < quantity:
                    raise ValueError(
                        f"Insufficient stock for product {product.name}."
                    )

                if not vendor or not vendor.is_active:
                    raise ValueError(
                        "One or more vendors are inactive."
                    )

                if vendor.status != "approved":
                    raise ValueError(
                        "One or more vendors are not approved."
                    )

                grouped_items[product.vendor_id].append(
                    (product, quantity)
                )

                order_total += product.price * quantity

            if order_total <= 0:
                raise ValueError("Invalid order total.")

            # Lock customer's wallet.
            wallet = WalletRepository.get_by_user_id_for_update(
                db,
                customer_id,
            )

            if wallet is None:
                raise ValueError("Customer wallet not found.")

            if wallet.balance < order_total:
                raise ValueError(
                    "Insufficient wallet balance."
                )

            # Create paid order.
            order = Order(
                customer_id=customer_id,
                status="pending",
                payment_status="paid",
                total_amount=order_total,
            )

            db.add(order)
            db.flush()

            # Debit wallet.
            new_balance = wallet.balance - order_total

            WalletRepository.update_balance(
                db,
                wallet,
                new_balance,
            )

            # Record payment transaction.
            WalletRepository.create_transaction(
                db,
                {
                    "wallet_id": wallet.id,
                    "transaction_type": "order_payment",
                    "amount": order_total,
                    "balance_after": new_balance,
                    "reference_type": "order",
                    "reference_id": order.id,
                    "description": (
                        f"Payment for order #{order.id}"
                    ),
                },
            )

            # Create vendor orders and order items.
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
                    unit_price = product.price
                    subtotal = unit_price * quantity

                    order_item = OrderItem(
                        vendor_order_id=vendor_order.id,
                        product_id=product.id,
                        product_name=product.name,
                        sku=product.sku,
                        quantity=quantity,
                        unit_price=unit_price,
                        subtotal=subtotal,
                    )

                    db.add(order_item)

                    product.stock_quantity -= quantity
                    vendor_subtotal += subtotal

                vendor_order.subtotal = vendor_subtotal
                vendor_order.total_amount = (
                    vendor_subtotal + vendor_order.shipping_fee
                )

            # Clear cart after successful order preparation.
            if cart is not None:
                CartRepository.clear(db, cart)

            db.commit()

            return OrderRepository.get_by_id(
                db,
                order.id,
            )

        except ValueError:
            # Validation errors happen before order changes.
            # Do not rollback the caller's existing transaction.
            raise

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create_order(
        db: Session,
        customer_id: int,
        order_data: OrderCreate,
    ) -> Order:
        return OrderService._create_order_from_items(
            db=db,
            customer_id=customer_id,
            items=order_data.items,
        )

    @staticmethod
    def checkout(
        db: Session,
        customer_id: int,
    ) -> Order:
        try:
            cart = CartRepository.get_by_customer_id_for_update(
                db,
                customer_id,
            )

            if not cart or not cart.items:
                raise ValueError("Your cart is empty.")

            return OrderService._create_order_from_items(
                db=db,
                customer_id=customer_id,
                items=cart.items,
                cart=cart,
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
            # Lock customer's order first.
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

            # Idempotent repeated cancellation.
            # A repeated request must not refund money or stock again.
            if (
                order.status == "cancelled"
                and order.payment_status == "refunded"
            ):
                return OrderRepository.get_by_id(
                    db,
                    order.id,
                )

            if (
                order.status == "cancelled"
                or order.payment_status == "refunded"
            ):
                raise ValueError(
                    "Order cancellation state is inconsistent."
                )

            if order.payment_status != "paid":
                raise ValueError(
                    "Only paid orders can be cancelled."
                )

            # Lock vendor orders in deterministic order.
            vendor_orders = list(
                db.scalars(
                    select(VendorOrder)
                    .where(VendorOrder.order_id == order.id)
                    .order_by(VendorOrder.id)
                    .with_for_update()
                ).all()
            )

            if not vendor_orders:
                raise ValueError(
                    "Order has no vendor suborders."
                )

            # Only pending orders can be cancelled directly.
            if order.status != "pending" or any(
                vendor_order.status != "pending"
                for vendor_order in vendor_orders
            ):
                raise ValueError(
                    "This order cannot be cancelled directly "
                    "because vendor processing has started."
                )

            # Get order items.
            vendor_order_ids = [
                vendor_order.id
                for vendor_order in vendor_orders
            ]

            order_items = list(
                db.scalars(
                    select(OrderItem)
                    .where(
                        OrderItem.vendor_order_id.in_(
                            vendor_order_ids
                        )
                    )
                    .order_by(
                        OrderItem.product_id,
                        OrderItem.id,
                    )
                ).all()
            )

            if not order_items:
                raise ValueError("Order has no items.")

            # Lock products in deterministic order.
            product_ids = sorted({
                item.product_id
                for item in order_items
            })

            products = list(
                db.scalars(
                    select(Product)
                    .where(Product.id.in_(product_ids))
                    .order_by(Product.id)
                    .with_for_update()
                ).all()
            )

            product_map = {
                product.id: product
                for product in products
            }

            if len(product_map) != len(product_ids):
                raise ValueError(
                    "One or more products could not be found."
                )

            # Lock customer's wallet.
            wallet = WalletRepository.get_by_user_id_for_update(
                db,
                customer_id,
            )

            if wallet is None:
                raise ValueError(
                    "Customer wallet not found."
                )

            if order.total_amount <= 0:
                raise ValueError(
                    "Invalid order refund amount."
                )

            # Restore stock.
            for item in order_items:
                product_map[item.product_id].stock_quantity += (
                    item.quantity
                )

            # Refund wallet.
            new_balance = wallet.balance + order.total_amount

            WalletRepository.update_balance(
                db,
                wallet,
                new_balance,
            )

            # Record refund transaction.
            WalletRepository.create_transaction(
                db,
                {
                    "wallet_id": wallet.id,
                    "transaction_type": "refund",
                    "amount": order.total_amount,
                    "balance_after": new_balance,
                    "reference_type": "order",
                    "reference_id": order.id,
                    "description": (
                        f"Refund for cancelled order #{order.id}"
                    ),
                },
            )

            # Update vendor order statuses.
            for vendor_order in vendor_orders:
                vendor_order.status = "cancelled"

            # Update parent order statuses.
            order.status = "cancelled"
            order.payment_status = "refunded"

            # Commit all cancellation changes atomically.
            db.commit()

            return OrderRepository.get_by_id(
                db,
                order.id,
            )

        except ValueError:
            # Business validation errors must not rollback
            # the caller's existing transaction.
            raise

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_customer_order(
        db: Session,
        order_id: int,
        customer_id: int,
    ):
        order = OrderRepository.get_by_id_for_customer(
            db,
            order_id,
            customer_id,
        )

        if not order:
            raise ValueError("Order not found.")

        return order

    @staticmethod
    def get_customer_orders(
        db: Session,
        customer_id: int,
        skip: int = 0,
        limit: int = 20,
    ):
        if skip < 0 or limit < 1 or limit > 100:
            raise ValueError("Invalid pagination parameters.")

        return OrderRepository.get_customer_orders(
            db,
            customer_id,
            skip,
            limit,
        )

    @staticmethod
    def get_vendor_orders(
        db: Session,
        vendor_id: int,
        skip: int = 0,
        limit: int = 20,
    ):
        if skip < 0 or limit < 1 or limit > 100:
            raise ValueError("Invalid pagination parameters.")

        return OrderRepository.get_vendor_orders(
            db,
            vendor_id,
            skip,
            limit,
        )

    @staticmethod
    def get_vendor_order(
        db: Session,
        vendor_order_id: int,
        vendor_id: int,
    ):
        vendor_order = OrderRepository.get_vendor_order(
            db,
            vendor_order_id,
            vendor_id,
        )

        if not vendor_order:
            raise ValueError(
                "Suborder not found or does not belong to this vendor."
            )

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
            # Find suborder without locking it first.
            initial_vendor_order = OrderRepository.get_vendor_order(
                db,
                vendor_order_id,
                vendor_id,
            )

            if initial_vendor_order is None:
                raise ValueError(
                    "Suborder not found or does not belong to this vendor."
                )

            # Lock parent order first.
            parent_order = db.scalar(
                select(Order)
                .where(Order.id == initial_vendor_order.order_id)
                .with_for_update()
            )

            if parent_order is None:
                raise ValueError("Parent order not found.")

            if (
                parent_order.status == "cancelled"
                or parent_order.payment_status != "paid"
            ):
                raise ValueError(
                    "This order cannot be processed."
                )

            # Lock vendor order after parent.
            vendor_order = OrderRepository.get_vendor_order_for_update(
                db,
                vendor_order_id,
                vendor_id,
            )

            if vendor_order is None:
                raise ValueError(
                    "Suborder not found or does not belong to this vendor."
                )

            expected_status = allowed_transitions.get(
                vendor_order.status
            )

            if expected_status is None:
                raise ValueError(
                    "This order is already in its final status."
                )

            if new_status != expected_status:
                raise ValueError(
                    f"Invalid status transition. "
                    f"Current status: {vendor_order.status}. "
                    f"Next allowed status: {expected_status}."
                )

            vendor_order.status = new_status
            db.flush()

            child_statuses = list(
                db.scalars(
                    select(VendorOrder.status).where(
                        VendorOrder.order_id == parent_order.id
                    )
                ).all()
            )

            if not child_statuses:
                raise ValueError(
                    "Order has no vendor suborders."
                )

            status_priority = {
                "pending": 1,
                "processing": 2,
                "shipped": 3,
                "delivered": 4,
            }

            unknown_statuses = [
                item
                for item in child_statuses
                if item not in status_priority
            ]

            if unknown_statuses:
                raise ValueError(
                    "One or more suborders have an unsupported status."
                )

            parent_order.status = min(
                child_statuses,
                key=lambda item: status_priority[item],
            )

            db.commit()

            return OrderRepository.get_vendor_order(
                db,
                vendor_order_id,
                vendor_id,
            )

        except Exception:
            db.rollback()
            raise
