"""
jobup_extraction.py

Description : extraction complète de jobup.ch : va chercher les pages, les envoie
              au parseur, stocke ce qu'il en tire. Les jobs de chaque catégorie,
              puis la fiche de chaque job encore à télécharger.
Règles      : JobupExtraction (déclarée dans le site.toml) lance les deux étapes,
              chacune une classe interne à ce module avec sa méthode execute :
              _JobupJobInfos (étape 1) et _JobupJobDetails (étapes 2 et 3).
              Seules ces classes font des requêtes et écrivent ; le parseur
              (options.parser, un IParser) ne fait que lire le contenu reçu.
              options (site.toml, [extraction.options]) : categories (slugs d'URL)
              et parser (module:Classe), validés avant toute requête.
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
                 Succès (réponse 2xx) : le HTML d'abord, sous son raw_hash, puis le
                 reçu RawJobDetail ; échec : un LogRawJobDetail.
              3. Chaque fiche téléchargée est aussitôt parsée ('job_detail') : un
                 ExtractedJob, ou un LogExtractedJob si elle est
                 illisible ; le téléchargement reste acquis dans les deux cas.
                 Le brut est conservé : reparser l'existant viendra plus tard.
              version = version de ce code, enregistrée avec chaque page ; changer
              la façon de télécharger = monter version.
"""

import importlib
import json
import uuid
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from catalog import Table
from contracts import (
    ExtractedJob,
    LogExtractedJob,
    LogRawJobDetail,
    LogRawJobInfo,
    RawJobDetail,
    RawJobInfo,
    RunStatus,
    compute_raw_hash,
)
from extraction.jobup.jobup_parser import (
    JOB_DETAIL,
    JOB_INFO,
    JobupJobDetail,
    JobupListing,
)
from interfaces import (
    DetailsSummary,
    ExtractionReport,
    GetPage,
    IParser,
    ISiteExtraction,
    IStorage,
    IUseCase,
    Page,
    PageFetchError,
    ParsingError,
)

LISTING_URL: str = "https://www.jobup.ch/fr/emplois/{category}/?page={page}"


class ListingError(Exception):
    """A result page could not be downloaded (blocked, error status...)."""


