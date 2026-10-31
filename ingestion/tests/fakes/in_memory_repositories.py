"""
in_memory_repositories.py

Description : in-memory implementations of the ingestion repositories, for tests.
Rules       : same behaviour as the interfaces (append only, order kept),
              data kept in public lists so tests can inspect them.
"""

from collections import Counter
from collections.abc import Sequence

from jobcompass_contracts import DiscoveredOffer, RawOffer
from jobcompass_ingestion.application.interfaces.i_discovered_offer_repository import (
    IDiscoveredOfferRepository,
)
from jobcompass_ingestion.application.interfaces.i_fetch_attempt_repository import (
    IFetchAttemptRepository,
)
from jobcompass_ingestion.application.interfaces.i_raw_offer_repository import (
    IRawOfferRepository,
)
from jobcompass_ingestion.domain.fetch_attempt import FetchAttempt
from jobcompass_ingestion.domain.pending_offers import OfferKey


class InMemoryDiscoveredOfferRepository(IDiscoveredOfferRepository):
    def __init__(self, offers: Sequence[DiscoveredOffer] = ()) -> None:
        self.offers: list[DiscoveredOffer] = list(offers)

    async def append(self, offers: Sequence[DiscoveredOffer]) -> None:
        self.offers.extend(offers)

    async def list_offer_keys(self, source: str) -> list[OfferKey]:
        return [(o.source, o.url) for o in self.offers if o.source == source]


class InMemoryRawOfferRepository(IRawOfferRepository):
    def __init__(self) -> None:
        self.raw_offers: list[RawOffer] = []

    async def append(self, raw_offers: Sequence[RawOffer]) -> None:
        self.raw_offers.extend(raw_offers)

    async def list_fetched_keys(self, source: str) -> set[OfferKey]:
        return {(r.source, r.url) for r in self.raw_offers if r.source == source}


class InMemoryFetchAttemptRepository(IFetchAttemptRepository):
    def __init__(self, attempts: Sequence[FetchAttempt] = ()) -> None:
        self.attempts: list[FetchAttempt] = list(attempts)

    async def append(self, attempts: Sequence[FetchAttempt]) -> None:
        self.attempts.extend(attempts)

    async def count_failures(self, source: str) -> dict[OfferKey, int]:
        return dict(
            Counter((a.source, a.url) for a in self.attempts if a.source == source)
        )
