"""create face_embeddings table

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure the pgvector extension exists (idempotent)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create the table using raw DDL so we can specify vector(512) directly.
    # Alembic's op.create_table doesn't know the pgvector type, but executing
    # raw SQL is safe and explicit here.
    op.execute("""
        CREATE TABLE face_embeddings (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            guest_id    UUID NOT NULL REFERENCES guests(id) ON DELETE CASCADE,
            embedding   vector(512) NOT NULL,
            model_version VARCHAR(100) NOT NULL DEFAULT 'buffalo_l',
            embedding_dim INTEGER NOT NULL DEFAULT 512,
            quality_score FLOAT,
            created_at  TIMESTAMPTZ,
            updated_at  TIMESTAMPTZ
        )
    """)
    op.execute(
        'CREATE INDEX ix_face_embeddings_guest_id ON face_embeddings (guest_id)'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_face_embeddings_guest_id')
    op.execute('DROP TABLE IF EXISTS face_embeddings')
