from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class WalletTransaction(TimestampMixin, Base):
    __tablename__ = "wallet_transactions"

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_wallet_transaction_amount_positive"),
        CheckConstraint("balance_after >= 0", name="check_wallet_transaction_balance_non_negative"),
        Index(
            "uq_wallet_order_payment", "reference_type", "reference_id", unique=True,
            postgresql_where=text("transaction_type = 'order_payment' AND reference_type = 'order' AND reference_id IS NOT NULL"),
            sqlite_where=text("transaction_type = 'order_payment' AND reference_type = 'order' AND reference_id IS NOT NULL"),
        ),
        Index(
            "uq_wallet_order_refund", "reference_type", "reference_id", unique=True,
            postgresql_where=text("transaction_type = 'refund' AND reference_type = 'order' AND reference_id IS NOT NULL"),
            sqlite_where=text("transaction_type = 'refund' AND reference_type = 'order' AND reference_id IS NOT NULL"),
        ),
        Index(
            "uq_wallet_top_up_payment", "reference_type", "reference_id", unique=True,
            postgresql_where=text("transaction_type = 'top_up' AND reference_type = 'payment' AND reference_id IS NOT NULL"),
            sqlite_where=text("transaction_type = 'top_up' AND reference_type = 'payment' AND reference_id IS NOT NULL"),
        ),
        Index(
            "uq_wallet_vendor_earning_vendor_order", "reference_type", "reference_id", unique=True,
            postgresql_where=text("transaction_type = 'vendor_earning' AND reference_type = 'vendor_order' AND reference_id IS NOT NULL"),
            sqlite_where=text("transaction_type = 'vendor_earning' AND reference_type = 'vendor_order' AND reference_id IS NOT NULL"),
        ),
        Index(
            "uq_wallet_payout_hold", "reference_type", "reference_id", unique=True,
            postgresql_where=text("transaction_type = 'payout_hold' AND reference_type = 'payout_request' AND reference_id IS NOT NULL"),
            sqlite_where=text("transaction_type = 'payout_hold' AND reference_type = 'payout_request' AND reference_id IS NOT NULL"),
        ),
        Index(
            "uq_wallet_payout_reversal", "reference_type", "reference_id", unique=True,
            postgresql_where=text("transaction_type = 'payout_reversal' AND reference_type = 'payout_request' AND reference_id IS NOT NULL"),
            sqlite_where=text("transaction_type = 'payout_reversal' AND reference_type = 'payout_request' AND reference_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")
