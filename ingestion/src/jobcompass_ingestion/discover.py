"""
discover.py

Description : discovery step: reads the result pages of a portal and records every
              offer URL found as a DiscoveredOffer.
Rules       : every URL seen is written, even if already known (one line per
              observation): nothing is read before writing.
              All URLs of a run share the same discovered_at (start of the run).
              Written once at the end of the run: a failed run writes nothing and
              is simply run again.
              find_offer_urls = the portal function (see portals/): returns
              (url, context) pairs, duplicates included, context e.g. {'page': '3'}.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from jobcompass_contracts import DiscoveredOffer, DiscoveryMethod
from jobcompass_ingestion.storage import Store

logger = logging.getLogger(__name__)

FoundUrl = tuple[str, dict[str, str]]  # (url, context of the finding)
FindOfferUrls = Callable[[DiscoveryMethod, dict[str, str]], Awaitable[list[FoundUrl]]]


@dataclass(frozen=True)
class DiscoverSummary:
    observed: int  # URLs written, one per observation
    distinct_urls: int


async def discover_offers(
    source: str,
    method: DiscoveryMethod,
    params: dict[str, str],
    find_offer_urls: FindOfferUrls,
    store: Store,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> DiscoverSummary:
    discovered_at = now()
    found = await find_offer_urls(method, params)
    offers = [
        DiscoveredOffer(
            source=source,
            url=url,
            discovered_at=discovered_at,
            discovery_method=method,
            discovery_params={**params, **context},
        )
        for url, context in found
    ]
    store.append_discovered(offers)

    summary = DiscoverSummary(
        observed=len(offers), distinct_urls=len({o.url for o in offers})
    )
    logger.info(
        "discover %s: %d observed, %d distinct",
        source,
        summary.observed,
        summary.distinct_urls,
    )
    return summary
