"""add IVFFlat index on face_embeddings.embedding

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-12 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IVFFlat index for cosine similarity search on face embeddings.
    # lists=100 is a good default for up to ~10K rows; tune if dataset grows.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_face_embeddings_embedding_ivfflat "
        "ON face_embeddings USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_face_embeddings_embedding_ivfflat")
