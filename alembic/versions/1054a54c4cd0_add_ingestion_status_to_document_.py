"""add ingestion status to document_versions

Revision ID: 1054a54c4cd0
Revises: 1e963362f779
Create Date: 2026-02-19 09:42:40.808052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1054a54c4cd0'
down_revision: Union[str, Sequence[str], None] = '1e963362f779'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("document_versions", sa.Column("status", sa.Text(), nullable=False, server_default="queued"))
    op.add_column("document_versions", sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("document_versions", sa.Column("error_code", sa.Text(), nullable=True))
    


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("document_versions", "error_code")
    op.drop_column("document_versions", "ingested_at")
    op.drop_column("document_versions", "status")
    
