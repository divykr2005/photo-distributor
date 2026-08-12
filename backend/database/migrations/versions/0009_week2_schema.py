"""create week 2 tables: upload_batches, photos, photo_faces, matches, match_runs

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-12 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add optional threshold columns to events table if not existing
    op.add_column('events', sa.Column('match_threshold', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('review_floor', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('match_margin', sa.Float(), nullable=True))

    # 1. UploadBatches
    op.create_table(
        'upload_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('received_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_upload_batches_event_id', 'upload_batches', ['event_id'])

    # 2. Photos
    op.create_table(
        'photos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('upload_batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('storage_key', sa.String(512), nullable=False),
        sa.Column('web_key', sa.String(512), nullable=True),
        sa.Column('thumb_key', sa.String(512), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('mime_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('exif_taken_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('face_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('event_id', 'content_hash', name='uq_photos_event_content_hash'),
    )
    op.create_index('ix_photos_event_status', 'photos', ['event_id', 'status'])
    op.create_index('ix_photos_batch_status', 'photos', ['batch_id', 'status'])

    # 3. PhotoFaces
    emb_type = Vector(512) if VECTOR_AVAILABLE else sa.Text
    op.create_table(
        'photo_faces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('photo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('photos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bbox_x', sa.Float(), nullable=False),
        sa.Column('bbox_y', sa.Float(), nullable=False),
        sa.Column('bbox_w', sa.Float(), nullable=False),
        sa.Column('bbox_h', sa.Float(), nullable=False),
        sa.Column('det_score', sa.Float(), nullable=False),
        sa.Column('embedding', emb_type, nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False, server_default='buffalo_l'),
        sa.Column('embedding_dim', sa.Integer(), nullable=False, server_default='512'),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('blur_score', sa.Float(), nullable=True),
        sa.Column('face_area_ratio', sa.Float(), nullable=True),
        sa.Column('yaw', sa.Float(), nullable=True),
        sa.Column('pitch', sa.Float(), nullable=True),
        sa.Column('roll', sa.Float(), nullable=True),
        sa.Column('is_matchable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('quality_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('crop_key', sa.String(512), nullable=True),
        sa.Column('matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_photo_faces_event_matchable', 'photo_faces', ['event_id', 'is_matchable', 'matched_at'])

    # 4. MatchRuns
    op.create_table(
        'match_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trigger', sa.String(50), nullable=False),
        sa.Column('scope', sa.String(50), nullable=False),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('faces_scanned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('guests_scanned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_confirmed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_to_review', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('protected_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_match_runs_event_id', 'match_runs', ['event_id'])

    # 5. Matches
    op.create_table(
        'matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('guests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('photo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('photos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('photo_face_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('photo_faces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('match_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('similarity', sa.Float(), nullable=False),
        sa.Column('threshold_used', sa.Float(), nullable=False),
        sa.Column('decision', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('second_guest_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('second_similarity', sa.Float(), nullable=True),
        sa.Column('margin', sa.Float(), nullable=True),
        sa.Column('review_reason', sa.String(100), nullable=True),
        sa.Column('top_candidates', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model_version', sa.String(100), nullable=False, server_default='buffalo_l'),
        sa.Column('matched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('photo_face_id', name='uq_matches_photo_face_id'),
    )
    op.create_index('ix_matches_guest_status_sim', 'matches', ['guest_id', 'status', sa.text('similarity DESC')])
    op.create_index('ix_matches_event_review', 'matches', ['event_id', 'decision'], postgresql_where=sa.text("decision = 'review'"))


def downgrade() -> None:
    op.drop_index('ix_matches_event_review', table_name='matches')
    op.drop_index('ix_matches_guest_status_sim', table_name='matches')
    op.drop_table('matches')

    op.drop_index('ix_match_runs_event_id', table_name='match_runs')
    op.drop_table('match_runs')

    op.drop_index('ix_photo_faces_event_matchable', table_name='photo_faces')
    op.drop_table('photo_faces')

    op.drop_index('ix_photos_batch_status', table_name='photos')
    op.drop_index('ix_photos_event_status', table_name='photos')
    op.drop_table('photos')

    op.drop_index('ix_upload_batches_event_id', table_name='upload_batches')
    op.drop_table('upload_batches')

    op.drop_column('events', 'match_margin')
    op.drop_column('events', 'review_floor')
    op.drop_column('events', 'match_threshold')
