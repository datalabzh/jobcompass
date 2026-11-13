"""
test_jobup_scraper.py

Description : tests of the jobup.ch scraper.
Rules       : runs on a real result page saved in tests/fixtures, served by a fake
              get_page (no network). Result pages: the URL uses the category slug;
              a non-200 answer or a page without __INIT__ is an error. Detail pages:
              any 2xx is kept; no answer or non-2xx raises JobDetailError.
"""

import json
from pathlib import Path

import pytest
from conftest import FakeGetPage, page

from ingestion.scrapers.i_scraper import (
    DetailPage,
    JobDetailError,
    ListingError,
    ListingPage,
)
from ingestion.scrapers.jobup_scraper import JobupScraper

FIXTURE: Path = Path(__file__).parent / "fixtures" / "jobup_listing_page.html"
CATEGORY: str = "informatique-telecommunications"
PAGE_3: str = "https://www.jobup.ch/fr/emplois/informatique-telecommunications/?page=3"
JOB: str = "https://www.jobup.ch/fr/emplois/detail/abc/"


def scraper(get_page: FakeGetPage) -> JobupScraper:
    """A jobup scraper on the given fake network."""
    return JobupScraper(get_page, [CATEGORY])


def test_jobs_from_real_page() -> None:
    """A real page gives its total, number of pages and jobs with raw JSON cards."""
    get_page: FakeGetPage = FakeGetPage({PAGE_3: page(content=FIXTURE.read_bytes())})

    result: ListingPage = scraper(get_page).extract_jobs_from_listing(CATEGORY, 3)

    assert get_page.requested == [PAGE_3]
    assert (result.announced_total, result.num_pages, len(result.jobs)) == (
        786,
        40,
        22,
    )
    url, card = result.jobs[0]
    assert url == (
        "https://www.jobup.ch/fr/emplois/detail/18943dd6-c820-41e9-9e37-0da70fd57866/"
    )
    assert json.loads(card)["title"] == "Financial Analyst & AI Engineer"


def test_blocked_listing_is_an_error() -> None:
    """A blocked result page (HTTP 403) raises ListingError."""
    get_page: FakeGetPage = FakeGetPage({PAGE_3: page(status=403)})
    with pytest.raises(ListingError, match="HTTP 403"):
        scraper(get_page).extract_jobs_from_listing(CATEGORY, 3)


def test_listing_without_data_is_an_error() -> None:
    """A result page without the __INIT__ block raises ListingError."""
    get_page: FakeGetPage = FakeGetPage({PAGE_3: page(content=b"<html>Denied</html>")})
    with pytest.raises(ListingError, match="__INIT__"):
        scraper(get_page).extract_jobs_from_listing(CATEGORY, 3)


def test_job_detail_kept_unchanged() -> None:
    """A 2xx detail page is returned with its content, type and status."""
    detail: DetailPage = scraper(FakeGetPage({JOB: page()})).extract_job_detail(JOB)
    assert (detail.content, detail.http_status) == (b"<html>job</html>", 200)


def test_job_detail_errors() -> None:
    """A 404 and a missing answer both raise JobDetailError with the reason."""
    with pytest.raises(JobDetailError, match="HTTP 404"):
        scraper(FakeGetPage({JOB: page(status=404)})).extract_job_detail(JOB)
    with pytest.raises(JobDetailError, match="no answer"):
        scraper(FakeGetPage({})).extract_job_detail(JOB)
