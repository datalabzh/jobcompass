"""
jobup_extraction_uc.py

Description : extraction complète de jobup.ch : va chercher les pages, les envoie
              au parseur, stocke ce qu'il en tire, brut (ADR-0002). Les jobs de
              chaque catégorie, puis la fiche de chaque job encore à télécharger.
Règles      : JobupExtractionUseCase (déclarée dans le site.toml) lance les deux étapes,
              chacune une classe interne à ce module avec sa méthode execute :
              _JobupJobInfosUseCase (étape 1) et _JobupJobDetailsUseCase (étape 2).
              Seules ces classes font des requêtes et écrivent ; le parseur
              (JobupParser, utilisé directement) ne fait que lire le contenu reçu.
              options (site.toml, [extraction.options]) : categories (slugs d'URL),
              validées avant toute requête.
              1. Pour chaque catégorie, page par page, de la page 1 à la dernière
                 (au plus max_pages) : la page est téléchargée, parsée ('job_info'),
                 et ses jobs écrits aussitôt (une ligne RawJobInfo par job, avec sa
                 carte JSON brute). Un LogRawJobInfo termine la catégorie :
                 completed, ou failed avec l'erreur. Une catégorie en échec n'arrête
                 ni les autres ni l'étape 2.
              2. Jobs à télécharger = jobs vus - déjà téléchargés - mis de côté
                 (max_failures échecs), au plus max_jobs, un par un, chacun écrit
                 dès qu'il est traité : un plantage ne fait rien refaire de ce qui
                 est écrit.
                 Succès (réponse 2xx) : le HTML d'abord, sous son raw_hash, puis un
                 RawJobDetail avec le bloc brut de la page (parseur, 'job_detail') ;
                 échec : un LogRawJobDetail.
              name + version = enregistrés avec chaque page (scraper,
              scraper_version) ; changer la façon de télécharger ou de lire les
              pages (parseur compris) = monter version.
"""

import json
import uuid
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from catalog import Table
from contracts import (
    LogRawJobDetail,
    LogRawJobInfo,
    RawJobDetail,
    RawJobInfo,
    RunStatus,
    compute_raw_hash,
)
from extraction.interfaces import (
    DetailsSummary,
    ExtractionReport,
    GetPage,
    ISiteExtractionUseCase,
    Page,
    PageFetchError,
)
from extraction.jobup.jobup_parser import (
    JOB_DETAIL,
    JOB_INFO,
    JobupJobDetail,
    JobupListing,
    JobupParser,
)
from interfaces import IUseCase
from storage.interfaces.i_db_storage import IDbStorage
from storage.interfaces.i_file_storage import IFileStorage

LISTING_URL: str = "https://www.jobup.ch/fr/emplois/{category}/?page={page}"


class ListingError(Exception):
    """A result page could not be downloaded (blocked, error status...)."""


