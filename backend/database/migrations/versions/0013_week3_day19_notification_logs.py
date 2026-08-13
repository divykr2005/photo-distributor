"""Week 3 Day 19: Notification logs table

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-13 17:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('guests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('notification_type', sa.String(), nullable=False, server_default='magic_link'),
        sa.Column('dedupe_key', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('provider_message_id', sa.String(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('guest_id', 'channel', 'notification_type', 'dedupe_key', name='uq_notification_logs_dedupe'),
    )
    op.create_index('ix_notification_logs_status_retry', 'notification_logs', ['status', 'next_retry_at'])
    op.create_index('ix_notification_logs_guest_id', 'notification_logs', ['guest_id'])
    op.create_index('ix_notification_logs_event_id', 'notification_logs', ['event_id'])


def downgrade() -> None:
    op.drop_index('ix_notification_logs_event_id', table_name='notification_logs')
    op.drop_index('ix_notification_logs_guest_id', table_name='notification_logs')
    op.drop_index('ix_notification_logs_status_retry', table_name='notification_logs')
    op.drop_table('notification_logs')
