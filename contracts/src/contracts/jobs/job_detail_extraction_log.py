"""
job_detail_extraction_log.py

Description : contract of the log of one failed download of a job detail page.
Rules       : one record per failed attempt (no answer or non-2xx status); a success
              is a JobDetail instead.
              The number of failures of a job = its number of records; after
              max_failures records, the job is set aside and no longer downloaded.
              error = short reason (no answer, HTTP status), never the content.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.blocks.components import JobUrl, SourceSlug
from contracts.blocks.contract_model import ContractModel


class JobDetailExtractionLog(ContractModel):
    """One failed download of a job detail page."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    url: JobUrl
    attempted_at: AwareDatetime
    error: str = Field(description="Short reason of the failure")
