"""
__init__.py

Description : public API of the JobCompass data contracts.
Rules       : bricks import only from here (from contracts import ...),
              never from the sub-packages: the internal layout can change freely.
              jobs/            = the contracts exchanged between bricks.
              blocks/          = what the contracts are made of (contract_model,
                                 components).
"""

from contracts.blocks.components import RunStatus, compute_raw_hash
from contracts.blocks.contract_model import ContractModel
from contracts.jobs.job_detail import JobDetail
from contracts.jobs.job_detail_extraction_log import JobDetailExtractionLog
from contracts.jobs.job_info import JobInfo
from contracts.jobs.job_info_extraction_log import JobInfoExtractionLog

__all__ = [
    "ContractModel",
    "JobDetail",
    "JobInfo",
    "JobInfoExtractionLog",
    "JobDetailExtractionLog",
    "RunStatus",
    "compute_raw_hash",
]
