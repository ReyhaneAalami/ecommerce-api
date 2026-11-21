from datetime import datetime
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class PayoutRequest(TimestampMixin, Base):
    __tablename__ = "payout_requests"
    __table_args__ = (
        CheckConstraint("amount_rial > 0", name="check_payout_amount_positive"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'paid')", name="check_payout_status"),
        UniqueConstraint("vendor_id", "idempotency_key", name="uq_payout_vendor_idempotency"),
        Index("ix_payout_requests_status_created", "status", "created_at"),
        Index("ix_payout_requests_vendor_created", "vendor_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_rial: Mapped[int] = mapped_column(BigInteger, nullable=False)
    iban: Mapped[str] = mapped_column(String(26), nullable=False)
    account_holder: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transfer_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    vendor = relationship("Vendor")
    user = relationship("User", foreign_keys=[user_id])
    administrator = relationship("User", foreign_keys=[admin_id])
