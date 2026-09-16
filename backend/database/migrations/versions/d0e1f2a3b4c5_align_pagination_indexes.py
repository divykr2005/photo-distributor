"""align indexes with stable pagination and cluster detail query paths

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-16
"""

from alembic import op


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # Mixed sort directions cannot fully use the previous index for the
        # deterministic similarity DESC, id DESC review ordering.
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_matches_event_review_page")
        op.execute(
            "CREATE INDEX CONCURRENTLY ix_matches_event_review_page "
            "ON matches (event_id, decision, status, similarity DESC, id DESC)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_photos_event_cluster_created "
            "ON photos (event_id, dup_cluster_id, created_at DESC, id DESC)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_photos_event_cluster_created")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_matches_event_review_page")
        op.execute(
            "CREATE INDEX CONCURRENTLY ix_matches_event_review_page "
            "ON matches (event_id, decision, status, similarity DESC, id)"
        )
