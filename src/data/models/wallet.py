
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class Wallet(TimestampMixin, Base):
    __tablename__ = "wallets"

    __table_args__ = (
        CheckConstraint(
            "balance >= 0",
            name="check_wallet_balance_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )

    balance: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default="0",
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="wallet",
    )

    transactions: Mapped[list["WalletTransaction"]] = relationship(
        back_populates="wallet",
        passive_deletes="all",
        order_by="WalletTransaction.created_at.desc()",
    )
