import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    section_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_range: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_tsv: Mapped[object | None] = mapped_column(TSVECTOR, nullable=True)

    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Keep only for loose labels if you still want them
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Explicit structured metadata
    doc_type: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    course_code: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    program_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessed_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_year: Mapped[str | None] = mapped_column(Text, nullable=True)

    citation_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)

    section_parser: Mapped[str | None] = mapped_column(Text, nullable=True)
    subchunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )