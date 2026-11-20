from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.data.base import Base, TimestampMixin


class IdempotencyRecord(TimestampMixin, Base):
    __tablename__ = "idempotency_records"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_user_operation_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    operation: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
