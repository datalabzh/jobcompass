"""Versioned data contracts exchanged between JobCompass bricks."""

from jobcompass_contracts.discovered_offer import DiscoveredOffer
from jobcompass_contracts.enums import DiscoveryMethod
from jobcompass_contracts.raw_offer import RawOffer

__all__ = ["DiscoveredOffer", "DiscoveryMethod", "RawOffer"]
