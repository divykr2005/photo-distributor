"""P3_AuditLog

Revision ID: 5c9e2b1d3f4a
Revises: 1ab66ee073eb
Create Date: 2026-09-14 00:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5c9e2b1d3f4a'
down_revision: Union[str, None] = '1ab66ee073eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_event_id'), 'audit_logs', ['event_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_guest_id'), 'audit_logs', ['guest_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_guest_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
