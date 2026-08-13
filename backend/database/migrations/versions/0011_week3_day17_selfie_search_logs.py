"""Week 3 Day 17: selfie_search_logs table

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-13 16:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'selfie_search_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ip_hash', sa.String(64), nullable=False),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),
        sa.Column('faces_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('threshold_used', sa.Float(), nullable=False),
        sa.Column('results_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('top_similarity', sa.Float(), nullable=True),
        sa.Column('session_id', sa.String(64), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_selfie_search_logs_event_created', 'selfie_search_logs', ['event_id', 'created_at'])
    op.create_index('ix_selfie_search_logs_ip_created', 'selfie_search_logs', ['ip_hash', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_selfie_search_logs_ip_created', table_name='selfie_search_logs')
    op.drop_index('ix_selfie_search_logs_event_created', table_name='selfie_search_logs')
    op.drop_table('selfie_search_logs')
