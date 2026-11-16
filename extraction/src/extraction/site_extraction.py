"""
site_extraction.py

Description : cas d'utilisation unique de la brique : extraire un site, job infos
              puis job details, en vérifiant et en stockant tout ce que renvoient
              les classes du site.
Règles      : les classes du site ne stockent rien ; ici, chaque page de job infos
              et chaque lot de job details est vérifié (contract_checks) puis écrit
              aussitôt : une seule page ou un seul lot en mémoire à la fois.
              1. Pour chaque catégorie : les pages de résultats, au plus max_pages
                 (None = toutes) ; un JobInfoExtractionLog termine la catégorie.
                 Une catégorie en échec n'arrête ni les autres ni l'étape 2.
              2. Jobs à télécharger = jobs vus - déjà téléchargés - mis de côté
                 (max_failures échecs), au plus max_jobs (None = tous), par lots de
                 batch_size. Pour chaque succès : le HTML d'abord (sous son hash),
                 puis le reçu JobDetail ; chaque échec : un JobDetailExtractionLog.
              Une violation de contrat arrête tout (bug du code du site).
              Le stockage reçu est déjà celui du bon mode (test ou réel).
"""

import itertools
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from contracts import JobDetail, JobInfoExtractionLog, RunStatus
from extraction.contract_checks import (
    ContractViolationError,
    check_job_details_batch,
    check_job_info_page,
)
from extraction.interfaces.i_job_details_extractor import (
    FetchedJobDetail,
    IJobDetailsExtractor,
)
from extraction.interfaces.i_job_infos_extractor import (
    IJobInfosExtractor,
    JobInfoPage,
)
from extraction.interfaces.i_storage import IStorage, Table
from interfaces import IUseCase


@dataclass(frozen=True)
class DetailsSummary:
    """Outcome of step 2: pages downloaded, failures, jobs set aside."""

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
    status: RunStatus  # failed if any category failed
    categories: list[JobInfoExtractionLog]  # one log per category
    details: DetailsSummary


@dataclass
class _CategoryProgress:
    """Counters of a category run, updated page after page."""

    pages_read: int = 0
    announced_total: int | None = None
    urls: list[str] = field(default_factory=list)


