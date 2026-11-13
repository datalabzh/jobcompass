"""
fetch.py

Description : fetch step: fetches the pending offers of a source and stores their
              content.
Rules       : pending = discovered URLs - URLs already fetched with success
              - URLs set aside (max_failures failed attempts or more).
              Computed from the data at each run: no status table.
              Each URL is processed independently, a failure never stops the others.
              Success = HTTP 2xx: content stored under its raw_hash (if not already
              there), then a RawOffer appended to the manifest (content first, so a
              manifest line always has its content).
              Failure = no answer or non-2xx status: a FetchAttempt is logged.
              Storage errors are not URL failures: they stop the run.
              Processed in batches of batch_size URLs, results written after each
              batch; at most max_concurrency requests at once.
              Idempotent: running it again only processes what is still pending.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from jobcompass_contracts import RawOffer, compute_raw_hash
from jobcompass_ingestion.storage import FetchAttempt, OfferKey, Store

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchedPage:
    """Answer received for one URL: body unchanged, any HTTP status."""

    content: bytes
    http_status: int
    content_type: str


class PageFetchError(Exception):
    """No HTTP answer was received for the URL (network error, timeout)."""


FetchPage = Callable[[str], Awaitable[FetchedPage]]


@dataclass(frozen=True)
class PendingOffers:
    to_fetch: list[OfferKey]
    set_aside: list[OfferKey]


@dataclass(frozen=True)
class FetchSummary:
    fetched: int
    failed: int
    set_aside: int  # URLs skipped because of too many failures


def compute_pending_offers(
    discovered: Iterable[OfferKey],
    fetched: Iterable[OfferKey],
    failure_counts: Mapping[OfferKey, int],
    max_failures: int,
) -> PendingOffers:
    """Pure rule. Repeated observations are kept once, in order of first discovery."""
    already_fetched = set(fetched)
    to_fetch: list[OfferKey] = []
    set_aside: list[OfferKey] = []
    for key in dict.fromkeys(discovered):
        if key in already_fetched:
            continue
        if failure_counts.get(key, 0) >= max_failures:
            set_aside.append(key)
        else:
            to_fetch.append(key)
    return PendingOffers(to_fetch=to_fetch, set_aside=set_aside)


async def fetch_offers(
    source: str,
    fetch_page: FetchPage,
    store: Store,
    scraper_version: str,
    max_failures: int = 3,
    max_concurrency: int = 4,
    batch_size: int = 50,
    limit: int | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FetchSummary:
    pending = compute_pending_offers(
        discovered=store.discovered_keys(source),
        fetched=store.fetched_keys(source),
        failure_counts=store.failure_counts(source),
        max_failures=max_failures,
    )
    to_fetch = pending.to_fetch[:limit]
    semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_one(key: OfferKey) -> RawOffer | FetchAttempt:
        source, url = key
        async with semaphore:
            attempted_at = now()
            try:
                page = await fetch_page(url)
            except PageFetchError as error:
                return FetchAttempt(source, url, attempted_at, f"no answer: {error}")

        if not 200 <= page.http_status < 300:
            return FetchAttempt(source, url, attempted_at, f"HTTP {page.http_status}")

        raw_hash = compute_raw_hash(page.content)
        if not store.has_content(raw_hash):
            store.put_content(raw_hash, page.content)
        return RawOffer(
            source=source,
            url=url,
            raw_hash=raw_hash,
            content_type=page.content_type,
            fetched_at=attempted_at,
            http_status=page.http_status,
            scraper_version=scraper_version,
        )

    fetched = failed = 0
    for start in range(0, len(to_fetch), batch_size):
        batch = to_fetch[start : start + batch_size]
        results = await asyncio.gather(*(fetch_one(key) for key in batch))
        raw_offers = [r for r in results if isinstance(r, RawOffer)]
        attempts = [r for r in results if isinstance(r, FetchAttempt)]
        store.append_raw_offers(raw_offers)
        store.append_fetch_attempts(attempts)
        fetched += len(raw_offers)
        failed += len(attempts)

    summary = FetchSummary(
        fetched=fetched, failed=failed, set_aside=len(pending.set_aside)
    )
    logger.info(
        "fetch %s: %d fetched, %d failed, %d set aside",
        source,
        summary.fetched,
        summary.failed,
        summary.set_aside,
    )
    return summary
