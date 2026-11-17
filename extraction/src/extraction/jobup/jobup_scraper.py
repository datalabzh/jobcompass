"""
jobup_scraper.py

Description : lecture des pages de résultats de jobup.ch : les jobs d'une page d'une
              catégorie, et le nombre de pages.
Règles      : pages publiques uniquement (robots.txt : /api/ est interdit).
              Catégorie donnée par son slug d'URL, ex. 'informatique-telecommunications'
              (le paramètre ?category= n'est pas appliqué par le serveur).
              Tout autre statut que HTTP 200 est une erreur. La page embarque ses
              données en JSON dans un script `__INIT__ = {...}` :
                vacancy.results.main.meta     totalHits, numPages
                vacancy.results.main.results  les jobs de la page
              Chaque job est rendu tel quel (dictionnaire JSON) ; son URL est
              construite à partir de son id.
              Une page au-delà de la dernière réaffiche la page 1 : le nombre de pages
              se lit sur la page 1, jamais en cherchant une page vide.
              Aucune écriture ici : le scraper lit, JobupExtraction stocke.
"""

import json
from dataclasses import dataclass
from typing import Any

from interfaces import GetPage, Page

LISTING_URL: str = "https://www.jobup.ch/fr/emplois/{category}/?page={page}"
JOB_URL: str = "https://www.jobup.ch/fr/emplois/detail/{id}/"
INIT_MARKER: str = "__INIT__"


class ListingError(Exception):
    """A result page could not be read as expected (blocked, changed...)."""


@dataclass(frozen=True)
class JobupListing:
    """One result page: its jobs as given by jobup, and the counts of the category."""

    num_pages: int
    total: int | None
    jobs: list[dict[str, Any]]


class JobupScraper:
    """Reads jobup.ch result pages through their __INIT__ JSON."""

    def __init__(self, get_page: GetPage) -> None:
        self.get_page: GetPage = get_page

    def read_listing(self, category: str, page: int) -> JobupListing:
        """The jobs of one result page of a category, and the page count."""
        url: str = LISTING_URL.format(category=category, page=page)
        answer: Page = self.get_page(url)
        if answer.http_status != 200:
            raise ListingError(f"HTTP {answer.http_status} on {url}")
        return self._to_listing(self._extract_raw_data(answer.content.decode("utf-8")))

    def job_url(self, job: dict[str, Any]) -> str:
        """The URL of a job's detail page, built from its id."""
        return JOB_URL.format(id=job["id"])

    def _extract_raw_data(self, html: str) -> dict[str, Any]:
        """Extract vacancy.results.main from the __INIT__ JSON of the page."""
        start: int = html.find(INIT_MARKER)
        if start == -1:
            raise ListingError("no __INIT__ block")
        try:
            init: dict[str, Any]
            init, _ = json.JSONDecoder().raw_decode(html, html.index("{", start))
            return init["vacancy"]["results"]["main"]
        except (KeyError, TypeError, ValueError) as error:
            raise ListingError(f"unreadable __INIT__ block: {error!r}") from error

    def _to_listing(self, data: dict[str, Any]) -> JobupListing:
        """The page count, the announced total and the jobs of the page."""
        try:
            return JobupListing(
                num_pages=int(data["meta"]["numPages"]),
                total=data["meta"].get("totalHits"),
                jobs=list(data["results"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ListingError(f"unexpected __INIT__ content: {error!r}") from error
