"""Add verified product reviews, vendor payout workflow, and vendor earnings ledger.

Revision ID: e5f6a7b8c9d0
Revises: d4f8a2c91b70
"""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4f8a2c91b70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("moderation_note", sa.String(500), nullable=True),
        sa.Column("moderated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="check_product_review_rating"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_product_review_status"),
        sa.UniqueConstraint("product_id", "customer_id", name="uq_product_review_customer_product"),
        sa.UniqueConstraint("order_item_id", name="uq_product_review_order_item"),
    )
    op.create_index("ix_product_reviews_product_id", "product_reviews", ["product_id"])
    op.create_index("ix_product_reviews_customer_id", "product_reviews", ["customer_id"])
    op.create_index("ix_product_reviews_product_status_created", "product_reviews", ["product_id", "status", "created_at"])

    op.create_table(
        "payout_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_rial", sa.BigInteger(), nullable=False),
        sa.Column("iban", sa.String(26), nullable=False),
        sa.Column("account_holder", sa.String(150), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("admin_note", sa.String(500), nullable=True),
        sa.Column("transfer_reference", sa.String(150), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_rial > 0", name="check_payout_amount_positive"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'paid')", name="check_payout_status"),
        sa.UniqueConstraint("vendor_id", "idempotency_key", name="uq_payout_vendor_idempotency"),
    )
    op.create_index("ix_payout_requests_vendor_id", "payout_requests", ["vendor_id"])
    op.create_index("ix_payout_requests_user_id", "payout_requests", ["user_id"])
    op.create_index("ix_payout_requests_status_created", "payout_requests", ["status", "created_at"])
    op.create_index("ix_payout_requests_vendor_created", "payout_requests", ["vendor_id", "created_at"])

    # Exactly-once ledger records for delivered vendor orders and payout holds/releases.
    op.create_index(
        "uq_wallet_vendor_earning_vendor_order", "wallet_transactions",
        ["reference_type", "reference_id"], unique=True,
        postgresql_where=sa.text("transaction_type = 'vendor_earning' AND reference_type = 'vendor_order' AND reference_id IS NOT NULL"),
    )
    op.create_index(
        "uq_wallet_payout_hold", "wallet_transactions",
        ["reference_type", "reference_id"], unique=True,
        postgresql_where=sa.text("transaction_type = 'payout_hold' AND reference_type = 'payout_request' AND reference_id IS NOT NULL"),
    )
    op.create_index(
        "uq_wallet_payout_reversal", "wallet_transactions",
        ["reference_type", "reference_id"], unique=True,
        postgresql_where=sa.text("transaction_type = 'payout_reversal' AND reference_type = 'payout_request' AND reference_id IS NOT NULL"),
    )

    # Backfill balances for vendor suborders already delivered before this release.
    # Existing vendor wallets are created by the previous wallet migrations.
    op.execute(sa.text("""
        WITH eligible AS (
            SELECT vo.id AS vendor_order_id, v.user_id, vo.subtotal
            FROM vendor_orders vo
            JOIN vendors v ON v.id = vo.vendor_id
            WHERE vo.status = 'delivered'
              AND vo.subtotal > 0
              AND NOT EXISTS (
                  SELECT 1 FROM wallet_transactions wt
                  WHERE wt.transaction_type = 'vendor_earning'
                    AND wt.reference_type = 'vendor_order'
                    AND wt.reference_id = vo.id
              )
        ), ranked AS (
            SELECT e.vendor_order_id, e.subtotal, w.id AS wallet_id, w.balance AS base_balance,
                   SUM(e.subtotal) OVER (
                       PARTITION BY e.user_id ORDER BY e.vendor_order_id
                       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                   ) AS running_earnings
            FROM eligible e
            JOIN wallets w ON w.user_id = e.user_id
        ), inserted AS (
            INSERT INTO wallet_transactions (
                wallet_id, transaction_type, amount, balance_after,
                reference_type, reference_id, description, created_at, updated_at
            )
            SELECT wallet_id, 'vendor_earning', subtotal,
                   base_balance + running_earnings,
                   'vendor_order', vendor_order_id,
                   'Backfilled earnings for previously delivered vendor order', now(), now()
            FROM ranked
            RETURNING wallet_id, amount
        ), totals AS (
            SELECT wallet_id, SUM(amount) AS amount
            FROM inserted GROUP BY wallet_id
        )
        UPDATE wallets w
        SET balance = w.balance + totals.amount, updated_at = now()
        FROM totals
        WHERE w.id = totals.wallet_id
    """))


def downgrade() -> None:
    op.drop_index("uq_wallet_payout_reversal", table_name="wallet_transactions")
    op.drop_index("uq_wallet_payout_hold", table_name="wallet_transactions")
    op.drop_index("uq_wallet_vendor_earning_vendor_order", table_name="wallet_transactions")
    op.drop_index("ix_payout_requests_vendor_created", table_name="payout_requests")
    op.drop_index("ix_payout_requests_status_created", table_name="payout_requests")
    op.drop_index("ix_payout_requests_user_id", table_name="payout_requests")
    op.drop_index("ix_payout_requests_vendor_id", table_name="payout_requests")
    op.drop_table("payout_requests")
    op.drop_index("ix_product_reviews_product_status_created", table_name="product_reviews")
    op.drop_index("ix_product_reviews_customer_id", table_name="product_reviews")
    op.drop_index("ix_product_reviews_product_id", table_name="product_reviews")
    op.drop_table("product_reviews")
