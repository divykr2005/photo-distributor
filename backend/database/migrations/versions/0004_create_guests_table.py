"""create guests table

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    embedding_status = postgresql.ENUM(
        'pending', 'success', 'failed',
        name='embeddingstatus', create_type=True
    )
    embedding_status.create(op.get_bind(), checkfirst=True)

    op.create_table('guests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(500), nullable=True),
        sa.Column('embedding_status', embedding_status, nullable=False, server_default='pending'),
        sa.Column('consent_given_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_guests_event_id'), 'guests', ['event_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_guests_event_id'), table_name='guests')
    op.drop_table('guests')
    sa.Enum(name='embeddingstatus').drop(op.get_bind(), checkfirst=True)
