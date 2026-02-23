"""add hnsw index for embeddings

Revision ID: 55eb041f0730
Revises: 1054a54c4cd0
Create Date: 2026-02-23 08:49:14.483013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55eb041f0730'
down_revision: Union[str, Sequence[str], None] = '1054a54c4cd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_embeddings_embedding_hnsw
        ON embeddings
        USING hnsw (embedding vector_cosine_ops);
        """
    )
    pass


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_embedding_hnsw;")
        
    pass
