"""Add idempotency records and immutable wallet ledger trigger."""

from alembic import op
import sqlalchemy as sa


revision = "7e4c9b2a1d60"
down_revision = "c1bc37157565"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "user_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_user_operation_key",
        ),
    )
    op.create_index(
        "ix_idempotency_records_user_id",
        "idempotency_records",
        ["user_id"],
    )
    op.create_index(
        "ix_idempotency_records_order_id",
        "idempotency_records",
        ["order_id"],
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_wallet_transaction_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'wallet_transactions are immutable; create a compensating transaction instead'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_wallet_transactions_immutable
        BEFORE UPDATE OR DELETE ON wallet_transactions
        FOR EACH ROW
        EXECUTE FUNCTION prevent_wallet_transaction_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_wallet_transactions_immutable "
        "ON wallet_transactions"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS prevent_wallet_transaction_mutation()"
    )
    op.drop_index(
        "ix_idempotency_records_order_id",
        table_name="idempotency_records",
    )
    op.drop_index(
        "ix_idempotency_records_user_id",
        table_name="idempotency_records",
    )
    op.drop_table("idempotency_records")
