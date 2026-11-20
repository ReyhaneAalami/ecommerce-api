
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint("price > 0", name="check_product_price"),
        CheckConstraint(
            "stock_quantity >= 0",
            name="check_product_stock",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    vendor_id: Mapped[int] = mapped_column(
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(220),
        unique=True,
        nullable=False,
    )

    sku: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    vendor: Mapped["Vendor"] = relationship(
        back_populates="products",
    )

    category: Mapped["Category"] = relationship(
        back_populates="products",
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="product",
    )
