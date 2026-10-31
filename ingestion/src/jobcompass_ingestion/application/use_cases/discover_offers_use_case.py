"""
discover_offers_use_case.py

Description : use case reading the result pages of a portal and recording every
              offer URL found as a DiscoveredOffer.
Rules       : every URL seen is written, even if already known (one line per
              observation): nothing is read before writing.
              All URLs of a run share the same discovered_at (start of the run).
              Written once at the end of the run: a failed run writes nothing and
              is simply run again.
              Unknown source = ValueError, no discoverer registered for it.
"""

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from jobcompass_contracts import DiscoveredOffer
from jobcompass_ingestion.application.dto.discover_offers_dto import (
    DiscoverOffersInput,
    DiscoverOffersOutput,
)
from jobcompass_ingestion.application.interfaces.i_discovered_offer_repository import (
    IDiscoveredOfferRepository,
)
from jobcompass_ingestion.application.interfaces.i_offer_discoverer import (
    IOfferDiscoverer,
)

logger = logging.getLogger(__name__)


class DiscoverOffersUseCase:
    def __init__(
        self,
        discoverers: Mapping[str, IOfferDiscoverer],
        discovered_offer_repository: IDiscoveredOfferRepository,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._discoverers = discoverers
        self._repository = discovered_offer_repository
        self._now = now

    async def execute(self, request: DiscoverOffersInput) -> DiscoverOffersOutput:
        discoverer = self._discoverers.get(request.source)
        if discoverer is None:
            raise ValueError(f"no discoverer for source '{request.source}'")

        discovered_at = self._now()
        found = await discoverer.discover(
            request.discovery_method, request.discovery_params
        )
        offers = [
            DiscoveredOffer(
                source=request.source,
                url=item.url,
                discovered_at=discovered_at,
                discovery_method=request.discovery_method,
                discovery_params={**request.discovery_params, **item.params},
            )
            for item in found
        ]
        await self._repository.append(offers)

        output = DiscoverOffersOutput(
            observed=len(offers), distinct_urls=len({o.url for o in offers})
        )
        logger.info(
            "discover %s: %d observed, %d distinct",
            request.source,
            output.observed,
            output.distinct_urls,
        )
        return output
