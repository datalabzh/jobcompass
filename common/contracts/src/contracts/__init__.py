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
from contracts.components.field_types import RunStatus, SkillOrigin, compute_raw_hash
from contracts.jobs.extracted_job import ExtractedJob
from contracts.jobs.log_extracted_job import LogExtractedJob
from contracts.jobs.log_raw_job_detail import LogRawJobDetail
from contracts.jobs.log_raw_job_info import LogRawJobInfo
from contracts.jobs.normalized_job import NormalizedJob, NormalizedSkill
from contracts.jobs.raw_job_detail import RawJobDetail
from contracts.jobs.raw_job_info import RawJobInfo

__all__ = [
    "ContractModel",
    "RawJobDetail",
    "RawJobInfo",
    "LogRawJobInfo",
    "LogRawJobDetail",
    "ExtractedJob",
    "LogExtractedJob",
    "NormalizedJob",
    "NormalizedSkill",
    "RunStatus",
    "SkillOrigin",
    "compute_raw_hash",
]
