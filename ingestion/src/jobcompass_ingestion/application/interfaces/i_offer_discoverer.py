"""
i_offer_discoverer.py

Description : interface of a discoverer, reading the result pages of one portal.
Rules       : one implementation per portal (jobup, ...).
              Returns every offer URL found, duplicates included, without
              checking whether it is already known.
              Reads only what robots.txt allows; politeness (rate limit) is the
              implementation's responsibility.
              Raises DiscoveryError when the portal cannot be read at all.
"""

from abc import ABC, abstractmethod

from jobcompass_contracts import DiscoveryMethod
from jobcompass_ingestion.application.dto.found_offer_url_dto import FoundOfferUrl


class DiscoveryError(Exception):
    """The portal could not be read (network, unexpected page structure)."""


class IOfferDiscoverer(ABC):
    @abstractmethod
    async def discover(
        self, method: DiscoveryMethod, params: dict[str, str]
    ) -> list[FoundOfferUrl]: ...
