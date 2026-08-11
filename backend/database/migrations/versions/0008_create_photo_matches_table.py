"""create photo_matches table

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-12 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'photo_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_photo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('face_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_solo', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_photo_id'], ['event_photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guest_id'], ['guests.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_photo_matches_event_photo_id', 'photo_matches', ['event_photo_id'])
    op.create_index('ix_photo_matches_guest_id', 'photo_matches', ['guest_id'])
    # Prevent duplicate matches for the same face in the same photo
    op.create_index(
        'ix_photo_matches_unique_photo_guest',
        'photo_matches',
        ['event_photo_id', 'guest_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_photo_matches_unique_photo_guest', table_name='photo_matches')
    op.drop_index('ix_photo_matches_guest_id', table_name='photo_matches')
    op.drop_index('ix_photo_matches_event_photo_id', table_name='photo_matches')
    op.drop_table('photo_matches')
