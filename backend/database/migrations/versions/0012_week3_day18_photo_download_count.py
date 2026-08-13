"""Week 3 Day 18: Add download_count to photos table

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-13 16:20:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0012'
down_revision: Union[str, None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('photos', sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('photos', 'download_count')
