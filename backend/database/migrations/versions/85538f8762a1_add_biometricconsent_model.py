"""Add BiometricConsent model

Revision ID: 85538f8762a1
Revises: 0118205ec8f1
Create Date: 2026-09-10 11:22:48.625198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '85538f8762a1'
down_revision: Union[str, None] = '0118205ec8f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('biometric_consents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('guest_id', sa.UUID(), nullable=False),
    sa.Column('consent_text_version', sa.String(length=50), nullable=False),
    sa.Column('phone_e164', sa.String(length=20), nullable=False),
    sa.Column('given_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['guest_id'], ['guests.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_biometric_consents_guest_id'), 'biometric_consents', ['guest_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_biometric_consents_guest_id'), table_name='biometric_consents')
    op.drop_table('biometric_consents')
