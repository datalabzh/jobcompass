"""
conftest.py

Description : shared test helpers of the ingestion brick.
Rules       : tests use the real LocalParquetStorage in a temporary folder (no fake
              storage); only the network (FakeGetPage) or the site (FakeScraper) is
              faked.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from contracts import JobInfo
from ingestion.http import Page, PageFetchError
from ingestion.scrapers.i_scraper import (
    DetailPage,
    IScraper,
    JobDetailError,
    ListingError,
    ListingPage,
)
from ingestion.storage.i_storage import Table
from ingestion.storage.local_parquet_storage import LocalParquetStorage

NOW: datetime = datetime(2026, 11, 13, 6, 0, tzinfo=UTC)


@pytest.fixture
def storage(tmp_path: Path) -> LocalParquetStorage:
    """A real storage writing into the test's temporary folder."""
    return LocalParquetStorage(tmp_path)


def page(status: int = 200, content: bytes = b"<html>job</html>") -> Page:
    """An HTML answer with the given status and body."""
    return Page(content=content, http_status=status, content_type="text/html")


def job_info(*urls: str, at: datetime = NOW) -> list[JobInfo]:
    """JobInfo records of source 'fake' for the given URLs."""
    return [JobInfo(run_id="r1", source="fake", url=url, seen_at=at) for url in urls]


def save_seen(storage: LocalParquetStorage, *urls: str, at: datetime = NOW) -> None:
    """Record the URLs as seen on a result page."""
    storage.append(Table.JOB_INFO, job_info(*urls, at=at))


class FakeGetPage:
    """Answers set up in advance; URL absent = no answer. Records requested URLs."""

    def __init__(self, pages: dict[str, Page]) -> None:
        self.pages: dict[str, Page] = pages
        self.requested: list[str] = []

    def __call__(self, url: str) -> Page:
        """Return the answer set up for the URL, or raise PageFetchError."""
        self.requested.append(url)
        if url not in self.pages:
            raise PageFetchError("connection refused")
        return self.pages[url]


class FakeScraper(IScraper):
    """A fake site: result pages and detail pages set up in advance.

    listings: category -> pages, each page a list of job URLs.
    details: URL -> content (absent = HTTP 404).
    blocked: (category, page) that raise ListingError.
    """

    name: str = "fake"
    version: str = "9.9.9"

    def __init__(
        self,
        listings: dict[str, list[list[str]]],
        details: dict[str, bytes] | None = None,
        blocked: set[tuple[str, int]] | None = None,
    ) -> None:
        super().__init__(get_page=FakeGetPage({}), categories=list(listings))
        self.listings: dict[str, list[list[str]]] = listings
        self.details: dict[str, bytes] = details or {}
        self.blocked: set[tuple[str, int]] = blocked or set()
        self.requested: list[str] = []

    def extract_jobs_from_listing(self, category: str, page: int) -> ListingPage:
        """The jobs of page `page` of a category, each with a minimal JSON card."""
        if (category, page) in self.blocked:
            raise ListingError("HTTP 403")
        pages: list[list[str]] = self.listings[category]
        return ListingPage(
            announced_total=sum(len(p) for p in pages),
            num_pages=len(pages),
            jobs=[(url, json.dumps({"url": url})) for url in pages[page - 1]],
        )

    def extract_job_detail(self, url: str) -> DetailPage:
        """The content set up for the URL, or JobDetailError('HTTP 404')."""
        self.requested.append(url)
        if url not in self.details:
            raise JobDetailError("HTTP 404")
        return DetailPage(
            content=self.details[url], content_type="text/html", http_status=200
        )
