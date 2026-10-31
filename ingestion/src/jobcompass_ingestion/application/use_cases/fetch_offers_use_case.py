"""
fetch_offers_use_case.py

Description : use case fetching the pending offers of a source and storing their
              content.
Rules       : pending offers computed by compute_pending_offers, URLs set aside
              are skipped.
              Each URL is processed independently, a failure never stops the others.
              Success = HTTP 2xx: content stored under its raw_hash (if not already
              there), then a RawOffer appended to the manifest (content first, so a
              manifest line always has its content).
              Failure = no answer or non-2xx status: attempt recorded in the fetch
              attempt log.
              Storage or repository errors are not URL failures: they stop the run.
              Processed in batches of FETCH_BATCH_SIZE URLs, results written after
              each batch; at most FETCH_MAX_CONCURRENCY requests at once.
              Idempotent: running it again only processes what is still pending.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from jobcompass_contracts import RawOffer, compute_raw_hash
from jobcompass_ingestion.application.dto.fetch_offers_dto import (
    FetchOffersInput,
    FetchOffersOutput,
)
from jobcompass_ingestion.application.interfaces.i_discovered_offer_repository import (
    IDiscoveredOfferRepository,
)
from jobcompass_ingestion.application.interfaces.i_fetch_attempt_repository import (
    IFetchAttemptRepository,
)
from jobcompass_ingestion.application.interfaces.i_page_fetcher import (
    IPageFetcher,
    PageFetchError,
)
from jobcompass_ingestion.application.interfaces.i_raw_content_storage import (
    IRawContentStorage,
)
from jobcompass_ingestion.application.interfaces.i_raw_offer_repository import (
    IRawOfferRepository,
)
from jobcompass_ingestion.domain.fetch_attempt import FetchAttempt
from jobcompass_ingestion.domain.pending_offers import (
    OfferKey,
    compute_pending_offers,
)

logger = logging.getLogger(__name__)


class FetchOffersUseCase:
    def __init__(
        self,
        page_fetcher: IPageFetcher,
        raw_content_storage: IRawContentStorage,
        discovered_offer_repository: IDiscoveredOfferRepository,
        raw_offer_repository: IRawOfferRepository,
        fetch_attempt_repository: IFetchAttemptRepository,
        scraper_version: str,
        max_failures: int = 3,
        max_concurrency: int = 4,
        batch_size: int = 50,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._page_fetcher = page_fetcher
        self._storage = raw_content_storage
        self._discovered = discovered_offer_repository
        self._raw_offers = raw_offer_repository
        self._attempts = fetch_attempt_repository
        self._scraper_version = scraper_version
        self._max_failures = max_failures
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._batch_size = batch_size
        self._now = now

    async def execute(self, request: FetchOffersInput) -> FetchOffersOutput:
        pending = compute_pending_offers(
            discovered=await self._discovered.list_offer_keys(request.source),
            fetched=await self._raw_offers.list_fetched_keys(request.source),
            failure_counts=await self._attempts.count_failures(request.source),
            max_failures=self._max_failures,
        )
        to_fetch = pending.to_fetch[: request.limit]

        fetched = failed = 0
        for start in range(0, len(to_fetch), self._batch_size):
            batch = to_fetch[start : start + self._batch_size]
            results = await asyncio.gather(*(self._fetch_one(k) for k in batch))
            raw_offers = [r for r in results if isinstance(r, RawOffer)]
            attempts = [r for r in results if isinstance(r, FetchAttempt)]
            if raw_offers:
                await self._raw_offers.append(raw_offers)
            if attempts:
                await self._attempts.append(attempts)
            fetched += len(raw_offers)
            failed += len(attempts)

        output = FetchOffersOutput(
            fetched=fetched, failed=failed, set_aside=len(pending.set_aside)
        )
        logger.info(
            "fetch %s: %d fetched, %d failed, %d set aside",
            request.source,
            output.fetched,
            output.failed,
            output.set_aside,
        )
        return output

    async def _fetch_one(self, key: OfferKey) -> RawOffer | FetchAttempt:
        source, url = key
        async with self._semaphore:
            attempted_at = self._now()
            try:
                page = await self._page_fetcher.fetch(url)
            except PageFetchError as error:
                return FetchAttempt(source, url, attempted_at, f"no answer: {error}")

        if not 200 <= page.http_status < 300:
            return FetchAttempt(source, url, attempted_at, f"HTTP {page.http_status}")

        raw_hash = compute_raw_hash(page.content)
        if not await self._storage.exists(raw_hash):
            await self._storage.put(raw_hash, page.content)
        return RawOffer(
            source=source,
            url=url,
            raw_hash=raw_hash,
            content_type=page.content_type,
            fetched_at=attempted_at,
            http_status=page.http_status,
            scraper_version=self._scraper_version,
        )
