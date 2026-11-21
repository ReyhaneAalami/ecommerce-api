from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class ProductReview(TimestampMixin, Base):
    __tablename__ = "product_reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_product_review_rating"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_product_review_status"),
        UniqueConstraint("product_id", "customer_id", name="uq_product_review_customer_product"),
        UniqueConstraint("order_item_id", name="uq_product_review_order_item"),
        Index("ix_product_reviews_product_status_created", "product_id", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    moderation_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    product = relationship("Product")
    customer = relationship("User", foreign_keys=[customer_id])
    moderator = relationship("User", foreign_keys=[moderated_by])
    order_item = relationship("OrderItem")
