from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import requests

from app.ingestion.schemas.catalog_models import CatalogPageSeed


DEFAULT_TIMEOUT_SECONDS = 20

COURSE_PAGES = [
    {
        "url": "https://catalog.oregonstate.edu/courses/cs/",
        "title_hint": "Computer Science Course Descriptions",
        "course_code": None,
    },
]

PROGRAM_PAGES = [
    {
        "url": "https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/",
        "title_hint": "Computer Science, B.S. Requirements",
        "program_name": "Computer Science BS",
    },
]

POLICY_PAGES = [
    {
        "url": "https://catalog.oregonstate.edu/regulations/",
        "title_hint": "Academic Regulations",
    },
]


@dataclass
class FetchedCatalogPage:
    url: str
    doc_type: str
    accessed_date: str
    status_code: int
    html: str
    title_hint: Optional[str] = None
    course_code: Optional[str] = None
    program_name: Optional[str] = None
    catalog_year: Optional[str] = None


class OSUCatalogSource:
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def get_course_seeds(self, accessed_date: str) -> List[CatalogPageSeed]:
        return [
            CatalogPageSeed(
                url=item["url"],
                doc_type="course",
                title_hint=item.get("title_hint"),
                course_code=item.get("course_code"),
                catalog_year="2025-2026",
                accessed_date=accessed_date,
            )
            for item in COURSE_PAGES
        ]

    def get_program_seeds(self, accessed_date: str) -> List[CatalogPageSeed]:
        return [
            CatalogPageSeed(
                url=item["url"],
                doc_type="program",
                title_hint=item.get("title_hint"),
                program_name=item.get("program_name"),
                catalog_year="2025-2026",
                accessed_date=accessed_date,
            )
            for item in PROGRAM_PAGES
        ]

    def get_policy_seeds(self, accessed_date: str) -> List[CatalogPageSeed]:
        return [
            CatalogPageSeed(
                url=item["url"],
                doc_type="policy",
                title_hint=item.get("title_hint"),
                catalog_year="2025-2026",
                accessed_date=accessed_date,
            )
            for item in POLICY_PAGES
        ]

    def get_all_seeds(self, accessed_date: str) -> List[CatalogPageSeed]:
        return [
            *self.get_course_seeds(accessed_date),
            *self.get_program_seeds(accessed_date),
            *self.get_policy_seeds(accessed_date),
        ]

    def fetch_page(self, seed: CatalogPageSeed) -> FetchedCatalogPage:
        response = requests.get(seed.url, timeout=self.timeout_seconds)
        response.raise_for_status()

        return FetchedCatalogPage(
            url=seed.url,
            doc_type=seed.doc_type,
            accessed_date=seed.accessed_date,
            status_code=response.status_code,
            html=response.text,
            title_hint=seed.title_hint,
            course_code=seed.course_code,
            program_name=seed.program_name,
            catalog_year=seed.catalog_year,
        )

    def fetch_all(self, accessed_date: str) -> List[FetchedCatalogPage]:
        return [self.fetch_page(seed) for seed in self.get_all_seeds(accessed_date)]