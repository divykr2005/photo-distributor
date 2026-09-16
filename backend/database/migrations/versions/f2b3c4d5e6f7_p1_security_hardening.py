"""p1_security_hardening

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-09-13

P1 security hardening — two schema changes:

1. events: add min_age_confirmed (boolean, default False).
   The extract_faces worker requires both upload_mode='controlled' AND
   min_age_confirmed=True before any biometric extraction is performed.
   This implements the COPPA / GDPR Art.8 / UK-GDPR age-assurance gate.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2b3c4d5e6f7'
down_revision: Union[str, None] = 'e1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. events: children age confirmation gate (P1)
    op.add_column(
        'events',
        sa.Column(
            'min_age_confirmed',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    op.drop_column('events', 'min_age_confirmed')
