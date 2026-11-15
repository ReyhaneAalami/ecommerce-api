from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class CartItem(TimestampMixin, Base):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            "product_id",
            name="uq_cart_item_product",
        ),
        CheckConstraint(
            "quantity > 0",
            name="check_cart_item_quantity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    cart: Mapped["Cart"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product"] = relationship()