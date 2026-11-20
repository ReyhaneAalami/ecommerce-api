
"""add wallets and wallet transactions

Revision ID: 5a23ee06cb9e
Revises: 6999a495449f
Create Date: 2026-11-20 22:13:15.741169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5a23ee06cb9e"
down_revision: Union[str, Sequence[str], None] = "6999a495449f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "balance",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "balance >= 0",
            name="check_wallet_balance_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_wallets_user_id",
        "wallets",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("reference_type", sa.String(length=30), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="check_wallet_transaction_amount_positive",
        ),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="check_wallet_transaction_balance_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["wallets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_wallet_transactions_reference_id",
        "wallet_transactions",
        ["reference_id"],
        unique=False,
    )

    op.create_index(
        "ix_wallet_transactions_wallet_id",
        "wallet_transactions",
        ["wallet_id"],
        unique=False,
    )

    op.create_index(
        "uq_wallet_order_payment",
        "wallet_transactions",
        ["reference_type", "reference_id"],
        unique=True,
        postgresql_where=sa.text(
            "transaction_type = 'order_payment' "
            "AND reference_type = 'order' "
            "AND reference_id IS NOT NULL"
        ),
    )

    op.create_index(
        "uq_wallet_order_refund",
        "wallet_transactions",
        ["reference_type", "reference_id"],
        unique=True,
        postgresql_where=sa.text(
            "transaction_type = 'refund' "
            "AND reference_type = 'order' "
            "AND reference_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_wallet_order_refund",
        table_name="wallet_transactions",
    )

    op.drop_index(
        "uq_wallet_order_payment",
        table_name="wallet_transactions",
    )

    op.drop_index(
        "ix_wallet_transactions_wallet_id",
        table_name="wallet_transactions",
    )

    op.drop_index(
        "ix_wallet_transactions_reference_id",
        table_name="wallet_transactions",
    )

    op.drop_table("wallet_transactions")

    op.drop_index(
        "ix_wallets_user_id",
        table_name="wallets",
    )

    op.drop_table("wallets")
