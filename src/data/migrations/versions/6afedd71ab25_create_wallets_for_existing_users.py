"""create wallets for existing users"""

from alembic import op


revision = "6afedd71ab25"
down_revision = "5a23ee06cb9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO wallets (
            user_id,
            balance,
            created_at,
            updated_at
        )
        SELECT
            users.id,
            0,
            NOW(),
            NOW()
        FROM users
        ON CONFLICT (user_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Do not delete existing wallet data during downgrade.
    pass
