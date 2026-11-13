"""
discovered_offer.py

Description : contract of an offer seen on a portal result page, not yet fetched.
Rules       : produced by the ingestion discovery step, consumed by SQL (dbt) models.
              One record per observation: the same URL is recorded at each discovery.
              An offer is identified by (source, url).
              snapshot_id = the discovery run the record belongs to; the run is
              complete only if a DiscoverySnapshot with the same id exists.
              discovery_params = context of the discovery, e.g. the category.
              listing_payload = the offer exactly as given by the result page (raw
              JSON text, never modified); fields are extracted later, in SQL.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from jobcompass_contracts.building_blocks.contract_model import ContractModel
from jobcompass_contracts.building_blocks.enums import DiscoveryMethod
from jobcompass_contracts.building_blocks.field_types import OfferUrl, SourceSlug


class DiscoveredOffer(ContractModel):
    """An offer seen on a portal result page, not yet fetched."""

    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str = Field(description="Id of the discovery run (UUID)")
    source: SourceSlug
    url: OfferUrl
    discovered_at: AwareDatetime = Field(description="Time the page was read")
    discovery_method: DiscoveryMethod
    discovery_params: dict[str, str] = Field(
        default_factory=dict,
        description="Parameters of the discovery, e.g. {'category': '702'}",
    )
    listing_payload: str | None = Field(
        default=None, description="Raw JSON of the offer as given by the result page"
    )
