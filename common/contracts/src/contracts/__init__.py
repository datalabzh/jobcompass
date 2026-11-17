"""
__init__.py

Description : API publique des contrats de données JobCompass.
Règles      : les briques importent uniquement d'ici (from contracts import ...),
              jamais depuis les sous-packages : l'organisation interne peut changer
              librement.
              jobs/            = les contrats échangés entre briques.
              components/      = ce dont les contrats sont faits (contract_model,
                                 field_types).
"""

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import RunStatus, compute_raw_hash
from contracts.jobs.raw_job_detail import RawJobDetail
from contracts.jobs.raw_job_detail_extraction_log import RawJobDetailExtractionLog
from contracts.jobs.raw_job_info import RawJobInfo
from contracts.jobs.raw_job_info_extraction_log import RawJobInfoExtractionLog

__all__ = [
    "ContractModel",
    "RawJobDetail",
    "RawJobInfo",
    "RawJobInfoExtractionLog",
    "RawJobDetailExtractionLog",
    "RunStatus",
    "compute_raw_hash",
]
