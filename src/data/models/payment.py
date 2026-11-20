from datetime import datetime
from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text,
    UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint("amount_rial > 0", name="check_payment_amount_positive"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'cancelled', 'expired')",
            name="check_payment_status",
        ),
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_payment_user_idempotency"
        ),
        Index(
            "uq_payment_provider_authority",
            "provider",
            "authority",
            unique=True,
            postgresql_where=text("authority IS NOT NULL"),
        ),
        Index("ix_payments_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount_rial: Mapped[int] = mapped_column(BigInteger, nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    callback_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    authority: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
