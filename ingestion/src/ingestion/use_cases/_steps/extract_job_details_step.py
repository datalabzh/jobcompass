"""
extract_job_details_step.py

Description : internal step: download the detail page of every job still to
              extract and store it unchanged.
Rules       : jobs to extract = jobs seen (job_info) - jobs already downloaded
              (job_detail) - jobs set aside (max_failures failures or more in
              job_detail_extraction_log); each URL once, first sighting first.
              Each job is processed on its own: a failure never stops the others.
              Success: page stored under its raw_hash (if not already there), then
              a JobDetail (page first, so a JobDetail always has its page).
              Failure: a JobDetailExtractionLog with the reason.
              Results written after each batch of batch_size jobs: a crash loses at
              most the current batch, done again at the next run.
              Internal to ExtractJobDetails, not a use case.
"""

import itertools
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from contracts import JobDetail, JobDetailExtractionLog, compute_raw_hash
from ingestion.scrapers.i_scraper import (
    DetailPage,
    IScraper,
    JobDetailError,
)
from ingestion.storage.i_storage import IStorage, Table


@dataclass(frozen=True)
class DetailsSummary:
    """Outcome of the step: pages downloaded, failures, jobs set aside."""

    extracted: int
    failed: int
    set_aside: int


class ExtractJobDetailsStep:
    """Downloads the detail pages of the jobs still to extract."""

    def __init__(
        self,
        scraper: IScraper,
        storage: IStorage,
        max_failures: int,
        batch_size: int,
        limit: int | None,
        now: Callable[[], datetime],
    ) -> None:
        self.scraper: IScraper = scraper
        self.storage: IStorage = storage
        self.max_failures: int = max_failures
        self.batch_size: int = batch_size
        self.limit: int | None = limit
        self.now: Callable[[], datetime] = now

    def run(self) -> DetailsSummary:
        """Download the pending pages batch by batch, writing after each batch."""
        to_extract, set_aside = self._pending_urls()
        extracted: int = 0
        failed: int = 0
        for batch in itertools.batched(to_extract[: self.limit], self.batch_size):
            details, failures = self._download_batch(list(batch))
            self.storage.append(Table.JOB_DETAIL, details)
            self.storage.append(Table.JOB_DETAIL_EXTRACTION_LOG, failures)
            extracted += len(details)
            failed += len(failures)
        return DetailsSummary(extracted=extracted, failed=failed, set_aside=set_aside)

    def _pending_urls(self) -> tuple[list[str], int]:
        """URLs still to extract, in order of first sighting; number set aside."""
        source: str = self.scraper.name
        seen: list[dict[str, object]] = sorted(
            self.storage.read(Table.JOB_INFO, source), key=lambda r: r["seen_at"]
        )
        extracted: set[object] = {
            r["url"] for r in self.storage.read(Table.JOB_DETAIL, source)
        }
        failures: Counter[object] = Counter(
            r["url"] for r in self.storage.read(Table.JOB_DETAIL_EXTRACTION_LOG, source)
        )
        to_extract: list[str] = []
        set_aside: int = 0
        for url in dict.fromkeys(str(r["url"]) for r in seen):
            if url in extracted:
                continue
            if failures[url] >= self.max_failures:
                set_aside += 1
            else:
                to_extract.append(url)
        return to_extract, set_aside

    def _download_batch(
        self, urls: list[str]
    ) -> tuple[list[JobDetail], list[JobDetailExtractionLog]]:
        """Download a batch of pages; return the successes and the failures."""
        details: list[JobDetail] = []
        failures: list[JobDetailExtractionLog] = []
        for url in urls:
            attempted_at: datetime = self.now()
            try:
                details.append(self._download_one(url, attempted_at))
            except JobDetailError as error:
                failures.append(
                    JobDetailExtractionLog(
                        source=self.scraper.name,
                        url=url,
                        attempted_at=attempted_at,
                        error=str(error),
                    )
                )
        return details, failures

    def _download_one(self, url: str, fetched_at: datetime) -> JobDetail:
        """Download one page, store it under its hash, describe it as a JobDetail."""
        page: DetailPage = self.scraper.extract_job_detail(url)
        raw_hash: str = compute_raw_hash(page.content)
        file_name: str = f"job_detail_html/{raw_hash}.html"
        if not self.storage.has_file(file_name):
            self.storage.put_file(file_name, page.content)
        return JobDetail(
            source=self.scraper.name,
            url=url,
            raw_hash=raw_hash,
            content_type=page.content_type,
            fetched_at=fetched_at,
            http_status=page.http_status,
            scraper_version=self.scraper.version,
        )
