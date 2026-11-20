"""Add PostgreSQL trigram indexes for product search.

Revision ID: b83f1a9c2d70
Revises: 7e4c9b2a1d60
Create Date: 2026-11-21
"""

from alembic import op


revision = "b83f1a9c2d70"
down_revision = "7e4c9b2a1d60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_name_trgm
        ON products USING gin (name gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_description_trgm
        ON products USING gin (description gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_description_trgm")
    op.execute("DROP INDEX IF EXISTS ix_products_name_trgm")
    # Do not drop pg_trgm: other application indexes may depend on it.
