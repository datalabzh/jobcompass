"""
i_scraper.py

Description : what every site scraper must provide: the two operations that depend
              on the site.
Rules       : extract_jobs_from_listing: the jobs of one result page of a category.
              extract_job_detail: the raw content of one job detail page.
              How URLs are built and pages are read is each scraper's own business
              (private methods).
              A scraper never implements HTTP nor stores anything: it receives
              get_page (http.py) and its categories (scrapers.toml) when created.
              A result page that cannot be read raises ListingError; a detail page
              that cannot be downloaded raises JobDetailError (with the reason).
              Adding a site = one new file implementing IScraper.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ingestion.http import GetPage


@dataclass(frozen=True)
class ListingPage:
    """The jobs of one result page, with what the site says about the listing."""

    announced_total: int | None  # jobs announced by the site
    num_pages: int
    jobs: list[tuple[str, str]]  # (job url, raw JSON card)


@dataclass(frozen=True)
class DetailPage:
    """The raw content of one job detail page."""

    content: bytes
    content_type: str
    http_status: int


class ListingError(Exception):
    """A result page could not be read as expected (blocked, changed...)."""


class JobDetailError(Exception):
    """A job detail page could not be downloaded (no answer, HTTP error...)."""


class IScraper(ABC):
    """Site-specific part of the ingestion: result pages and job detail pages."""

    name: str  # source slug, e.g. 'jobup'
    version: str  # version of the scraper code, recorded with each page

    def __init__(self, get_page: GetPage, categories: list[str]) -> None:
        self.get_page: GetPage = get_page
        self.categories: list[str] = categories

    @abstractmethod
    def extract_jobs_from_listing(self, category: str, page: int) -> ListingPage:
        """Return the jobs of result page `page` (from 1) of a category."""

    @abstractmethod
    def extract_job_detail(self, url: str) -> DetailPage:
        """Return the raw content of a job detail page."""
