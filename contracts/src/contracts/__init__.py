"""
__init__.py

Description : API publique des contrats de données JobCompass.
Règles      : les briques importent uniquement d'ici (from contracts import ...),
              jamais depuis les sous-packages : l'organisation interne peut changer
              librement.
              jobs/            = les contrats échangés entre briques.
              blocks/          = ce dont les contrats sont faits (contract_model,
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
