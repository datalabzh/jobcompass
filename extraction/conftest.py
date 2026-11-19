"""
conftest.py

Description : outils de test partagés par tous les tests de l'extraction (commun
              et sites), à la racine de la brique pour être vus partout.
Règles      : les tests utilisent le vrai LocalParquetStorage dans un dossier
              temporaire (pas de faux stockage) ; seul le réseau est simulé
              (FakeGetPage).
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from extraction.interfaces import Page, PageFetchError
from storage import LocalParquetStorage

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
