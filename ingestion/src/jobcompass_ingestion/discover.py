"""
discover.py

Description : discovery step: reads every result page of a portal category and
              loads the offers found, as they are (extract + load, no logic).
Rules       : full snapshot at each run: every page is read, nothing is compared
              with what is already known (new / updated / gone is decided in SQL).
              Page 1 gives the number of pages; pages 2..N are then read, at most
              max_concurrency at once (politeness is the HTTP client's job).
              Each page is written as soon as it is read.
              The DiscoverySnapshot record is written last, only if every page was
              read without error: no record = incomplete run.
              read_page = the portal function (see portals/).
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from jobcompass_contracts import DiscoveredOffer, DiscoveryMethod, DiscoverySnapshot
from jobcompass_ingestion.storage import Store


@dataclass(frozen=True)
class ListingPage:
    """One result page, as read by a portal function."""

    announced_total: int | None  # offers announced by the portal
    num_pages: int
    offers: list[tuple[str, str]]  # (offer url, raw JSON of the offer)


ReadListingPage = Callable[[int], Awaitable[ListingPage]]


async def discover_offers(
    source: str,
    params: dict[str, str],
    read_page: ReadListingPage,
    store: Store,
    max_concurrency: int = 2,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> DiscoverySnapshot:
    snapshot_id = str(uuid.uuid4())
    started_at = now()
    seen_urls: list[str] = []

    def load(page: ListingPage) -> None:
        discovered_at = now()
        store.append_discovered(
            [
                DiscoveredOffer(
                    snapshot_id=snapshot_id,
                    source=source,
                    url=url,
                    discovered_at=discovered_at,
                    discovery_method=DiscoveryMethod.LISTING,
                    discovery_params=params,
                    listing_payload=payload,
                )
                for url, payload in page.offers
            ]
        )
        seen_urls.extend(url for url, _ in page.offers)

    first = await read_page(1)
    load(first)

    semaphore = asyncio.Semaphore(max_concurrency)

    async def read_and_load(number: int) -> None:
        async with semaphore:
            load(await read_page(number))

    await asyncio.gather(*(read_and_load(n) for n in range(2, first.num_pages + 1)))

    snapshot = DiscoverySnapshot(
        snapshot_id=snapshot_id,
        source=source,
        discovery_method=DiscoveryMethod.LISTING,
        discovery_params=params,
        started_at=started_at,
        finished_at=now(),
        announced_total=first.announced_total,
        pages_read=first.num_pages,
        offers_seen=len(seen_urls),
        distinct_urls=len(set(seen_urls)),
    )
    store.append_discovery_snapshot(snapshot)
    return snapshot
