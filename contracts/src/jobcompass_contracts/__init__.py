"""
__init__.py

Description : public API of the JobCompass data contracts.
Rules       : bricks import only from here (from jobcompass_contracts import ...),
              never from the sub-packages: the internal layout can change freely.
              offers/          = the contracts exchanged between bricks.
              building_blocks/ = what the contracts are made of.
"""

from jobcompass_contracts.building_blocks.enums import DiscoveryMethod
from jobcompass_contracts.building_blocks.raw_content_hash import compute_raw_hash
from jobcompass_contracts.offers.discovered_offer import DiscoveredOffer
from jobcompass_contracts.offers.raw_offer import RawOffer

__all__ = ["DiscoveredOffer", "DiscoveryMethod", "RawOffer", "compute_raw_hash"]
