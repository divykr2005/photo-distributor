"""P2_RLS_roles

Revision ID: 1ab66ee073eb
Revises: 79da2cb09482
Create Date: 2026-09-13 23:39:08.882769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ab66ee073eb'
down_revision: Union[str, None] = 'f2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely create roles if they don't exist
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'role_biometric_worker') THEN
            CREATE ROLE role_biometric_worker;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'role_general_worker') THEN
            CREATE ROLE role_general_worker;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'role_api') THEN
            CREATE ROLE role_api;
        END IF;
    END
    $$;
    """)

    # Enable RLS on sensitive tables
    op.execute("ALTER TABLE face_embeddings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE photo_faces ENABLE ROW LEVEL SECURITY;")

    # Grant access ONLY to the biometric worker for these tables
    # (Note: Table owners bypass RLS by default unless FORCE ROW LEVEL SECURITY is used.
    # To fully utilize this, the app must connect using these specific roles.)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE policyname = 'biometric_worker_all_face_embeddings'
        ) THEN
            CREATE POLICY biometric_worker_all_face_embeddings ON face_embeddings
                FOR ALL
                TO role_biometric_worker
                USING (true)
                WITH CHECK (true);
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE policyname = 'biometric_worker_all_photo_faces'
        ) THEN
            CREATE POLICY biometric_worker_all_photo_faces ON photo_faces
                FOR ALL
                TO role_biometric_worker
                USING (true)
                WITH CHECK (true);
        END IF;
    END
    $$;
    """)

def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS biometric_worker_all_face_embeddings ON face_embeddings;")
    op.execute("DROP POLICY IF EXISTS biometric_worker_all_photo_faces ON photo_faces;")

    # Disable RLS
    op.execute("ALTER TABLE face_embeddings DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE photo_faces DISABLE ROW LEVEL SECURITY;")

    # (Roles are not dropped in downgrade to avoid breaking other potential dependencies)