class JobupOptions(BaseModel):
    """The [extraction.options] table of jobup's site.toml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    categories: list[str] = Field(min_length=1, description="Category URL slugs")
    parser: type[IParser] = Field(description="module:Class of the parser")

    @field_validator("parser", mode="before")
    @classmethod
    def _import_parser(cls, path: object) -> object:
        """Import the class named 'module:Class'."""
        if not isinstance(path, str):
            return path
        module_name, _, class_name = path.partition(":")
        try:
            return getattr(importlib.import_module(module_name), class_name)
        except (ImportError, AttributeError, ValueError) as error:
            raise ValueError(f"parser not found: '{path}' ({error})") from error


class JobupExtraction(ISiteExtraction):
    """Extracts jobup.ch: the jobs of every category, then their detail pages."""

    version: str = "0.1.0"  # recorded with every page downloaded

    def execute(self) -> ExtractionReport:
        """Record the jobs of every category, then download and parse their pages."""
        options: JobupOptions = JobupOptions(**self.options)  # before any request
        parser: IParser = options.parser()
        logs: list[LogRawJobInfo] = _JobupJobInfos(
            source=self.source,
            get_page=self.get_page,
            storage=self.storage,
            parser=parser,
            is_test=self.is_test,
            max_pages=self.max_pages,
            now=self.now,
            categories=options.categories,
        ).execute()
        details: DetailsSummary = _JobupJobDetails(
            source=self.source,
            get_page=self.get_page,
            storage=self.storage,
            parser=parser,
            is_test=self.is_test,
            max_jobs=self.max_jobs,
            max_failures=self.max_failures,
            now=self.now,
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


class _JobupJobInfos(IUseCase):
    """Reads every result page of every category and stores their jobs."""

    def __init__(
        self,
        source: str,
        get_page: GetPage,
        storage: IStorage,
        parser: IParser,
        is_test: bool,
        max_pages: int | None,
        now: Callable[[], datetime],
        categories: list[str],
    ) -> None:
        self.source: str = source
        self.get_page: GetPage = get_page
        self.storage: IStorage = storage
        self.parser: IParser = parser
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
        self.storage.append(Table.LOG_RAW_JOB_INFO, [log])
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
        self.storage.append(Table.RAW_JOB_INFO, infos)
        urls.extend(info.url for info in infos)


# --- 2. and 3. raw job details, one by one, parsed at once ------------------------


class _JobupJobDetails(IUseCase):
    """Downloads, stores and parses the detail pages still to extract."""

    def __init__(
        self,
        source: str,
        get_page: GetPage,
        storage: IStorage,
        parser: IParser,
        is_test: bool,
        max_jobs: int | None,
        max_failures: int,
        now: Callable[[], datetime],
        scraper_version: str,
    ) -> None:
        self.source: str = source
        self.get_page: GetPage = get_page
        self.storage: IStorage = storage
        self.parser: IParser = parser
        self.is_test: bool = is_test
        self.max_jobs: int | None = max_jobs
        self.max_failures: int = max_failures
        self.now: Callable[[], datetime] = now
        self.scraper_version: str = scraper_version

    def execute(self) -> DetailsSummary:
        """Download and parse the pending pages one by one, storing each one."""
        to_extract, set_aside = self._pending_urls()
        counts: Counter[str] = Counter()
        for url in to_extract[: self.max_jobs]:
            counts.update(self._extract_detail(url))
        return DetailsSummary(
            extracted=counts["extracted"],
            failed=counts["failed"],
            set_aside=set_aside,
            parsed=counts["parsed"],
            parse_failed=counts["parse_failed"],
        )

    def _pending_urls(self) -> tuple[list[str], int]:
        """URLs still to download, in order of first sighting; number set aside."""
        seen: list[dict[str, Any]] = sorted(
            self.storage.read(Table.RAW_JOB_INFO, self.source),
            key=lambda row: row["seen_at"],
        )
        downloaded: set[str] = {
            row["url"] for row in self.storage.read(Table.RAW_JOB_DETAIL, self.source)
        }
        failures: Counter[str] = Counter(
            row["url"]
            for row in self.storage.read(Table.LOG_RAW_JOB_DETAIL, self.source)
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

    def _extract_detail(self, url: str) -> Counter[str]:
        """Download, store and parse one page; what happened, as counts."""
        downloaded: tuple[RawJobDetail, bytes] | LogRawJobDetail = self._download(url)
        if isinstance(downloaded, LogRawJobDetail):
            self.storage.append(Table.LOG_RAW_JOB_DETAIL, [downloaded])
            return Counter(failed=1)
        receipt, content = downloaded
        self.storage.append(Table.RAW_JOB_DETAIL, [receipt])
        parsed: ExtractedJob | LogExtractedJob = self._parse(receipt, content)
        if isinstance(parsed, LogExtractedJob):
            self.storage.append(Table.LOG_EXTRACTED_JOB, [parsed])
            return Counter(extracted=1, parse_failed=1)
        self.storage.append(Table.EXTRACTED_JOB, [parsed])
        return Counter(extracted=1, parsed=1)

    def _download(self, url: str) -> tuple[RawJobDetail, bytes] | LogRawJobDetail:
        """Download one page and store its HTML; receipt and content, or failure."""
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
        if not self.storage.has_file(file_name):
            self.storage.put_file(file_name, answer.content)
        receipt: RawJobDetail = RawJobDetail(
            source=self.source,
            is_test=self.is_test,
            url=url,
            raw_hash=raw_hash,
            content_type=answer.content_type,
            fetched_at=attempted_at,
            http_status=answer.http_status,
            scraper_version=self.scraper_version,
        )
        return receipt, answer.content

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

    def _parse(
        self, receipt: RawJobDetail, content: bytes
    ) -> ExtractedJob | LogExtractedJob:
        """The ExtractedJob of a downloaded page, or the log of its failure."""
        parsed_at: datetime = self.now()
        try:
            detail: object = self.parser.parse(JOB_DETAIL, content)
            if not isinstance(detail, JobupJobDetail):
                raise TypeError(f"{self.parser.name} returned {type(detail).__name__}")
            return ExtractedJob(
                source=self.source,
                is_test=self.is_test,
                url=receipt.url,
                raw_hash=receipt.raw_hash,
                parser=self.parser.name,
                parser_version=self.parser.version,
                parsed_at=parsed_at,
                title=detail.title,
                company=detail.company,
                description=detail.description,
                date_posted=detail.date_posted,
                postal_code=detail.postal_code,
                employment_types=detail.employment_types,
                categories=detail.categories,
                declared_skills=detail.declared_skills,
            )
        except (ParsingError, ValidationError) as error:
            return LogExtractedJob(
                source=self.source,
                is_test=self.is_test,
                url=receipt.url,
                raw_hash=receipt.raw_hash,
                parser=self.parser.name,
                parser_version=self.parser.version,
                attempted_at=parsed_at,
                error=f"{type(error).__name__}: {str(error).splitlines()[0]}",
            )
