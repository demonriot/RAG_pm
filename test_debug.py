import json
from pathlib import Path

from app.ingestion.sources.osu_catalog import OSUCatalogSource
from app.ingestion.parsers.html_cleaner import clean_html
from app.ingestion.parsers.section_parser import parse_sections
from app.ingestion.parsers.chunker import build_chunks


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def main() -> None:
    source = OSUCatalogSource()
    pages = source.fetch_all(accessed_date="2026-03-28")

    out_dir = Path("tmp/osu_debug")
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, page in enumerate(pages, start=1):
        parsed_title, clean_text = clean_html(page.html)
        sections = parse_sections(clean_text, page.doc_type)
        chunks = build_chunks(
            sections=sections,
            doc_type=page.doc_type,
            title=parsed_title,
            source_url=page.url,
            accessed_date=page.accessed_date,
            course_code=page.course_code,
            program_name=page.program_name,
            catalog_year=page.catalog_year,
            max_chars=1200,
            overlap=150,
        )

        base = f"{idx:02d}_{page.doc_type}_{slugify(parsed_title or page.title_hint or f'page_{idx}')}"

        meta = {
            "url": page.url,
            "doc_type": page.doc_type,
            "title_hint": page.title_hint,
            "parsed_title": parsed_title,
            "accessed_date": page.accessed_date,
            "catalog_year": page.catalog_year,
            "course_code": page.course_code,
            "program_name": page.program_name,
        }

        (out_dir / f"{base}_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        (out_dir / f"{base}_clean.txt").write_text(
            clean_text,
            encoding="utf-8",
        )

        (out_dir / f"{base}_sections.json").write_text(
            json.dumps([section.model_dump() for section in sections], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        (out_dir / f"{base}_chunks.json").write_text(
            json.dumps([chunk.model_dump() for chunk in chunks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"Saved debug artifacts for: {base}")

    print(f"\nDone. Files written to: {out_dir}")


if __name__ == "__main__":
    main()