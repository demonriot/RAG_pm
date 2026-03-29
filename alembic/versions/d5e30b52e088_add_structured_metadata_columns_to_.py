"""add structured metadata columns to chunks

Revision ID: d5e30b52e088
Revises: c26c3fbfc22b
Create Date: 2026-03-29 06:50:06.320668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e30b52e088'
down_revision: Union[str, Sequence[str], None] = 'c26c3fbfc22b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("doc_type", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("course_code", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("program_name", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("accessed_date", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("catalog_year", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("citation_label", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("section", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("section_parser", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("subchunk_index", sa.Integer(), nullable=True))

    op.create_index("ix_chunks_doc_type", "chunks", ["doc_type"], unique=False)
    op.create_index("ix_chunks_course_code", "chunks", ["course_code"], unique=False)



def downgrade() -> None:
    op.drop_index("ix_chunks_course_code", table_name="chunks")
    op.drop_index("ix_chunks_doc_type", table_name="chunks")

    op.drop_column("chunks", "subchunk_index")
    op.drop_column("chunks", "section_parser")
    op.drop_column("chunks", "section")
    op.drop_column("chunks", "citation_label")
    op.drop_column("chunks", "catalog_year")
    op.drop_column("chunks", "accessed_date")
    op.drop_column("chunks", "source_url")
    op.drop_column("chunks", "program_name")
    op.drop_column("chunks", "course_code")
    op.drop_column("chunks", "doc_type")