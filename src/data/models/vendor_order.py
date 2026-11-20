
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class VendorOrder(TimestampMixin, Base):
    __tablename__ = "vendor_orders"

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "vendor_id",
            name="uq_vendor_order_order_vendor",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="check_vendor_order_subtotal",
        ),
        CheckConstraint(
            "shipping_fee >= 0",
            name="check_vendor_order_shipping_fee",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="check_vendor_order_total",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    vendor_id: Mapped[int] = mapped_column(
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    vendor_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    subtotal: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    shipping_fee: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    total_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    order: Mapped["Order"] = relationship(
        back_populates="vendor_orders",
    )

    vendor: Mapped["Vendor"] = relationship(
        back_populates="vendor_orders",
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="vendor_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
