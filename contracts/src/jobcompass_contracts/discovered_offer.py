from typing import Literal

from pydantic import AwareDatetime, Field

from jobcompass_contracts.contract_model import ContractModel
from jobcompass_contracts.enums import DiscoveryMethod
from jobcompass_contracts.field_types import OfferUrl, SourceSlug


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