class SiteExtraction(IUseCase):
    """Extracts one site: job infos, then job details; checks and stores all."""

    def __init__(
        self,
        source: str,
        job_infos: IJobInfosExtractor,
        job_details: IJobDetailsExtractor,
        storage: IStorage,
        categories: list[str],
        max_pages: int | None,
        max_jobs: int | None,
        max_failures: int,
        batch_size: int,
        now: Callable[[], datetime],
    ) -> None:
        self.source: str = source
        self.job_infos: IJobInfosExtractor = job_infos
        self.job_details: IJobDetailsExtractor = job_details
        self.storage: IStorage = storage
        self.categories: list[str] = categories
        self.max_pages: int | None = max_pages
        self.max_jobs: int | None = max_jobs
        self.max_failures: int = max_failures
        self.batch_size: int = batch_size
        self.now: Callable[[], datetime] = now

    def execute(self) -> ExtractionReport:
        """Record the jobs of every category, then download their detail pages."""
        logs: list[JobInfoExtractionLog] = [
            self._extract_category(category) for category in self.categories
        ]
        details: DetailsSummary = self._extract_details()
        failed: bool = any(log.status == RunStatus.FAILED for log in logs)
        return ExtractionReport(
            source=self.source,
            is_test=self.storage.is_test,
            max_pages=self.max_pages,
            max_jobs=self.max_jobs,
            status=RunStatus.FAILED if failed else RunStatus.COMPLETED,
            categories=logs,
            details=details,
        )

    # --- step 1: job infos ------------------------------------------------------

    def _extract_category(self, category: str) -> JobInfoExtractionLog:
        """Read and store the result pages of a category; store and return its log."""
        run_id: str = str(uuid.uuid4())
        started_at: datetime = self.now()
        progress: _CategoryProgress = _CategoryProgress()
        error: Exception | None = None
        try:
            self._store_pages(category, run_id, progress)
        except ContractViolationError:
            raise
        except Exception as caught:
            error = caught
        log: JobInfoExtractionLog = self._category_log(
            category, run_id, started_at, progress, error
        )
        self.storage.append(Table.JOB_INFO_EXTRACTION_LOG, [log])
        return log

    def _store_pages(
        self, category: str, run_id: str, progress: _CategoryProgress
    ) -> None:
        """Check and write each page as it comes, up to max_pages."""
        for page in self.job_infos.execute(category, run_id):
            checked: JobInfoPage = check_job_info_page(
                page, self.source, self.storage.is_test
            )
            self.storage.append(Table.JOB_INFO, checked.job_infos)
            self._count_page(checked, progress)
            if self.max_pages is not None and progress.pages_read >= self.max_pages:
                break

    def _count_page(self, page: JobInfoPage, progress: _CategoryProgress) -> None:
        """Add one stored page to the counters of the category."""
        if progress.pages_read == 0:
            progress.announced_total = page.announced_total
        progress.pages_read += 1
        progress.urls.extend(job_info.url for job_info in page.job_infos)

    def _category_log(
        self,
        category: str,
        run_id: str,
        started_at: datetime,
        progress: _CategoryProgress,
        error: Exception | None,
    ) -> JobInfoExtractionLog:
        """The log of a category run: completed, or failed with its error."""
        urls: list[str] = progress.urls
        return JobInfoExtractionLog(
            run_id=run_id,
            source=self.source,
            is_test=self.storage.is_test,
            listing_params={"category": category},
            started_at=started_at,
            finished_at=self.now(),
            status=RunStatus.COMPLETED if error is None else RunStatus.FAILED,
            error=None if error is None else f"{type(error).__name__}: {error}",
            announced_total=progress.announced_total,
            pages_read=progress.pages_read,
            jobs_seen=len(urls),
            distinct_urls=len(set(urls)),
        )

    # --- step 2: job details ----------------------------------------------------

    def _extract_details(self) -> DetailsSummary:
        """Download the pending pages batch by batch, storing after each batch."""
        to_extract, set_aside = self._pending_urls()
        extracted: int = 0
        failed: int = 0
        for batch in itertools.batched(to_extract[: self.max_jobs], self.batch_size):
            urls: list[str] = list(batch)
            fetched, failures = check_job_details_batch(
                self.job_details.execute(urls),
                urls,
                self.source,
                self.storage.is_test,
            )
            self._store_fetched(fetched)
            self.storage.append(Table.JOB_DETAIL_EXTRACTION_LOG, failures)
            extracted += len(fetched)
            failed += len(failures)
        return DetailsSummary(extracted=extracted, failed=failed, set_aside=set_aside)

    def _pending_urls(self) -> tuple[list[str], int]:
        """URLs still to download, in order of first sighting; number set aside."""
        seen: list[dict[str, object]] = sorted(
            self.storage.read(Table.JOB_INFO, self.source), key=lambda r: r["seen_at"]
        )
        downloaded: set[object] = {
            r["url"] for r in self.storage.read(Table.JOB_DETAIL, self.source)
        }
        failures: Counter[object] = Counter(
            r["url"]
            for r in self.storage.read(Table.JOB_DETAIL_EXTRACTION_LOG, self.source)
        )
        to_extract: list[str] = []
        set_aside: int = 0
        for url in dict.fromkeys(str(r["url"]) for r in seen):
            if url in downloaded:
                continue
            if failures[url] >= self.max_failures:
                set_aside += 1
            else:
                to_extract.append(url)
        return to_extract, set_aside

    def _store_fetched(self, fetched: list[FetchedJobDetail]) -> None:
        """Each page under its hash (if new), then all the receipts."""
        for result in fetched:
            file_name: str = f"job_detail_html/{result.job_detail.raw_hash}.html"
            if not self.storage.has_file(file_name):
                self.storage.put_file(file_name, result.content)
        receipts: list[JobDetail] = [result.job_detail for result in fetched]
        self.storage.append(Table.JOB_DETAIL, receipts)
