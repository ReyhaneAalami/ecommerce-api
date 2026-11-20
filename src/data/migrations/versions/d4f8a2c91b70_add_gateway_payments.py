"""Add gateway payments and wallet top-up ledger uniqueness.

Revision ID: d4f8a2c91b70
Revises: b83f1a9c2d70
"""
from alembic import op
import sqlalchemy as sa

revision = "d4f8a2c91b70"
down_revision = "b83f1a9c2d70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_rial", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("callback_token", sa.String(64), nullable=False),
        sa.Column("authority", sa.String(100), nullable=True),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_rial > 0", name="check_payment_amount_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'cancelled', 'expired')",
            name="check_payment_status",
        ),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_payment_user_idempotency"),
        sa.UniqueConstraint("callback_token", name="uq_payments_callback_token"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_user_created", "payments", ["user_id", "created_at"])
    op.create_index(
        "uq_payment_provider_authority", "payments", ["provider", "authority"],
        unique=True, postgresql_where=sa.text("authority IS NOT NULL"),
    )
    op.create_index(
        "uq_wallet_top_up_payment", "wallet_transactions",
        ["reference_type", "reference_id"], unique=True,
        postgresql_where=sa.text(
            "transaction_type = 'top_up' AND reference_type = 'payment' "
            "AND reference_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_wallet_top_up_payment", table_name="wallet_transactions")
    op.drop_index("uq_payment_provider_authority", table_name="payments")
    op.drop_index("ix_payments_user_created", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")
