"""
jobup_scraper.py

Description : scraper of jobup.ch: result pages and job detail pages.
Rules       : public pages only (robots.txt: /api/ is forbidden).
              Category given by its URL slug, e.g. 'informatique-telecommunications'
              (the ?category= parameter is not applied by the server).
              Result pages: anything but HTTP 200 is an error. The page embeds its
              data as JSON in a `__INIT__ = {...}` script:
                vacancy.results.main.meta     totalHits, numPages
                vacancy.results.main.results  the jobs of the page
              Each job is kept as raw JSON; its URL is built from its id.
              A page beyond the last one shows page 1 again: the number of pages
              comes from page 1, never from an empty page.
              Detail pages: any 2xx answer is kept unchanged.
"""

import json
from typing import Any

from ingestion.http import Page, PageFetchError
from ingestion.scrapers.i_scraper import (
    DetailPage,
    IScraper,
    JobDetailError,
    ListingError,
    ListingPage,
)

LISTING_URL: str = "https://www.jobup.ch/fr/emplois/{category}/?page={page}"
JOB_URL: str = "https://www.jobup.ch/fr/emplois/detail/{id}/"
INIT_MARKER: str = "__INIT__"


class JobupScraper(IScraper):
    """Reads jobup.ch result pages (through their __INIT__ JSON) and job pages."""

    name: str = "jobup"
    version: str = "0.1.0"

    # --- public -----------------------------------------------------------------

    def extract_jobs_from_listing(self, category: str, page: int) -> ListingPage:
        """Return the jobs of result page `page` of a category slug."""
        html: str = self._download_page_content(self._build_listing_url(category, page))
        return self._split_raw_data_into_jobs(self._extract_raw_data(html))

    def extract_job_detail(self, url: str) -> DetailPage:
        """Return the raw content of a job detail page; any 2xx answer is kept."""
        try:
            answer: Page = self.get_page(url)
        except PageFetchError as error:
            raise JobDetailError(f"no answer: {error}") from error
        if not 200 <= answer.http_status < 300:
            raise JobDetailError(f"HTTP {answer.http_status}")
        return DetailPage(
            content=answer.content,
            content_type=answer.content_type,
            http_status=answer.http_status,
        )

    # --- result pages -----------------------------------------------------------

    def _build_listing_url(self, category: str, page: int) -> str:
        """URL of result page `page` of a category slug."""
        return LISTING_URL.format(category=category, page=page)

    def _download_page_content(self, url: str) -> str:
        """Download a result page; anything but HTTP 200 is an error."""
        answer: Page = self.get_page(url)
        if answer.http_status != 200:
            raise ListingError(f"HTTP {answer.http_status} on {url}")
        return answer.content.decode("utf-8")

    def _extract_raw_data(self, html: str) -> dict[str, Any]:
        """Extract the search results (vacancy.results.main) from the __INIT__ JSON."""
        start: int = html.find(INIT_MARKER)
        if start == -1:
            raise ListingError("no __INIT__ block")
        try:
            init: dict[str, Any]
            init, _ = json.JSONDecoder().raw_decode(html, html.index("{", start))
            return init["vacancy"]["results"]["main"]
        except (KeyError, TypeError, ValueError) as error:
            raise ListingError(f"unreadable __INIT__ block: {error!r}") from error

    def _split_raw_data_into_jobs(self, data: dict[str, Any]) -> ListingPage:
        """One (url, raw JSON card) per job, with the total and number of pages."""
        try:
            jobs: list[tuple[str, str]] = [
                (JOB_URL.format(id=job["id"]), json.dumps(job, ensure_ascii=False))
                for job in data["results"]
            ]
            return ListingPage(
                announced_total=data["meta"].get("totalHits"),
                num_pages=int(data["meta"]["numPages"]),
                jobs=jobs,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ListingError(f"unexpected __INIT__ content: {error!r}") from error
