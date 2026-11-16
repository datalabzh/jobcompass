"""
i_job_infos_extractor.py

Description : ce que doit fournir tout site pour ses pages de résultats : les job
              infos d'une catégorie, page par page.
Règles      : execute(category, run_id) renvoie les pages au fil de l'eau (yield),
              de la page 1 à la dernière : une seule page en mémoire à la fois.
              Chaque page est un JobInfoPage : le total annoncé par le site et la
              liste des JobInfo de la page.
              Le site ne stocke rien et ne gère pas les limites : le point d'entrée
              vérifie chaque page, l'écrit, et arrête la lecture à max_pages.
              Une page illisible lève ListingError.
              Les JobInfo se construisent avec _job_info : source, is_test et date
              sont remplis à l'identique pour tous les sites.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from contracts import JobInfo
from extraction.http import GetPage


@dataclass(frozen=True)
class JobInfoPage:
    """The jobs of one result page, with the total announced by the site."""

    announced_total: int | None
    job_infos: list[JobInfo]


class ListingError(Exception):
    """A result page could not be read as expected (blocked, changed...)."""


class IJobInfosExtractor(ABC):
    """Site-specific reading of the result pages of a category."""

    def __init__(
        self,
        get_page: GetPage,
        source: str,
        is_test: bool,
        now: Callable[[], datetime],
    ) -> None:
        self.get_page: GetPage = get_page
        self.source: str = source
        self.is_test: bool = is_test
        self.now: Callable[[], datetime] = now

    @abstractmethod
    def execute(self, category: str, run_id: str) -> Iterator[JobInfoPage]:
        """Yield the result pages of a category, from page 1 to the last one."""

    def _job_info(self, run_id: str, category: str, url: str, card: str) -> JobInfo:
        """A JobInfo of this site, seen now in a category."""
        return JobInfo(
            run_id=run_id,
            source=self.source,
            is_test=self.is_test,
            url=url,
            seen_at=self.now(),
            listing_params={"category": category},
            card=card,
        )
