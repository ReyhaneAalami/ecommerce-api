
from collections import defaultdict
from decimal import Decimal

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
                raise ValueError("Cannot create an order with an empty cart.")

            quantities = defaultdict(int)

            for item in items:
                quantities[item.product_id] += item.quantity

            product_ids = list(quantities.keys())

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

            order = Order(
                customer_id=customer_id,
                status="pending",
                total_amount=Decimal("0.00"),
            )

            db.add(order)
            db.flush()

            order_total = Decimal("0.00")

            for vendor_id, vendor_items in grouped_items.items():
                vendor = vendor_map[vendor_id]

                vendor_order = VendorOrder(
                    order_id=order.id,
                    vendor_id=vendor_id,
                    vendor_name=vendor.store_name,
                    status="pending",
                    subtotal=Decimal("0.00"),
                    shipping_fee=Decimal("0.00"),
                    total_amount=Decimal("0.00"),
                )

                db.add(vendor_order)
                db.flush()

                vendor_subtotal = Decimal("0.00")

                for product, quantity in vendor_items:
                    unit_price = Decimal(product.price)
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

                order_total += vendor_order.total_amount

            order.total_amount = order_total

            # Clear the cart only after all order operations succeeded.
            if cart is not None:
                CartRepository.clear(db, cart)

            db.commit()

            return OrderRepository.get_by_id(
                db,
                order.id,
            )

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
            vendor_order = OrderRepository.get_vendor_order_for_update(
                db,
                vendor_order_id,
                vendor_id,
            )

            if not vendor_order:
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

            parent_order = db.scalar(
                select(Order)
                .where(Order.id == vendor_order.order_id)
                .with_for_update()
            )

            if parent_order is None:
                raise ValueError("Parent order not found.")

            child_statuses = list(
                db.scalars(
                    select(VendorOrder.status).where(
                        VendorOrder.order_id == parent_order.id
                    )
                ).all()
            )

            if not child_statuses:
                raise ValueError("Order has no vendor suborders.")

            status_priority = {
                "pending": 1,
                "processing": 2,
                "shipped": 3,
                "delivered": 4,
            }

            unknown_statuses = [
                item for item in child_statuses
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
