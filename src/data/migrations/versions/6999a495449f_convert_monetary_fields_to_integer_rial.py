
"""convert monetary fields to integer rial

Revision ID: 6999a495449f
Revises: c715e76e2712
Create Date: 2026-11-20 21:26:57.362377
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6999a495449f"
down_revision: Union[str, Sequence[str], None] = "c715e76e2712"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert monetary columns to integer rial."""

    op.alter_column(
        "products",
        "price",
        existing_type=sa.Numeric(12, 2),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="price::bigint",
    )

    op.alter_column(
        "orders",
        "total_amount",
        existing_type=sa.Numeric(12, 2),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="total_amount::bigint",
    )

    for column in ("subtotal", "shipping_fee", "total_amount"):
        op.alter_column(
            "vendor_orders",
            column,
            existing_type=sa.Numeric(12, 2),
            type_=sa.BigInteger(),
            existing_nullable=False,
            postgresql_using=f"{column}::bigint",
        )

    for column in ("unit_price", "subtotal"):
        op.alter_column(
            "order_items",
            column,
            existing_type=sa.Numeric(12, 2),
            type_=sa.BigInteger(),
            existing_nullable=False,
            postgresql_using=f"{column}::bigint",
        )


def downgrade() -> None:
    """Convert integer rial columns back to numeric."""

    for column in ("unit_price", "subtotal"):
        op.alter_column(
            "order_items",
            column,
            existing_type=sa.BigInteger(),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
            postgresql_using=f"{column}::numeric(12,2)",
        )

    for column in ("subtotal", "shipping_fee", "total_amount"):
        op.alter_column(
            "vendor_orders",
            column,
            existing_type=sa.BigInteger(),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
            postgresql_using=f"{column}::numeric(12,2)",
        )

    op.alter_column(
        "orders",
        "total_amount",
        existing_type=sa.BigInteger(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
        postgresql_using="total_amount::numeric(12,2)",
    )

    op.alter_column(
        "products",
        "price",
        existing_type=sa.BigInteger(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
        postgresql_using="price::numeric(12,2)",
    )
