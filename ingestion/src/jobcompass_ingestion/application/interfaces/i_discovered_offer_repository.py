"""
i_discovered_offer_repository.py

Description : interface of the store of discovered offers (DiscoveredOffer).
Rules       : append only, one line per observation: the same URL is written again
              at each discovery run.
              Deduplication happens downstream (pending offers, dbt), never here.
              list_offer_keys returns (source, url) in order of discovery,
              duplicates included.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from jobcompass_contracts import DiscoveredOffer
from jobcompass_ingestion.domain.pending_offers import OfferKey


class IDiscoveredOfferRepository(ABC):
    @abstractmethod
    async def append(self, offers: Sequence[DiscoveredOffer]) -> None: ...

    @abstractmethod
    async def list_offer_keys(self, source: str) -> list[OfferKey]: ...
