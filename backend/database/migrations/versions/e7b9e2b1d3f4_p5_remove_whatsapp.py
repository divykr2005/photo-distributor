"""p5_remove_whatsapp

Revision ID: e7b9e2b1d3f4
Revises: 5c9e2b1d3f4a
Create Date: 2026-09-14 01:37:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7b9e2b1d3f4'
down_revision = '5c9e2b1d3f4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop whatsapp_consent_at column from guests table
    op.drop_column('guests', 'whatsapp_consent_at')


def downgrade() -> None:
    # Re-add whatsapp_consent_at column
    op.add_column('guests', sa.Column('whatsapp_consent_at', sa.DateTime(timezone=True), nullable=True))
