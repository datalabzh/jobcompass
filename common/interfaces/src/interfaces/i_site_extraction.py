"""
i_site_extraction.py

Description : ce que fournit l'extraction de tout site : une classe par site, avec
              une seule méthode publique, execute.
Règles      : chaque site possède tout son processus (comment il découpe ses offres,
              comment il lit ses pages, ce qu'il journalise) : rien n'est imposé ici
              au-delà de ce que le point d'entrée doit fournir et recevoir.
              Fourni à la création, à l'identique pour tous les sites : source,
              get_page, storage, is_test, les garde-fous max_pages / max_jobs (None =
              sans limite), max_failures, batch_size, now, et options = la table
              [extraction.options] du site.toml, que le site valide lui-même.
              Le site écrit ses données lui-même, dans les tables communes
              (catalog) et avec les contrats communs : c'est le contrat,
              pas le code, qui rend les données des sites comparables.
              execute renvoie un ExtractionReport, de même forme pour tous les sites
              (lu par Dagster).
"""

from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from contracts import RawJobInfoExtractionLog, RunStatus
from interfaces.i_get_page import GetPage
from interfaces.i_storage import IStorage
from interfaces.i_use_case import IUseCase


@dataclass(frozen=True)
class DetailsSummary:
    """Outcome of the detail downloads: pages downloaded, failures, set aside."""

    extracted: int
    failed: int
    set_aside: int


@dataclass(frozen=True)
class ExtractionReport:
    """What a run did, printed as the JSON summary of the command."""

    source: str
    is_test: bool
    max_pages: int | None
    max_jobs: int | None
    status: RunStatus  # failed if any listing failed
    listings: list[RawJobInfoExtractionLog]  # one log per listing read
    details: DetailsSummary


class ISiteExtraction(IUseCase):
    """The whole extraction of one site: listings, then detail pages."""

    def __init__(
        self,
        source: str,
        get_page: GetPage,
        storage: IStorage,
        is_test: bool,
        max_pages: int | None,
        max_jobs: int | None,
        max_failures: int,
        batch_size: int,
        now: Callable[[], datetime],
        options: dict[str, Any],
    ) -> None:
        self.source: str = source
        self.get_page: GetPage = get_page
        self.storage: IStorage = storage
        self.is_test: bool = is_test
        self.max_pages: int | None = max_pages
        self.max_jobs: int | None = max_jobs
        self.max_failures: int = max_failures
        self.batch_size: int = batch_size
        self.now: Callable[[], datetime] = now
        self.options: dict[str, Any] = options

    @abstractmethod
    def execute(self) -> ExtractionReport:
        """Extract the site and return the report of the run."""
