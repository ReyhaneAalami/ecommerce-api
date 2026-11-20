
"""add payment status to orders

Revision ID: c1bc37157565
Revises: 6afedd71ab25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1bc37157565"
down_revision: Union[str, Sequence[str], None] = "6afedd71ab25"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "payment_status",
            sa.String(length=30),
            nullable=False,
            server_default="unpaid",
        ),
    )

    op.create_check_constraint(
        "check_order_payment_status",
        "orders",
        "payment_status IN ('unpaid', 'paid', 'refunded')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "check_order_payment_status",
        "orders",
        type_="check",
    )

    op.drop_column(
        "orders",
        "payment_status",
    )
