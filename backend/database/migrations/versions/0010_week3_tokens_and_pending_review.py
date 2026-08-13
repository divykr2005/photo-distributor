"""Week 3 Day 15: pending_review status, guest_access_tokens, event/guest amendments

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-13 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── D20 fix: backfill decision='review' rows from active → pending_review ──
    # The status column is a free-form String(50), no enum to alter.
    op.execute(
        "UPDATE matches SET status = 'pending_review' "
        "WHERE decision = 'review' AND status = 'active'"
    )

    # ── Event amendments for Week 3 ──
    op.add_column('events', sa.Column('portal_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('events', sa.Column('portal_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('events', sa.Column('selfie_search_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('events', sa.Column('timezone', sa.String(64), nullable=False, server_default='UTC'))
    op.add_column('events', sa.Column('selfie_threshold', sa.Float(), nullable=True))

    # ── Guest amendments for Week 3 ──
    op.add_column('guests', sa.Column('notify_opt_out_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('guests', sa.Column('last_notified_at', sa.DateTime(timezone=True), nullable=True))

    # ── GuestAccessTokens (D17–D19) ──
    op.create_table(
        'guest_access_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('guests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('token_prefix', sa.String(8), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_guest_access_tokens_token_hash', 'guest_access_tokens', ['token_hash'], unique=True)
    op.create_index('ix_guest_access_tokens_guest_revoked', 'guest_access_tokens', ['guest_id', 'revoked_at'])


def downgrade() -> None:
    op.drop_index('ix_guest_access_tokens_guest_revoked', table_name='guest_access_tokens')
    op.drop_index('ix_guest_access_tokens_token_hash', table_name='guest_access_tokens')
    op.drop_table('guest_access_tokens')

    op.drop_column('guests', 'last_notified_at')
    op.drop_column('guests', 'notify_opt_out_at')

    op.drop_column('events', 'selfie_threshold')
    op.drop_column('events', 'timezone')
    op.drop_column('events', 'selfie_search_enabled')
    op.drop_column('events', 'portal_expires_at')
    op.drop_column('events', 'portal_enabled')

    # Revert backfill
    op.execute(
        "UPDATE matches SET status = 'active' "
        "WHERE decision = 'review' AND status = 'pending_review'"
    )
