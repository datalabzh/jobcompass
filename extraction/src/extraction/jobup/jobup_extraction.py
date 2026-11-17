"""
jobup_extraction.py

Description : extraction complète de jobup.ch : les jobs de chaque catégorie, puis
              la page de détail brute de chaque job encore à télécharger.
Règles      : options (site.toml, [extraction.options]) : categories, liste de slugs.
              1. Pour chaque catégorie : les pages de résultats, de la page 1 à la
                 dernière, au plus max_pages ; chaque page est écrite dès qu'elle est
                 lue (une ligne RawJobInfo par job, avec sa carte JSON brute). Un
                 RawJobInfoExtractionLog termine la catégorie : completed, ou failed
                 avec l'erreur. Une catégorie en échec n'arrête ni les autres ni
                 l'étape 2.
              2. Jobs à télécharger = jobs vus - déjà téléchargés - mis de côté
                 (max_failures échecs), au plus max_jobs, par lots de batch_size.
                 Succès (réponse 2xx) : le HTML d'abord, sous son raw_hash, puis le
                 reçu RawJobDetail ; échec : un RawJobDetailExtractionLog avec la
                 raison. Un plantage perd au plus le lot en cours.
              version = version de ce code, enregistrée avec chaque page ; changer
              la façon de télécharger = monter version.
"""

import itertools
import json
import uuid
from collections import Counter
from collections.abc import Iterator
from datetime import datetime
from functools import cached_property
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from catalog import Table
from contracts import (
    RawJobDetail,
    RawJobDetailExtractionLog,
    RawJobInfo,
    RawJobInfoExtractionLog,
    RunStatus,
    compute_raw_hash,
)
from extraction.jobup.jobup_scraper import JobupListing, JobupScraper
from interfaces import (
    DetailsSummary,
    ExtractionReport,
    ISiteExtraction,
    Page,
    PageFetchError,
)


class JobupOptions(BaseModel):
    """The [extraction.options] table of jobup's site.toml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    categories: list[str] = Field(min_length=1, description="Category URL slugs")


class JobupExtraction(ISiteExtraction):
    """Extracts jobup.ch: the jobs of each category, then their detail pages."""

    version: str = "0.1.0"

    def execute(self) -> ExtractionReport:
        """Record the jobs of every category, then download their detail pages."""
        options: JobupOptions = JobupOptions(
            **self.options
        )  # checked before any request
        logs: list[RawJobInfoExtractionLog] = [
            self._extract_category(category) for category in options.categories
        ]
        details: DetailsSummary = self._extract_details()
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

    # --- 1. raw job infos, category by category ---------------------------------

    def _extract_category(self, category: str) -> RawJobInfoExtractionLog:
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
        log: RawJobInfoExtractionLog = RawJobInfoExtractionLog(
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
        self.storage.append(Table.RAW_JOB_INFO_EXTRACTION_LOG, [log])
        return log

    @cached_property
    def _scraper(self) -> JobupScraper:
        """The reader of jobup's result pages."""
        return JobupScraper(self.get_page)

    def _listings(self, category: str) -> Iterator[JobupListing]:
        """The result pages of a category, one by one, up to max_pages."""
        first: JobupListing = self._scraper.read_listing(category, 1)
        yield first
        last: int = first.num_pages
        if self.max_pages is not None:
            last = min(last, self.max_pages)
        for page in range(2, last + 1):
            yield self._scraper.read_listing(category, page)

    def _store_listing(
        self, listing: JobupListing, category: str, run_id: str, urls: list[str]
    ) -> None:
        """Write one RawJobInfo per job of the page, and note their URLs."""
        infos: list[RawJobInfo] = [
            RawJobInfo(
                run_id=run_id,
                source=self.source,
                is_test=self.is_test,
                url=self._scraper.job_url(job),
                seen_at=self.now(),
                listing_params={"category": category},
                card=json.dumps(job, ensure_ascii=False),
            )
            for job in listing.jobs
        ]
        self.storage.append(Table.RAW_JOB_INFO, infos)
        urls.extend(info.url for info in infos)

    # --- 2. raw job details -----------------------------------------------------

    def _extract_details(self) -> DetailsSummary:
        """Download the pending pages batch by batch, storing after each batch."""
        to_extract, set_aside = self._pending_urls()
        extracted: int = 0
        failed: int = 0
        for batch in itertools.batched(to_extract[: self.max_jobs], self.batch_size):
            receipts: list[RawJobDetail] = []
            failures: list[RawJobDetailExtractionLog] = []
            for url in batch:
                result: RawJobDetail | RawJobDetailExtractionLog = self._download(url)
                if isinstance(result, RawJobDetail):
                    receipts.append(result)
                else:
                    failures.append(result)
            self.storage.append(Table.RAW_JOB_DETAIL, receipts)
            self.storage.append(Table.RAW_JOB_DETAIL_EXTRACTION_LOG, failures)
            extracted += len(receipts)
            failed += len(failures)
        return DetailsSummary(extracted=extracted, failed=failed, set_aside=set_aside)

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
            for row in self.storage.read(
                Table.RAW_JOB_DETAIL_EXTRACTION_LOG, self.source
            )
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

    def _download(self, url: str) -> RawJobDetail | RawJobDetailExtractionLog:
        """Download one page and store its HTML; the receipt, or the failure."""
        attempted_at: datetime = self.now()
        try:
            answer: Page = self.get_page(url)
        except PageFetchError as error:
            return self._failure(url, attempted_at, f"no answer: {error}")
        if not 200 <= answer.http_status < 300:
            return self._failure(url, attempted_at, f"HTTP {answer.http_status}")
        raw_hash: str = compute_raw_hash(answer.content)
        file_name: str = f"{Table.RAW_JOB_DETAIL_HTML}/{raw_hash}.html"
        if not self.storage.has_file(file_name):
            self.storage.put_file(file_name, answer.content)
        return RawJobDetail(
            source=self.source,
            is_test=self.is_test,
            url=url,
            raw_hash=raw_hash,
            content_type=answer.content_type,
            fetched_at=attempted_at,
            http_status=answer.http_status,
            scraper_version=self.version,
        )

    def _failure(
        self, url: str, attempted_at: datetime, error: str
    ) -> RawJobDetailExtractionLog:
        """The log of a failed download."""
        return RawJobDetailExtractionLog(
            source=self.source,
            is_test=self.is_test,
            url=url,
            attempted_at=attempted_at,
            error=error,
        )
