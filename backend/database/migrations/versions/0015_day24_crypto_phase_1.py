"""Day 24 Phase 1 Crypto Columns

Revision ID: 0015_day24_crypto_phase_1
Revises: bc5faf281906
Create Date: 2026-08-20 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0015_day24_crypto_phase_1'
down_revision = 'bc5faf281906'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add KEK to events
    op.add_column('events', sa.Column('wrapped_kek', sa.LargeBinary(), nullable=True))
    op.add_column('events', sa.Column('kek_key_id', sa.String(length=100), nullable=True))

    # 2. Add DEK to guests
    op.add_column('guests', sa.Column('wrapped_dek', sa.LargeBinary(), nullable=True))
    op.add_column('guests', sa.Column('dek_key_id', sa.String(length=100), nullable=True))

    # 3. Add encrypted embeddings to face_embeddings
    op.add_column('face_embeddings', sa.Column('embedding_enc', sa.LargeBinary(), nullable=True))
    op.add_column('face_embeddings', sa.Column('enc_nonce', sa.LargeBinary(), nullable=True))
    op.add_column('face_embeddings', sa.Column('enc_key_id', sa.String(length=100), nullable=True))

def downgrade():
    op.drop_column('face_embeddings', 'enc_key_id')
    op.drop_column('face_embeddings', 'enc_nonce')
    op.drop_column('face_embeddings', 'embedding_enc')
    op.drop_column('guests', 'dek_key_id')
    op.drop_column('guests', 'wrapped_dek')
    op.drop_column('events', 'kek_key_id')
    op.drop_column('events', 'wrapped_kek')
