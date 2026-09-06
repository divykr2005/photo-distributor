"""add embedding column

Revision ID: c4df029dd3a9
Revises: a2a3c194f9e0
Create Date: 2026-09-07 02:36:20.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'c4df029dd3a9'
down_revision: Union[str, None] = 'a2a3c194f9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('face_embeddings', sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=512), nullable=True))


def downgrade() -> None:
    op.drop_column('face_embeddings', 'embedding')
