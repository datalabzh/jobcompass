"""
i_site_extraction_uc.py

Description : ce que fournit l'extraction de tout site : une classe par site, avec
              une seule méthode publique, execute.
Règles      : chaque site possède tout son processus (comment il découpe ses offres,
              comment il lit ses pages, ce qu'il journalise) : rien n'est imposé ici
              au-delà de ce que le point d'entrée doit fournir et recevoir.
              Fourni à la création, à l'identique pour tous les sites : source,
              get_page, db_storage (tables), file_storage (fichiers bruts),
              is_test, les garde-fous max_pages / max_jobs (None =
              sans limite), max_failures, now, et options = la table
              [extraction.options] du site.toml, que le site valide lui-même.
              Le site écrit ses données lui-même, dans les tables communes
              (catalog) et avec les contrats communs : c'est le contrat,
              pas le code, qui rend les données des sites comparables.
              L'extraction va chercher les pages et stocke ; le parseur ne fait que
              lire le contenu qu'elle lui envoie. Une page de détail téléchargée
              donne un RawJobDetail avec son bloc brut (ADR-0002 : aucun champ
              choisi ni renommé, c'est le travail de dbt) ; le HTML reste stocké.
              Les pages de détail sont traitées et écrites une par une : un plantage
              ne fait rien refaire de ce qui est déjà écrit.
              execute renvoie un ExtractionReport, de même forme pour tous les sites
              (lu par Dagster).
"""

from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from contracts.components.field_types import RunStatus
from contracts.jobs.log_raw_job_info import LogRawJobInfo
from extraction.interfaces.i_get_page import GetPage
from interfaces.i_use_case import IUseCase
from storage.interfaces.i_db_storage import IDbStorage
from storage.interfaces.i_file_storage import IFileStorage


@dataclass(frozen=True)
class DetailsSummary:
    """Outcome of the detail pages: downloaded, failed, set aside."""

    extracted: int  # pages downloaded
    failed: int  # downloads failed
    set_aside: int  # jobs no longer downloaded (max_failures)


@dataclass(frozen=True)
class ExtractionReport:
    """What a run did, printed as the JSON summary of the command."""

    source: str
    is_test: bool
    max_pages: int | None
    max_jobs: int | None
    status: RunStatus  # failed if any listing failed
    listings: list[LogRawJobInfo]  # one log per listing read
    details: DetailsSummary


class ISiteExtractionUseCase(IUseCase):
    """The whole extraction of one site: listings, then detail pages."""

    def __init__(
        self,
        source: str,
        get_page: GetPage,
        db_storage: IDbStorage,
        file_storage: IFileStorage,
        is_test: bool,
        max_pages: int | None,
        max_jobs: int | None,
        max_failures: int,
        now: Callable[[], datetime],
        options: dict[str, Any],
    ) -> None:
        self.source: str = source
        self.get_page: GetPage = get_page
        self.db_storage: IDbStorage = db_storage
        self.file_storage: IFileStorage = file_storage
        self.is_test: bool = is_test
        self.max_pages: int | None = max_pages
        self.max_jobs: int | None = max_jobs
        self.max_failures: int = max_failures
        self.now: Callable[[], datetime] = now
        self.options: dict[str, Any] = options

    @abstractmethod
    def execute(self) -> ExtractionReport:
        """Extract the site and return the report of the run."""
