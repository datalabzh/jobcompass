"""
i_job_details_extractor.py

Description : ce que doit fournir tout site pour ses pages de détail : la page brute
              de chaque job d'un lot d'URL.
Règles      : execute(urls) renvoie un résultat par URL : un FetchedJobDetail (le
              reçu JobDetail + le HTML) en cas de succès, un JobDetailExtractionLog
              (la raison) en cas d'échec. Un échec n'arrête jamais le lot.
              Le site ne stocke rien : le point d'entrée vérifie le lot, écrit le
              HTML puis les reçus.
              _download_detail fait le cas courant (toute réponse 2xx est gardée
              telle quelle) : un site n'écrit sa propre version que s'il en a besoin.
              version = version du code du site, enregistrée avec chaque page.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from contracts import JobDetail, JobDetailExtractionLog, compute_raw_hash
from extraction.http import GetPage, Page, PageFetchError


@dataclass(frozen=True)
class FetchedJobDetail:
    """A downloaded detail page: its receipt (JobDetail) and its raw content."""

    job_detail: JobDetail
    content: bytes


JobDetailResult = FetchedJobDetail | JobDetailExtractionLog


class IJobDetailsExtractor(ABC):
    """Site-specific download of job detail pages."""

    version: str  # version of the site code, recorded with each page

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
    def execute(self, urls: list[str]) -> list[JobDetailResult]:
        """One result per URL: the fetched page, or the reason of the failure."""

    def _download_detail(self, url: str) -> JobDetailResult:
        """Download one page; any 2xx answer is kept, anything else is a failure."""
        attempted_at: datetime = self.now()
        try:
            answer: Page = self.get_page(url)
        except PageFetchError as error:
            return self._failure(url, attempted_at, f"no answer: {error}")
        if not 200 <= answer.http_status < 300:
            return self._failure(url, attempted_at, f"HTTP {answer.http_status}")
        return self._fetched(url, attempted_at, answer)

    def _fetched(
        self, url: str, fetched_at: datetime, answer: Page
    ) -> FetchedJobDetail:
        """The receipt and content of a downloaded page."""
        receipt: JobDetail = JobDetail(
            source=self.source,
            is_test=self.is_test,
            url=url,
            raw_hash=compute_raw_hash(answer.content),
            content_type=answer.content_type,
            fetched_at=fetched_at,
            http_status=answer.http_status,
            scraper_version=self.version,
        )
        return FetchedJobDetail(job_detail=receipt, content=answer.content)

    def _failure(
        self, url: str, attempted_at: datetime, error: str
    ) -> JobDetailExtractionLog:
        """The log of a failed download."""
        return JobDetailExtractionLog(
            source=self.source,
            is_test=self.is_test,
            url=url,
            attempted_at=attempted_at,
            error=error,
        )
