"""
extract_job_details.py

Description : use case: give the raw detail pages of the jobs of a site, ready to
              be structured.
Rules       : the only entry point of the ingestion; callers know only execute().
              Two internal steps, in this order:
                1. for each category of the site (scrapers.toml): record the jobs
                   of its result pages (job_info);
                2. download the detail pages still to extract (job_detail).
              A category that fails is logged (job_info_extraction_log) and does not
              stop the others nor step 2: the jobs already recorded are still
              downloaded.
              The report says what happened; it is failed if any category failed.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial

from contracts import JobInfoExtractionLog, RunStatus
from ingestion.scrapers.i_scraper import IScraper
from ingestion.storage.i_storage import IStorage
from ingestion.use_cases._steps.extract_job_details_step import (
    DetailsSummary,
    ExtractJobDetailsStep,
)
from ingestion.use_cases._steps.extract_job_infos_step import (
    ExtractJobInfosStep,
)
from interfaces import IUseCase


@dataclass(frozen=True)
class ExtractJobDetailsReport:
    """What a run did, printed as the JSON summary of the command."""

    source: str
    status: RunStatus  # failed if any category failed
    categories: list[JobInfoExtractionLog]  # one log per category
    details: DetailsSummary


class ExtractJobDetails(IUseCase):
    """Gives the raw detail pages of the jobs of a site."""

    def __init__(
        self,
        scraper: IScraper,
        storage: IStorage,
        max_failures: int = 3,
        batch_size: int = 50,
        limit: int | None = None,
        now: Callable[[], datetime] = partial(datetime.now, UTC),
    ) -> None:
        self.scraper: IScraper = scraper
        self.storage: IStorage = storage
        self.max_failures: int = max_failures
        self.batch_size: int = batch_size
        self.limit: int | None = limit
        self.now: Callable[[], datetime] = now

    def execute(self) -> ExtractJobDetailsReport:
        """Record the jobs of every category, then download their detail pages."""
        logs: list[JobInfoExtractionLog] = self._extract_job_infos()
        details: DetailsSummary = self._extract_job_details()
        return ExtractJobDetailsReport(
            source=self.scraper.name,
            status=self._status(logs),
            categories=logs,
            details=details,
        )

    def _extract_job_infos(self) -> list[JobInfoExtractionLog]:
        """Step 1, for each category of the site."""
        step: ExtractJobInfosStep = ExtractJobInfosStep(
            self.scraper, self.storage, self.now
        )
        return [step.run(category) for category in self.scraper.categories]

    def _extract_job_details(self) -> DetailsSummary:
        """Step 2: download the detail pages still to extract."""
        step: ExtractJobDetailsStep = ExtractJobDetailsStep(
            self.scraper,
            self.storage,
            self.max_failures,
            self.batch_size,
            self.limit,
            self.now,
        )
        return step.run()

    def _status(self, logs: list[JobInfoExtractionLog]) -> RunStatus:
        """Failed if any category failed, completed otherwise."""
        if any(log.status == RunStatus.FAILED for log in logs):
            return RunStatus.FAILED
        return RunStatus.COMPLETED
