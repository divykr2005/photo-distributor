"""Add HNSW index for face embeddings

Revision ID: a17d960eaf48
Revises: 8cbfadeeee1c
Create Date: 2026-09-07 22:03:59.008371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a17d960eaf48'
down_revision: Union[str, None] = '8cbfadeeee1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Alter columns to ensure they are parsed as vector(512)
    # (they might be TEXT if VECTOR_AVAILABLE was previously False on init)
    op.execute("ALTER TABLE photo_faces ALTER COLUMN embedding TYPE vector(512) USING (embedding::vector(512));")
    op.execute("ALTER TABLE face_embeddings ALTER COLUMN embedding TYPE vector(512) USING (embedding::vector(512));")

    # Create HNSW indexes using cosine distance
    # m=16, ef_construction=64 are reasonable defaults for 512d vectors
    op.execute("CREATE INDEX IF NOT EXISTS photo_faces_embedding_idx ON photo_faces USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);")
    op.execute("CREATE INDEX IF NOT EXISTS face_embeddings_embedding_idx ON face_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS face_embeddings_embedding_idx;")
    op.execute("DROP INDEX IF EXISTS photo_faces_embedding_idx;")
    op.execute("ALTER TABLE face_embeddings ALTER COLUMN embedding TYPE TEXT USING (embedding::text);")
    op.execute("ALTER TABLE photo_faces ALTER COLUMN embedding TYPE TEXT USING (embedding::text);")
