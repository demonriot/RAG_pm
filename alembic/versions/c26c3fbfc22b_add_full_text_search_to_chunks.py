"""add full text search to chunks

Revision ID: c26c3fbfc22b
Revises: 55eb041f0730
Create Date: 2026-02-23 09:00:45.252071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c26c3fbfc22b'
down_revision: Union[str, Sequence[str], None] = '55eb041f0730'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ Add tsvector column
    op.add_column(
        "chunks",
        sa.Column("content_tsv", sa.dialects.postgresql.TSVECTOR(), nullable=True),
    )

    # 2️⃣ Populate existing rows
    op.execute(
        """
        UPDATE chunks
        SET content_tsv = to_tsvector('simple', content);
        """
    )

    # 3️⃣ Create GIN index
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunks_content_tsv
        ON chunks
        USING GIN (content_tsv);
        """
    )

    # 4️⃣ Optional but recommended: trigger to auto-update on insert/update
    op.execute(
        """
        CREATE FUNCTION chunks_tsv_trigger() RETURNS trigger AS $$
        BEGIN
          NEW.content_tsv :=
            to_tsvector('simple', NEW.content);
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER tsv_update BEFORE INSERT OR UPDATE
        ON chunks
        FOR EACH ROW EXECUTE FUNCTION chunks_tsv_trigger();
        """
    )
    pass


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tsv_update ON chunks;")
    op.execute("DROP FUNCTION IF EXISTS chunks_tsv_trigger;")
    op.drop_index("ix_chunks_content_tsv", table_name="chunks")
    op.drop_column("chunks", "content_tsv")
    pass
