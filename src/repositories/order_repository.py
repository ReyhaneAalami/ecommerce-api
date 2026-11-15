
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.data.models import Order, VendorOrder


class OrderRepository:

    @staticmethod
    def create(db: Session, order: Order) -> Order:
        db.add(order)
        db.flush()
        return order

    @staticmethod
    def get_by_id(db: Session, order_id: int) -> Order | None:
        statement = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.vendor_orders)
                .selectinload(VendorOrder.items)
            )
        )
        return db.scalar(statement)

    @staticmethod
    def get_by_id_for_customer(
        db: Session,
        order_id: int,
        customer_id: int,
    ) -> Order | None:
        statement = (
            select(Order)
            .where(
                Order.id == order_id,
                Order.customer_id == customer_id,
            )
            .options(
                selectinload(Order.vendor_orders)
                .selectinload(VendorOrder.items)
            )
        )
        return db.scalar(statement)

    @staticmethod
    def get_customer_orders(
        db: Session,
        customer_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Order]:
        statement = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .options(
                selectinload(Order.vendor_orders)
                .selectinload(VendorOrder.items)
            )
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def get_vendor_orders(
        db: Session,
        vendor_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[VendorOrder]:
        statement = (
            select(VendorOrder)
            .where(VendorOrder.vendor_id == vendor_id)
            .options(
                selectinload(VendorOrder.items)
            )
            .order_by(VendorOrder.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def get_vendor_order(
        db: Session,
        vendor_order_id: int,
        vendor_id: int,
    ) -> VendorOrder | None:
        statement = (
            select(VendorOrder)
            .where(
                VendorOrder.id == vendor_order_id,
                VendorOrder.vendor_id == vendor_id,
            )
            .options(
                selectinload(VendorOrder.items)
            )
        )
        return db.scalar(statement)

    @staticmethod
    def get_vendor_order_for_update(
        db: Session,
        vendor_order_id: int,
        vendor_id: int,
    ) -> VendorOrder | None:
        statement = (
            select(VendorOrder)
            .where(
                VendorOrder.id == vendor_order_id,
                VendorOrder.vendor_id == vendor_id,
            )
            .with_for_update()
        )
        return db.scalar(statement)
