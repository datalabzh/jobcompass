"""
conftest.py

Description : outils de test partagés de la brique extraction.
Règles      : les tests utilisent le vrai LocalParquetStorage dans un dossier
              temporaire (pas de faux stockage) ; seul le réseau (FakeGetPage) ou le
              site (FakeJobInfos, FakeJobDetails) est simulé.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from contracts import JobInfo
from extraction.http import Page, PageFetchError
from extraction.interfaces.i_job_details_extractor import (
    IJobDetailsExtractor,
    JobDetailResult,
)
from extraction.interfaces.i_job_infos_extractor import (
    IJobInfosExtractor,
    JobInfoPage,
    ListingError,
)
from extraction.interfaces.i_storage import Table
from extraction.storage.local_parquet_storage import LocalParquetStorage

NOW: datetime = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)


def fixed_now() -> datetime:
    """The fixed time of the tests."""
    return NOW


@pytest.fixture
def storage(tmp_path: Path) -> LocalParquetStorage:
    """A real storage for real runs, writing into the test's temporary folder."""
    return LocalParquetStorage(is_test=False, data_dir=tmp_path)


def page(status: int = 200, content: bytes = b"<html>job</html>") -> Page:
    """An HTML answer with the given status and body."""
    return Page(content=content, http_status=status, content_type="text/html")


def save_seen(storage: LocalParquetStorage, *urls: str, at: datetime = NOW) -> None:
    """Record the URLs as seen on a result page of source 'fake'."""
    records: list[JobInfo] = [
        JobInfo(
            run_id="r1", source="fake", is_test=storage.is_test, url=url, seen_at=at
        )
        for url in urls
    ]
    storage.append(Table.JOB_INFO, records)


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


class FakeJobInfos(IJobInfosExtractor):
    """A fake site's result pages: category -> pages, each a list of job URLs.

    blocked: (category, page) that raise ListingError.
    """

    def __init__(
        self,
        listings: dict[str, list[list[str]]],
        blocked: set[tuple[str, int]] | None = None,
        is_test: bool = False,
    ) -> None:
        super().__init__(FakeGetPage({}), "fake", is_test, fixed_now)
        self.listings: dict[str, list[list[str]]] = listings
        self.blocked: set[tuple[str, int]] = blocked or set()
        self.pages_produced: int = 0

    def execute(self, category: str, run_id: str) -> Iterator[JobInfoPage]:
        """Yield the pages of a category, each job with a minimal JSON card."""
        pages: list[list[str]] = self.listings[category]
        for number, urls in enumerate(pages, start=1):
            if (category, number) in self.blocked:
                raise ListingError("HTTP 403")
            self.pages_produced += 1
            yield JobInfoPage(
                announced_total=sum(len(p) for p in pages),
                job_infos=[
                    self._job_info(run_id, category, url, json.dumps({"url": url}))
                    for url in urls
                ],
            )


class FakeJobDetails(IJobDetailsExtractor):
    """A fake site's detail pages: URL -> content (absent = HTTP 404)."""

    version: str = "9.9.9"

    def __init__(self, details: dict[str, bytes], is_test: bool = False) -> None:
        pages: dict[str, Page] = {url: page(content=c) for url, c in details.items()}
        self.fake_get_page: FakeGetPage = FakeGetPage(pages)
        super().__init__(self.fake_get_page, "fake", is_test, fixed_now)

    def execute(self, urls: list[str]) -> list[JobDetailResult]:
        """One result per URL; a URL not set up answers HTTP 404."""
        results: list[JobDetailResult] = []
        for url in urls:
            if url not in self.fake_get_page.pages:
                self.fake_get_page.pages[url] = page(status=404)
            results.append(self._download_detail(url))
        return results
