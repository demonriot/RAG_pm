from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


DocType = Literal["course", "program", "policy"]


class CatalogPageSeed(BaseModel):
    """
    Describes a catalog page to fetch and ingest.
    This is the input to the ingestion pipeline.
    """
    url: str
    doc_type: DocType
    title_hint: Optional[str] = None
    course_code: Optional[str] = None
    program_name: Optional[str] = None
    catalog_year: Optional[str] = None
    accessed_date: str


class CatalogSection(BaseModel):
    """
    A logical section extracted from a catalog page,
    e.g. 'Prerequisites', 'Description', 'Degree Requirements'.
    """
    heading: str
    text: str
    order: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CatalogDocument(BaseModel):
    """
    Normalized parsed document before persistence into DB models.
    """
    doc_type: DocType
    title: str
    source_url: str
    accessed_date: str

    course_code: Optional[str] = None
    program_name: Optional[str] = None
    catalog_year: Optional[str] = None

    raw_text: str
    clean_text: str

    sections: List[CatalogSection] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CatalogChunk(BaseModel):
    """
    Final normalized chunk ready to map into DB chunk rows
    and later into vector-store records.
    """
    doc_type: DocType
    title: str
    source_url: str
    accessed_date: str

    chunk_index: int
    text: str
    citation_label: str

    section: Optional[str] = None
    course_code: Optional[str] = None
    program_name: Optional[str] = None
    catalog_year: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)