class JobupOptions(BaseModel):
    """The [extraction.options] table of jobup's site.toml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    categories: list[str] = Field(min_length=1, description="Category URL slugs")


class JobupExtractionUseCase(ISiteExtractionUseCase):
    """Extracts jobup.ch: the jobs of every category, then their detail pages."""

    name: str = "jobup_extraction"  # recorded with every page downloaded
    version: str = "0.2.0"  # recorded too: change it with the download or parser

    def execute(self) -> ExtractionReport:
        """Record the jobs of every category, then download their pages."""
        options: JobupOptions = JobupOptions(**self.options)  # before any request
        parser: JobupParser = JobupParser()
        logs: list[LogRawJobInfo] = _JobupJobInfosUseCase(
            source=self.source,
            get_page=self.get_page,
            db_storage=self.db_storage,
            parser=parser,
            is_test=self.is_test,
            max_pages=self.max_pages,
            now=self.now,
            categories=options.categories,
        ).execute()
        details: DetailsSummary = _JobupJobDetailsUseCase(
            source=self.source,
            get_page=self.get_page,
            db_storage=self.db_storage,
            file_storage=self.file_storage,
            parser=parser,
            is_test=self.is_test,
            max_jobs=self.max_jobs,
            max_failures=self.max_failures,
            now=self.now,
            scraper=self.name,
            scraper_version=self.version,
        ).execute()
        failed: bool = any(log.status == RunStatus.FAILED for log in logs)
        return ExtractionReport(
            source=self.source,
            is_test=self.is_test,
            max_pages=self.max_pages,
            max_jobs=self.max_jobs,
            status=RunStatus.FAILED if failed else RunStatus.COMPLETED,
            listings=logs,
            details=details,
        )


# --- 1. raw job infos, category by category, page by page -----------------------


class _JobupJobInfosUseCase(IUseCase):
    """Reads every result page of every category and stores their jobs."""

    def __init__(
        self,
        source: str,
        get_page: GetPage,
        db_storage: IDbStorage,
        parser: JobupParser,
        is_test: bool,
        max_pages: int | None,
        now: Callable[[], datetime],
        categories: list[str],
    ) -> None:
        self.source: str = source
        self.get_page: GetPage = get_page
        self.db_storage: IDbStorage = db_storage
        self.parser: JobupParser = parser
        self.is_test: bool = is_test
        self.max_pages: int | None = max_pages
        self.now: Callable[[], datetime] = now
        self.categories: list[str] = categories

    def execute(self) -> list[LogRawJobInfo]:
        """Extract every category; one log per category, failed or completed."""
        return [self._extract_category(category) for category in self.categories]

    def _extract_category(self, category: str) -> LogRawJobInfo:
        """Read and store the result pages of a category; store and return its log."""
        run_id: str = str(uuid.uuid4())
        started_at: datetime = self.now()
        urls: list[str] = []
        pages_read: int = 0
        total: int | None = None
        error: Exception | None = None
        try:
            for listing in self._listings(category):
                self._store_listing(listing, category, run_id, urls)
                pages_read += 1
                total = listing.total if total is None else total
        except Exception as caught:
            error = caught
        log: LogRawJobInfo = LogRawJobInfo(
            run_id=run_id,
            source=self.source,
            is_test=self.is_test,
            listing_params={"category": category},
            started_at=started_at,
            finished_at=self.now(),
            status=RunStatus.COMPLETED if error is None else RunStatus.FAILED,
            error=None if error is None else f"{type(error).__name__}: {error}",
            announced_total=total,
            pages_read=pages_read,
            jobs_seen=len(urls),
            distinct_urls=len(set(urls)),
        )
        self.db_storage.append(Table.LOG_RAW_JOB_INFO, [log])
        return log

    def _listings(self, category: str) -> Iterator[JobupListing]:
        """The result pages of a category, one by one, up to max_pages."""
        first: JobupListing = self._read_listing(category, 1)
        yield first
        last: int = first.num_pages
        if self.max_pages is not None:
            last = min(last, self.max_pages)
        for page in range(2, last + 1):
            yield self._read_listing(category, page)

    def _read_listing(self, category: str, page: int) -> JobupListing:
        """Download one result page and have it parsed."""
        url: str = LISTING_URL.format(category=category, page=page)
        answer: Page = self.get_page(url)
        if answer.http_status != 200:
            raise ListingError(f"HTTP {answer.http_status} on {url}")
        listing: object = self.parser.parse(JOB_INFO, answer.content)
        if not isinstance(listing, JobupListing):
            raise TypeError(f"{self.parser.name} returned {type(listing).__name__}")
        return listing

    def _store_listing(
        self, listing: JobupListing, category: str, run_id: str, urls: list[str]
    ) -> None:
        """Write one RawJobInfo per job of the page, and note their URLs."""
        infos: list[RawJobInfo] = [
            RawJobInfo(
                run_id=run_id,
                source=self.source,
                is_test=self.is_test,
                url=job.url,
                seen_at=self.now(),
                listing_params={"category": category},
                card=json.dumps(job.card, ensure_ascii=False),
            )
            for job in listing.jobs
        ]
        self.db_storage.append(Table.RAW_JOB_INFO, infos)
        urls.extend(info.url for info in infos)


# --- 2. raw job details, one by one ------------------------------------------------


class _JobupJobDetailsUseCase(IUseCase):
    """Downloads and stores the detail pages still to extract, with their block."""

    def __init__(
        self,
        source: str,
        get_page: GetPage,
        db_storage: IDbStorage,
        file_storage: IFileStorage,
        parser: JobupParser,
        is_test: bool,
        max_jobs: int | None,
        max_failures: int,
        now: Callable[[], datetime],
        scraper: str,
        scraper_version: str,
    ) -> None:
        self.source: str = source
        self.get_page: GetPage = get_page
        self.db_storage: IDbStorage = db_storage
        self.file_storage: IFileStorage = file_storage
        self.parser: JobupParser = parser
        self.is_test: bool = is_test
        self.max_jobs: int | None = max_jobs
        self.max_failures: int = max_failures
        self.now: Callable[[], datetime] = now
        self.scraper: str = scraper
        self.scraper_version: str = scraper_version

    def execute(self) -> DetailsSummary:
        """Download the pending pages one by one, storing each one."""
        to_extract, set_aside = self._pending_urls()
        counts: Counter[str] = Counter()
        for url in to_extract[: self.max_jobs]:
            counts.update(self._extract_detail(url))
        return DetailsSummary(
            extracted=counts["extracted"],
            failed=counts["failed"],
            set_aside=set_aside,
        )

    def _pending_urls(self) -> tuple[list[str], int]:
        """URLs still to download, in order of first sighting; number set aside."""
        seen: list[dict[str, Any]] = sorted(
            self._read(Table.RAW_JOB_INFO, ["url", "seen_at"]),
            key=lambda row: row["seen_at"],
        )
        downloaded: set[str] = {
            row["url"] for row in self._read(Table.RAW_JOB_DETAIL, ["url"])
        }
        failures: Counter[str] = Counter(
            row["url"] for row in self._read(Table.LOG_RAW_JOB_DETAIL, ["url"])
        )
        to_extract: list[str] = []
        set_aside: int = 0
        for url in dict.fromkeys(str(row["url"]) for row in seen):
            if url in downloaded:
                continue
            if failures[url] >= self.max_failures:
                set_aside += 1
            else:
                to_extract.append(url)
        return to_extract, set_aside

    def _read(self, table: str, columns: list[str]) -> list[dict[str, Any]]:
        """The given columns of a table, for this source."""
        return self.db_storage.read(table, self.source, columns=columns)

    def _extract_detail(self, url: str) -> Counter[str]:
        """Download and store one page; what happened, as counts."""
        downloaded: RawJobDetail | LogRawJobDetail = self._download(url)
        if isinstance(downloaded, LogRawJobDetail):
            self.db_storage.append(Table.LOG_RAW_JOB_DETAIL, [downloaded])
            return Counter(failed=1)
        self.db_storage.append(Table.RAW_JOB_DETAIL, [downloaded])
        return Counter(extracted=1)

    def _download(self, url: str) -> RawJobDetail | LogRawJobDetail:
        """Download one page and store its HTML; its RawJobDetail, or the failure."""
        attempted_at: datetime = self.now()
        try:
            answer: Page = self.get_page(url)
        except PageFetchError as error:
            return self._download_failure(url, attempted_at, f"no answer: {error}")
        if not 200 <= answer.http_status < 300:
            return self._download_failure(
                url, attempted_at, f"HTTP {answer.http_status}"
            )
        raw_hash: str = compute_raw_hash(answer.content)
        file_name: str = f"{Table.RAW_JOB_DETAIL_HTML}/{raw_hash}.html"
        if not self.file_storage.has_file(file_name):
            self.file_storage.put_file(file_name, answer.content)
        detail: object = self.parser.parse(JOB_DETAIL, answer.content)
        if not isinstance(detail, JobupJobDetail):
            raise TypeError(f"{self.parser.name} returned {type(detail).__name__}")
        return RawJobDetail(
            source=self.source,
            is_test=self.is_test,
            url=url,
            raw_hash=raw_hash,
            content_type=answer.content_type,
            fetched_at=attempted_at,
            http_status=answer.http_status,
            scraper=self.scraper,
            scraper_version=self.scraper_version,
            payload_format=detail.payload_format,
            payload=detail.payload,
        )

    def _download_failure(
        self, url: str, attempted_at: datetime, error: str
    ) -> LogRawJobDetail:
        """The log of a failed download."""
        return LogRawJobDetail(
            source=self.source,
            is_test=self.is_test,
            url=url,
            attempted_at=attempted_at,
            error=error,
        )
