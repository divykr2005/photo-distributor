"""Week 3 Day 20: Zip archives table

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-13 17:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'zip_archives',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('guests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_set_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('photo_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('processed_photos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('ix_zip_archives_guest_id', 'zip_archives', ['guest_id'])
    op.create_index('ix_zip_archives_event_id', 'zip_archives', ['event_id'])
    op.create_index('ix_zip_archives_status', 'zip_archives', ['status'])
    op.create_index('ix_zip_archives_expires_at', 'zip_archives', ['expires_at'])
    op.create_unique_constraint('uq_zip_archives_guest_match_hash', 'zip_archives', ['guest_id', 'match_set_hash'])


def downgrade() -> None:
    op.drop_constraint('uq_zip_archives_guest_match_hash', 'zip_archives', type_='unique')
    op.drop_index('ix_zip_archives_expires_at', table_name='zip_archives')
    op.drop_index('ix_zip_archives_status', table_name='zip_archives')
    op.drop_index('ix_zip_archives_event_id', table_name='zip_archives')
    op.drop_index('ix_zip_archives_guest_id', table_name='zip_archives')
    op.drop_table('zip_archives')
