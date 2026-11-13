"""
job_detail.py

Description : contract of one job detail page downloaded with success.
Rules       : produced by extract_job_details, consumed by structuring.
              The page is stored unchanged, addressed by raw_hash: its storage path
              is derived from the hash and deliberately not part of the contract.
              Listing data (title, company...) are absent: they are in JobInfo, and
              reading the page is the job of structuring.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.blocks.components import JobUrl, Sha256Hash, SourceSlug
from contracts.blocks.contract_model import ContractModel


class JobDetail(ContractModel):
    """One job detail page downloaded with success."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    url: JobUrl
    raw_hash: Sha256Hash
    content_type: str = Field(description="Content-Type of the answer")
    fetched_at: AwareDatetime
    http_status: int = Field(ge=200, le=299)
    scraper_version: str = Field(description="Version of the code that fetched it")
