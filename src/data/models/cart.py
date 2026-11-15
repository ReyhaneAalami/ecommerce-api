from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            name="uq_cart_customer",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer: Mapped["User"] = relationship(
        back_populates="cart",
    )

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )