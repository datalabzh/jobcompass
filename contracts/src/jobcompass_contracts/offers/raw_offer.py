"""
raw_offer.py

Description : contract of the manifest record of one successfully fetched offer
              content.
Rules       : produced by the ingestion fetch step, consumed by structuring.
              The content is stored unchanged in object storage, addressed by
              raw_hash (see raw_content_hash).
              The storage path is derived from the hash by the storage adapter and is
              deliberately not part of the contract.
              Portal offer id and listing data (title, company...) are deliberately
              absent: unstable, or the job of structuring.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from jobcompass_contracts.building_blocks.contract_model import ContractModel
from jobcompass_contracts.building_blocks.field_types import (
    OfferUrl,
    Sha256Hash,
    SourceSlug,
)


class RawOffer(ContractModel):
    """Manifest record of one successfully fetched offer content.

    The content itself is stored unchanged in object storage, addressed by
    `raw_hash`. The storage location is derived from the hash by the storage
    adapter and is deliberately not part of the contract.
    """

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    url: OfferUrl
    raw_hash: Sha256Hash
    content_type: str = Field(description="e.g. 'text/html', 'application/json'")
    fetched_at: AwareDatetime = Field(description="Fetch time (timezone-aware)")
    http_status: int = Field(ge=100, le=599)
    scraper_version: str = Field(description="Version of the fetcher that produced it")
    source_lastmod: AwareDatetime | None = Field(
        default=None, description="Last modification date announced by the portal"
    )
