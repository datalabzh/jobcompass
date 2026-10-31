"""
fake_connectors.py

Description : fake discoverer, page fetcher and content storage, for tests.
Rules       : answers are set up in advance by the test; no network, no disk.
              FakePageFetcher: URL absent from the pages = no answer
              (PageFetchError); it records every URL it was asked for.
"""

from jobcompass_contracts import DiscoveryMethod
from jobcompass_ingestion.application.dto.fetched_page_dto import FetchedPage
from jobcompass_ingestion.application.dto.found_offer_url_dto import FoundOfferUrl
from jobcompass_ingestion.application.interfaces.i_offer_discoverer import (
    IOfferDiscoverer,
)
from jobcompass_ingestion.application.interfaces.i_page_fetcher import (
    IPageFetcher,
    PageFetchError,
)
from jobcompass_ingestion.application.interfaces.i_raw_content_storage import (
    IRawContentStorage,
)


class FakeOfferDiscoverer(IOfferDiscoverer):
    def __init__(self, found: list[FoundOfferUrl]) -> None:
        self.found = found

    async def discover(
        self, method: DiscoveryMethod, params: dict[str, str]
    ) -> list[FoundOfferUrl]:
        return list(self.found)


class FakePageFetcher(IPageFetcher):
    def __init__(self, pages: dict[str, FetchedPage]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    async def fetch(self, url: str) -> FetchedPage:
        self.requested.append(url)
        if url not in self.pages:
            raise PageFetchError("connection refused")
        return self.pages[url]


class InMemoryRawContentStorage(IRawContentStorage):
    def __init__(self) -> None:
        self.contents: dict[str, bytes] = {}
        self.put_count = 0

    async def exists(self, raw_hash: str) -> bool:
        return raw_hash in self.contents

    async def put(self, raw_hash: str, content: bytes) -> None:
        self.put_count += 1
        self.contents[raw_hash] = content
