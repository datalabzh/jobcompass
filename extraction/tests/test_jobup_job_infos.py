"""
test_jobup_job_infos.py

Description : tests des job infos de jobup.ch.
Règles      : s'exécute sur une vraie page de résultats enregistrée dans
              tests/fixtures, servie par un faux get_page (pas de réseau). L'URL
              utilise le slug de catégorie ; une réponse non 200 ou une page sans
              __INIT__ est une erreur ; les pages sont produites une par une.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import FakeGetPage, fixed_now, page

from extraction.interfaces.i_job_infos_extractor import JobInfoPage, ListingError
from extraction.jobup.jobup_job_infos import JobupJobInfos

FIXTURE: Path = Path(__file__).parent / "fixtures" / "jobup_listing_page.html"
CATEGORY: str = "informatique-telecommunications"
PAGE_1: str = "https://www.jobup.ch/fr/emplois/informatique-telecommunications/?page=1"


def job_infos(get_page: FakeGetPage, is_test: bool = False) -> JobupJobInfos:
    """jobup job infos on the given fake network."""
    return JobupJobInfos(get_page, "jobup", is_test, fixed_now)


def test_first_page_from_real_page() -> None:
    """A real page gives its total and its jobs as JobInfo with raw JSON cards."""
    get_page: FakeGetPage = FakeGetPage({PAGE_1: page(content=FIXTURE.read_bytes())})

    pages: Iterator[JobInfoPage] = job_infos(get_page, is_test=True).execute(
        CATEGORY, "run-1"
    )
    first: JobInfoPage = next(pages)

    assert get_page.requested == [PAGE_1]  # one page read, not the 40
    assert (first.announced_total, len(first.job_infos)) == (786, 22)
    info = first.job_infos[0]
    assert info.url == (
        "https://www.jobup.ch/fr/emplois/detail/18943dd6-c820-41e9-9e37-0da70fd57866/"
    )
    assert (info.source, info.is_test, info.run_id) == ("jobup", True, "run-1")
    assert info.listing_params == {"category": CATEGORY}
    assert json.loads(info.card or "")["title"] == "Financial Analyst & AI Engineer"


def test_blocked_listing_is_an_error() -> None:
    """A blocked result page (HTTP 403) raises ListingError."""
    get_page: FakeGetPage = FakeGetPage({PAGE_1: page(status=403)})
    with pytest.raises(ListingError, match="HTTP 403"):
        next(job_infos(get_page).execute(CATEGORY, "run-1"))


def test_listing_without_data_is_an_error() -> None:
    """A result page without the __INIT__ block raises ListingError."""
    get_page: FakeGetPage = FakeGetPage({PAGE_1: page(content=b"<html>Denied</html>")})
    with pytest.raises(ListingError, match="__INIT__"):
        next(job_infos(get_page).execute(CATEGORY, "run-1"))
