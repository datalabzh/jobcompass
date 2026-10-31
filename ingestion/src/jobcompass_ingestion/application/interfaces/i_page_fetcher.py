"""
i_page_fetcher.py

Description : interface of the HTTP client fetching one offer page.
Rules       : returns the page for any HTTP answer, whatever its status.
              Raises PageFetchError only when no answer was received
              (network error, timeout).
              Politeness (rate limit, user agent) is the implementation's
              responsibility.
"""

from abc import ABC, abstractmethod

from jobcompass_ingestion.application.dto.fetched_page_dto import FetchedPage


class PageFetchError(Exception):
    """No HTTP answer was received for the URL."""


class IPageFetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> FetchedPage: ...
