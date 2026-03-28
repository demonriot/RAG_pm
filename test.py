import json
from pathlib import Path
from app.ingestion.sources.osu_catalog import OSUCatalogSource
from app.ingestion.parsers.html_cleaner import clean_html
from app.ingestion.parsers.section_parser import parse_sections
from app.ingestion.parsers.chunker import build_chunks


def main() -> None:
    source = OSUCatalogSource()
    pages = source.fetch_all(accessed_date="2026-03-28")

    out_dir = Path("tmp/chunk_debug")
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, page in enumerate(pages, start=1):
        title, clean_text = clean_html(page.html)
        sections = parse_sections(clean_text, page.doc_type)

        chunks = build_chunks(
            sections=sections,
            doc_type=page.doc_type,
            title=title,
            source_url=page.url,
            accessed_date=page.accessed_date,
            course_code=page.course_code,
            program_name=page.program_name,
            catalog_year=page.catalog_year,
        )

        payload = [chunk.model_dump() for chunk in chunks]
        out_path = out_dir / f"page_{i}_{page.doc_type}_chunks.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print(f"Saved {len(chunks)} chunks to {out_path}")


if __name__ == "__main__":
    main()