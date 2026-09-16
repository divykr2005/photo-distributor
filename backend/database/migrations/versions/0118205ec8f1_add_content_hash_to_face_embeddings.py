"""Add content_hash to face_embeddings

Revision ID: 0118205ec8f1
Revises: a59c236c14f2
Create Date: 2026-09-10 10:51:50.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0118205ec8f1'
down_revision = 'a59c236c14f2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('face_embeddings', sa.Column('content_hash', sa.String(length=64), nullable=True))

def downgrade() -> None:
    op.drop_column('face_embeddings', 'content_hash')
