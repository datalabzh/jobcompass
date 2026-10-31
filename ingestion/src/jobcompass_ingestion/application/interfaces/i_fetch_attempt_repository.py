"""
i_fetch_attempt_repository.py

Description : interface of the fetch attempt log (failed attempts only).
Rules       : append only.
              count_failures returns, for each (source, url) of the source,
              the number of failed attempts logged; absent = no failure.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from jobcompass_ingestion.domain.fetch_attempt import FetchAttempt
from jobcompass_ingestion.domain.pending_offers import OfferKey


class IFetchAttemptRepository(ABC):
    @abstractmethod
    async def append(self, attempts: Sequence[FetchAttempt]) -> None: ...

    @abstractmethod
    async def count_failures(self, source: str) -> dict[OfferKey, int]: ...
