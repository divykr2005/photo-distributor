"""create events table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type first
    event_status = postgresql.ENUM(
        'draft', 'active', 'completed', 'cancelled',
        name='eventstatus', create_type=True
    )
    event_status.create(op.get_bind(), checkfirst=True)

    op.create_table('events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(300), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', postgresql.ENUM('draft', 'active', 'completed', 'cancelled', name='eventstatus', create_type=False), nullable=False, server_default='draft'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_events_created_by'), 'events', ['created_by'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_events_created_by'), table_name='events')
    op.drop_table('events')
    # Drop the enum type
    sa.Enum(name='eventstatus').drop(op.get_bind(), checkfirst=True)
