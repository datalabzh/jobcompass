"""
job_info.py

Description : contract of a job as seen on a portal result page (its card), before
              its detail page is downloaded.
Rules       : produced by extract_job_infos, one record per job per extraction run:
              the same job is recorded again at each run (its lifetime comes from it).
              A job is identified by (source, url).
              run_id = the extraction run the record belongs to (see
              JobInfoExtractionLog).
              listing_params = context of the run, e.g. {'category': '...'}.
              card = the job exactly as given by the result page (raw JSON text,
              never modified); its fields are read later, in SQL.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.blocks.components import JobUrl, SourceSlug
from contracts.blocks.contract_model import ContractModel


class JobInfo(ContractModel):
    """A job as seen on a portal result page."""

    schema_version: Literal["1.0"] = "1.0"
    run_id: str = Field(description="Id of the extraction run (UUID)")
    source: SourceSlug
    url: JobUrl
    seen_at: AwareDatetime = Field(description="Time the result page was read")
    listing_params: dict[str, str] = Field(
        default_factory=dict, description="Context of the run, e.g. the category"
    )
    card: str | None = Field(
        default=None, description="Raw JSON of the job as given by the result page"
    )
