"""Day 24 Phase 3 Drop Plaintext

Revision ID: 0016_day24_crypto_phase_3
Revises: 0015_day24_crypto_phase_1
Create Date: 2026-08-20 22:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0016_day24_crypto_phase_3'
down_revision = '0015_day24_crypto_phase_1'
branch_labels = None
depends_on = None

def upgrade():
    # Only drop after backfill script confirms verification.
    # Note: postgresql.VECTOR is needed if using pgvector, but sa.Text is the fallback.
    # We will just drop it.
    op.drop_column('face_embeddings', 'embedding')

def downgrade():
    # We cannot recover the plaintext data easily.
    # Add column back as fallback Text type.
    op.add_column('face_embeddings', sa.Column('embedding', sa.Text(), nullable=True))
