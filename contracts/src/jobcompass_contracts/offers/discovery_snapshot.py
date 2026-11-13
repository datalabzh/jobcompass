"""
discovery_snapshot.py

Description : contract of a completed discovery run (snapshot) of a portal.
Rules       : written once, at the end of a run, only if every result page was read
              without error. No record = run incomplete: its DiscoveredOffer lines
              must not be used to decide that an offer has disappeared.
              announced_total = total announced by the portal, used in SQL to check
              that the snapshot is plausible (distinct_urls close to it).
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from jobcompass_contracts.building_blocks.contract_model import ContractModel
from jobcompass_contracts.building_blocks.enums import DiscoveryMethod
from jobcompass_contracts.building_blocks.field_types import SourceSlug


class DiscoverySnapshot(ContractModel):
    """A completed discovery run of a portal."""

    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str = Field(description="Id of the discovery run (UUID)")
    source: SourceSlug
    discovery_method: DiscoveryMethod
    discovery_params: dict[str, str] = Field(default_factory=dict)
    started_at: AwareDatetime
    finished_at: AwareDatetime
    announced_total: int | None = Field(
        default=None, ge=0, description="Total of offers announced by the portal"
    )
    pages_read: int = Field(ge=0)
    offers_seen: int = Field(ge=0, description="Lines written, duplicates included")
    distinct_urls: int = Field(ge=0)
