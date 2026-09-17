"""add no-face guest embedding status

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

from alembic import op


revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE embeddingstatus ADD VALUE IF NOT EXISTS 'no_face'")


def downgrade() -> None:
    # PostgreSQL cannot safely remove an enum value while rows may use it.
    # Keeping the value is the non-destructive downgrade behavior.
    pass
