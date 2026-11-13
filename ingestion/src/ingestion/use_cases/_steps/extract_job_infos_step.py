"""
extract_job_infos_step.py

Description : internal step: read every result page of one category and record
              each job seen (URL and card) in job_info.
Rules       : page 1 gives the number of pages; each page is written as soon as
              it is read, so a crash keeps the pages already read.
              Full snapshot at each run: nothing is compared with what is known.
              A JobInfoExtractionLog ends the run: 'completed', or 'failed' with the
              error. The error is not raised again: the caller reads the log.
              Internal to ExtractJobDetails, not a use case.
"""

import uuid
from collections.abc import Callable
from datetime import datetime

from contracts import JobInfo, JobInfoExtractionLog, RunStatus
from ingestion.scrapers.i_scraper import IScraper, ListingPage
from ingestion.storage.i_storage import IStorage, Table


class ExtractJobInfosStep:
    """Records the jobs of one category's result pages."""

    def __init__(
        self, scraper: IScraper, storage: IStorage, now: Callable[[], datetime]
    ) -> None:
        self.scraper: IScraper = scraper
        self.storage: IStorage = storage
        self.now: Callable[[], datetime] = now

    def run(self, category: str) -> JobInfoExtractionLog:
        """Read every result page of the category; return the run log."""
        run_id: str = str(uuid.uuid4())
        started_at: datetime = self.now()
        pages: list[ListingPage] = []
        error: Exception | None = None
        try:
            self._read_all_pages(run_id, category, pages)
        except Exception as caught:
            error = caught
        log: JobInfoExtractionLog = self._build_log(
            run_id, category, started_at, pages, error
        )
        self.storage.append(Table.JOB_INFO_EXTRACTION_LOG, [log])
        return log

    def _read_all_pages(
        self, run_id: str, category: str, pages: list[ListingPage]
    ) -> None:
        """Read pages 1..N, writing each one and adding it to `pages` once read."""
        page_number: int = 1
        num_pages: int = 1  # known once page 1 is read
        while page_number <= num_pages:
            listing: ListingPage = self.scraper.extract_jobs_from_listing(
                category, page_number
            )
            self.storage.append(
                Table.JOB_INFO, self._build_job_infos(run_id, category, listing)
            )
            pages.append(listing)
            num_pages = pages[0].num_pages
            page_number += 1

    def _build_job_infos(
        self, run_id: str, category: str, listing: ListingPage
    ) -> list[JobInfo]:
        """The jobs of one result page, as JobInfo records."""
        seen_at: datetime = self.now()
        return [
            JobInfo(
                run_id=run_id,
                source=self.scraper.name,
                url=url,
                seen_at=seen_at,
                listing_params={"category": category},
                card=card,
            )
            for url, card in listing.jobs
        ]

    def _build_log(
        self,
        run_id: str,
        category: str,
        started_at: datetime,
        pages: list[ListingPage],
        error: Exception | None,
    ) -> JobInfoExtractionLog:
        """The log of the run, from the pages read: completed, or failed with error."""
        urls: list[str] = [url for listing in pages for url, _ in listing.jobs]
        return JobInfoExtractionLog(
            run_id=run_id,
            source=self.scraper.name,
            listing_params={"category": category},
            started_at=started_at,
            finished_at=self.now(),
            status=RunStatus.COMPLETED if error is None else RunStatus.FAILED,
            error=None if error is None else f"{type(error).__name__}: {error}",
            announced_total=pages[0].announced_total if pages else None,
            pages_read=len(pages),
            jobs_seen=len(urls),
            distinct_urls=len(set(urls)),
        )
