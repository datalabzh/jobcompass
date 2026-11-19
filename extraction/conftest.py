"""
conftest.py

Description : outils de test partagés par tous les tests de l'extraction (commun
              et sites), à la racine de la brique pour être vus partout.
Règles      : les tests utilisent les vrais stockages (PostgresDbStorage et
              S3FileStorage, réunis dans Storages), contre les conteneurs de infra/
              (docker compose -f infra/docker-compose.yml up -d --wait) ; pas de faux
              stockage. Ils écrivent dans la zone de test, vidée avant chaque test.
              Seul le réseau est simulé (FakeGetPage).
"""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from extraction.interfaces import Page, PageFetchError
from storage.postgres_db_storage import PostgresDbStorage
from storage.s3_file_storage import S3FileStorage

NOW: datetime = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)


def fixed_now() -> datetime:
    """The fixed time of the tests."""
    return NOW


@dataclass(frozen=True)
class Storages:
    """The two real storages of a test run: tables and raw files."""

    db: PostgresDbStorage
    files: S3FileStorage


@pytest.fixture
def storages() -> Storages:
    """The test zones of the real storages, emptied before the test."""
    test: Storages = Storages(
        db=PostgresDbStorage(is_test=True), files=S3FileStorage(is_test=True)
    )
    test.db.clear_test_zone()
    test.files.clear_test_zone()
    return test


def page(status: int = 200, content: bytes = b"<html>job</html>") -> Page:
    """An HTML answer with the given status and body."""
    return Page(content=content, http_status=status, content_type="text/html")


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
