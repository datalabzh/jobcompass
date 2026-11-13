"""
job_info_extraction_log.py

Description : contract of the log of one extract_job_infos run.
Rules       : one record per run, written at its end: status 'completed' if every
              result page was read, 'failed' with the error otherwise.
              A run without any record was killed (machine stopped): treated as failed.
              Only completed runs with a plausible count (distinct_urls close to
              announced_total) are used in SQL to decide that a job has disappeared.
              Counts cover what was written before the end or the error.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.blocks.components import RunStatus, SourceSlug
from contracts.blocks.contract_model import ContractModel


class JobInfoExtractionLog(ContractModel):
    """Log of one extract_job_infos run."""

    schema_version: Literal["1.0"] = "1.0"
    run_id: str = Field(description="Id of the extraction run (UUID)")
    source: SourceSlug
    listing_params: dict[str, str] = Field(default_factory=dict)
    started_at: AwareDatetime
    finished_at: AwareDatetime
    status: RunStatus
    error: str | None = Field(default=None, description="Error that stopped the run")
    announced_total: int | None = Field(
        default=None, ge=0, description="Total of jobs announced by the portal"
    )
    pages_read: int = Field(ge=0)
    jobs_seen: int = Field(ge=0, description="Records written, duplicates included")
    distinct_urls: int = Field(ge=0)
