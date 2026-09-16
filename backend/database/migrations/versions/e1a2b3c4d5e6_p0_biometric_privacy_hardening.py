"""p0_biometric_privacy_hardening

Revision ID: e1a2b3c4d5e6
Revises: c4df029dd3a9
Create Date: 2026-09-13

P0 biometric privacy hardening — three schema changes:

1. biometric_consents: add withdrawn_at (nullable timestamp) and
   notice_text_snapshot (text) for consent withdrawal tracking and
   immutable notice evidence.

2. events: add upload_mode enum column ('open'|'controlled') defaulting
   to 'open'. Workers gate biometric extraction on upload_mode='controlled'.

3. photo_faces: add embedding_enc (LargeBinary), enc_nonce (LargeBinary),
   enc_key_id (varchar), lawful_basis (varchar) to hold AES-256-GCM
   ciphertext and its provenance. The plaintext embedding column remains
   but MUST be NULL for all new rows.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, None] = '85538f8762a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. biometric_consents: consent withdrawal + notice evidence
    op.add_column(
        'biometric_consents',
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'biometric_consents',
        sa.Column('notice_text_snapshot', sa.Text(), nullable=True),
    )

    # 2. events: upload_mode (open = biometric extraction blocked by default)
    upload_mode_enum = sa.Enum('open', 'controlled', name='uploadmode')
    upload_mode_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'events',
        sa.Column(
            'upload_mode',
            upload_mode_enum,
            nullable=False,
            server_default='open',
        ),
    )

    # 3. photo_faces: encrypted embedding columns + lawful basis provenance
    op.add_column(
        'photo_faces',
        sa.Column('embedding_enc', sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        'photo_faces',
        sa.Column('enc_nonce', sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        'photo_faces',
        sa.Column('enc_key_id', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'photo_faces',
        sa.Column('lawful_basis', sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    # 3. photo_faces
    op.drop_column('photo_faces', 'lawful_basis')
    op.drop_column('photo_faces', 'enc_key_id')
    op.drop_column('photo_faces', 'enc_nonce')
    op.drop_column('photo_faces', 'embedding_enc')

    # 2. events
    op.drop_column('events', 'upload_mode')
    sa.Enum(name='uploadmode').drop(op.get_bind(), checkfirst=True)

    # 1. biometric_consents
    op.drop_column('biometric_consents', 'notice_text_snapshot')
    op.drop_column('biometric_consents', 'withdrawn_at')
