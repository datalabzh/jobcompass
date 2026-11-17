"""
test_jobup_scraper.py

Description : tests de la lecture des pages de résultats de jobup.ch.
Règles      : s'exécute sur une vraie page de résultats enregistrée dans fixtures/,
              servie par un faux get_page (pas de réseau). L'URL utilise le slug de
              catégorie ; une réponse non 200 ou une page sans __INIT__ est une erreur.
"""

from pathlib import Path

import pytest
from conftest import FakeGetPage, page

from extraction.jobup.jobup_scraper import JobupListing, JobupScraper, ListingError

FIXTURE: Path = Path(__file__).parent / "fixtures" / "jobup_listing_page.html"
PAGE_1: str = "https://www.jobup.ch/fr/emplois/informatique-telecommunications/?page=1"
CATEGORY: str = "informatique-telecommunications"


def test_real_listing_page() -> None:
    """A real page gives its page count, its total and its jobs as given by jobup."""
    get_page: FakeGetPage = FakeGetPage({PAGE_1: page(content=FIXTURE.read_bytes())})
    scraper: JobupScraper = JobupScraper(get_page)

    listing: JobupListing = scraper.read_listing(CATEGORY, 1)

    assert get_page.requested == [PAGE_1]
    assert (listing.num_pages, listing.total, len(listing.jobs)) == (40, 786, 22)
    assert listing.jobs[0]["title"] == "Financial Analyst & AI Engineer"
    assert scraper.job_url(listing.jobs[0]) == (
        "https://www.jobup.ch/fr/emplois/detail/18943dd6-c820-41e9-9e37-0da70fd57866/"
    )


def test_blocked_listing_is_an_error() -> None:
    """A blocked result page (HTTP 403) raises ListingError."""
    scraper: JobupScraper = JobupScraper(FakeGetPage({PAGE_1: page(status=403)}))
    with pytest.raises(ListingError, match="HTTP 403"):
        scraper.read_listing(CATEGORY, 1)


def test_listing_without_data_is_an_error() -> None:
    """A result page without the __INIT__ block raises ListingError."""
    get_page: FakeGetPage = FakeGetPage({PAGE_1: page(content=b"<html>Denied</html>")})
    with pytest.raises(ListingError, match="__INIT__"):
        JobupScraper(get_page).read_listing(CATEGORY, 1)
