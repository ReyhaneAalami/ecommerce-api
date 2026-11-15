
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="check_order_item_quantity",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="check_order_item_unit_price",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="check_order_item_subtotal",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    vendor_order_id: Mapped[int] = mapped_column(
        ForeignKey("vendor_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    sku: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    vendor_order: Mapped["VendorOrder"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product"] = relationship(
        back_populates="order_items",
    )
