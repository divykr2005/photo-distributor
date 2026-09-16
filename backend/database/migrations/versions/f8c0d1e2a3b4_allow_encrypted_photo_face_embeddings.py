"""allow encrypted-only photo face embeddings

Revision ID: f8c0d1e2a3b4
Revises: e7b9e2b1d3f4
Create Date: 2026-09-16

The face worker deliberately stores new embeddings only in ``embedding_enc``.
The legacy plaintext pgvector column therefore has to accept NULL.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "f8c0d1e2a3b4"
down_revision = "e7b9e2b1d3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("photo_faces", "embedding", nullable=True)


def downgrade() -> None:
    # PostgreSQL will reject this downgrade if encrypted-only rows exist.
    op.alter_column("photo_faces", "embedding", nullable=False)
