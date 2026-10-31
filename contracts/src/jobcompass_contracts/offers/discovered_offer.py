"""
discovered_offer.py

Description : contract of an offer URL found on a portal, not yet fetched.
Rules       : produced by the ingestion discovery step, consumed by the fetch step.
              One record per observation: the same URL is recorded at each discovery.
              An offer is identified by (source, url).
              discovery_params = context of the discovery, e.g. category and page.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from jobcompass_contracts.building_blocks.contract_model import ContractModel
from jobcompass_contracts.building_blocks.enums import DiscoveryMethod
from jobcompass_contracts.building_blocks.field_types import OfferUrl, SourceSlug


class DiscoveredOffer(ContractModel):
    """An offer URL found on a portal, not yet fetched.

    Produced by the ingestion discovery step; consumed by the fetch step.
    """

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    url: OfferUrl
    discovered_at: AwareDatetime = Field(description="Discovery time (timezone-aware)")
    discovery_method: DiscoveryMethod
    discovery_params: dict[str, str] = Field(
        default_factory=dict,
        description="Parameters of the discovery e.g. {'category': '702', 'page': '3'}",
    )
