"""add composite indexes for paginated and repeated query paths

Revision ID: c9d0e1f2a3b4
Revises: f8c0d1e2a3b4
Create Date: 2026-09-16
"""

from alembic import op


revision = "c9d0e1f2a3b4"
down_revision = "f8c0d1e2a3b4"
branch_labels = None
depends_on = None


INDEXES = (
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_events_owner_date ON events (created_by, date DESC, id DESC)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_guests_event_created ON guests (event_id, created_at DESC, id DESC)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_photos_event_created ON photos (event_id, created_at DESC, id DESC)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_photos_event_status_created ON photos (event_id, status, created_at DESC, id DESC)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_photo_clusters_active_event_created ON photo_clusters (event_id, created_at DESC, id DESC) WHERE size >= 2",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_matches_event_review_page ON matches (event_id, decision, status, similarity DESC, id)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_matches_guest_visible ON matches (guest_id, status, similarity DESC, photo_id)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_guest_tokens_active ON guest_access_tokens (guest_id, revoked_at, expires_at)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notification_logs_event_created ON notification_logs (event_id, created_at DESC, id DESC)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notification_logs_dedupe ON notification_logs (guest_id, channel, dedupe_key, status)",
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for statement in INDEXES:
            op.execute(statement)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for statement in reversed(INDEXES):
            index_name = statement.split(" EXISTS ", 1)[1].split(" ON ", 1)[0]
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")
