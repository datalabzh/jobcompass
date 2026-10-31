"""
i_raw_offer_repository.py

Description : interface of the manifest of fetched offers (RawOffer).
Rules       : append only, a written line is never modified or deleted.
              A line is appended only after its content is stored.
              list_fetched_keys returns the (source, url) fetched with success
              at least once.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from jobcompass_contracts import RawOffer
from jobcompass_ingestion.domain.pending_offers import OfferKey


class IRawOfferRepository(ABC):
    @abstractmethod
    async def append(self, raw_offers: Sequence[RawOffer]) -> None: ...

    @abstractmethod
    async def list_fetched_keys(self, source: str) -> set[OfferKey]: ...
