"""
jobup_job_infos.py

Description : job infos de jobup.ch : les jobs des pages de résultats d'une
              catégorie.
Règles      : pages publiques uniquement (robots.txt : /api/ est interdit).
              Catégorie donnée par son slug d'URL, ex. 'informatique-telecommunications'
              (le paramètre ?category= n'est pas appliqué par le serveur).
              Tout autre statut que HTTP 200 est une erreur. La page embarque ses
              données en JSON dans un script `__INIT__ = {...}` :
                vacancy.results.main.meta     totalHits, numPages
                vacancy.results.main.results  les jobs de la page
              Chaque job est conservé en JSON brut ; son URL est construite à
              partir de son id.
              Une page au-delà de la dernière réaffiche la page 1 : le nombre de
              pages vient de la page 1, jamais d'une page vide.
"""

import json
from collections.abc import Iterator
from typing import Any

from extraction.http import Page
from extraction.interfaces.i_job_infos_extractor import (
    IJobInfosExtractor,
    JobInfoPage,
    ListingError,
)

LISTING_URL: str = "https://www.jobup.ch/fr/emplois/{category}/?page={page}"
JOB_URL: str = "https://www.jobup.ch/fr/emplois/detail/{id}/"
INIT_MARKER: str = "__INIT__"


class JobupJobInfos(IJobInfosExtractor):
    """Reads jobup.ch result pages through their __INIT__ JSON."""

    def execute(self, category: str, run_id: str) -> Iterator[JobInfoPage]:
        """Yield the result pages of a category, from page 1 to the last one."""
        page_number: int = 1
        num_pages: int = 1  # known once page 1 is read
        while page_number <= num_pages:
            data: dict[str, Any] = self._read_listing(category, page_number)
            if page_number == 1:
                num_pages = self._num_pages(data)
            yield self._to_page(data, run_id, category)
            page_number += 1

    def _read_listing(self, category: str, page: int) -> dict[str, Any]:
        """The search results (vacancy.results.main) of one result page."""
        url: str = LISTING_URL.format(category=category, page=page)
        answer: Page = self.get_page(url)
        if answer.http_status != 200:
            raise ListingError(f"HTTP {answer.http_status} on {url}")
        return self._extract_raw_data(answer.content.decode("utf-8"))

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

    def _num_pages(self, data: dict[str, Any]) -> int:
        """Number of result pages of the category, as given by page 1."""
        try:
            return int(data["meta"]["numPages"])
        except (KeyError, TypeError, ValueError) as error:
            raise ListingError(f"no numPages: {error!r}") from error

    def _to_page(self, data: dict[str, Any], run_id: str, category: str) -> JobInfoPage:
        """One JobInfo per job (URL + raw JSON card), with the announced total."""
        try:
            return JobInfoPage(
                announced_total=data["meta"].get("totalHits"),
                job_infos=[
                    self._job_info(
                        run_id,
                        category,
                        JOB_URL.format(id=job["id"]),
                        json.dumps(job, ensure_ascii=False),
                    )
                    for job in data["results"]
                ],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ListingError(f"unexpected __INIT__ content: {error!r}") from error
