"""
test_fetch_offers_use_case.py

Description : tests of the fetch offers use case, with fakes.
Rules       : covers success, failures that do not stop the others, set aside URLs,
              idempotence, content deduplication, limit and batches.
"""

from datetime import UTC, datetime

from fakes.fake_connectors import FakePageFetcher, InMemoryRawContentStorage
from fakes.in_memory_repositories import (
    InMemoryDiscoveredOfferRepository,
    InMemoryFetchAttemptRepository,
    InMemoryRawOfferRepository,
)

from jobcompass_contracts import DiscoveredOffer, compute_raw_hash
from jobcompass_ingestion.application.dto.fetch_offers_dto import FetchOffersInput
from jobcompass_ingestion.application.dto.fetched_page_dto import FetchedPage
from jobcompass_ingestion.application.use_cases.fetch_offers_use_case import (
    FetchOffersUseCase,
)
from jobcompass_ingestion.domain.fetch_attempt import FetchAttempt

NOW = datetime(2026, 10, 31, 6, 0, tzinfo=UTC)
URL_A = "https://www.jobup.ch/a"
URL_B = "https://www.jobup.ch/b"
URL_C = "https://www.jobup.ch/c"
HTML = b"<html>offer</html>"


def discovered(*urls):
    return [
        DiscoveredOffer(
            source="jobup", url=url, discovered_at=NOW, discovery_method="listing"
        )
        for url in urls
    ]


class World:
    """All fakes of one test, and the use case wired on them."""

    def __init__(self, urls, pages, attempts=(), batch_size=50):
        self.fetcher = FakePageFetcher(pages)
        self.storage = InMemoryRawContentStorage()
        self.discovered = InMemoryDiscoveredOfferRepository(discovered(*urls))
        self.raw_offers = InMemoryRawOfferRepository()
        self.attempts = InMemoryFetchAttemptRepository(attempts)
        self.use_case = FetchOffersUseCase(
            page_fetcher=self.fetcher,
            raw_content_storage=self.storage,
            discovered_offer_repository=self.discovered,
            raw_offer_repository=self.raw_offers,
            fetch_attempt_repository=self.attempts,
            scraper_version="0.1.0",
            max_failures=3,
            batch_size=batch_size,
            now=lambda: NOW,
        )

    async def run(self, limit=None):
        return await self.use_case.execute(FetchOffersInput("jobup", limit))


def page(status=200, content=HTML):
    return FetchedPage(content=content, http_status=status, content_type="text/html")


async def test_success_stores_content_then_manifest():
    world = World([URL_A], {URL_A: page()})

    output = await world.run()

    assert output.fetched == 1
    raw = world.raw_offers.raw_offers[0]
    assert raw.raw_hash == compute_raw_hash(HTML)
    assert world.storage.contents[raw.raw_hash] == HTML
    assert raw.fetched_at == NOW


async def test_failures_logged_without_stopping_others():
    world = World([URL_A, URL_B, URL_C], {URL_A: page(), URL_B: page(status=404)})

    output = await world.run()

    assert (output.fetched, output.failed) == (1, 2)
    errors = {a.url: a.error for a in world.attempts.attempts}
    assert errors[URL_B] == "HTTP 404"
    assert errors[URL_C].startswith("no answer")


async def test_set_aside_url_not_requested():
    failures = [FetchAttempt("jobup", URL_A, NOW, "HTTP 500")] * 3
    world = World([URL_A, URL_B], {URL_A: page(), URL_B: page()}, failures)

    output = await world.run()

    assert output.set_aside == 1
    assert world.fetcher.requested == [URL_B]


async def test_second_run_fetches_nothing():
    world = World([URL_A], {URL_A: page()})

    await world.run()
    output = await world.run()

    assert output.fetched == 0
    assert world.fetcher.requested == [URL_A]


async def test_same_content_stored_once():
    world = World([URL_A, URL_B], {URL_A: page(), URL_B: page()})

    await world.run()

    assert len(world.raw_offers.raw_offers) == 2
    assert world.storage.put_count == 1


async def test_limit_and_batches():
    world = World(
        [URL_A, URL_B, URL_C],
        {u: page(content=u.encode()) for u in (URL_A, URL_B, URL_C)},
        batch_size=1,
    )

    output = await world.run(limit=2)

    assert output.fetched == 2
    assert world.fetcher.requested == [URL_A, URL_B]
