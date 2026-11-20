
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0",
            name="check_order_total_amount",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    total_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    customer: Mapped["User"] = relationship(
        back_populates="orders",
    )

    vendor_orders: Mapped[list["VendorOrder"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
