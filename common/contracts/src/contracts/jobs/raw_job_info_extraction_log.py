"""
raw_job_info_extraction_log.py

Description : contrat du journal d'une extraction des job infos d'une catégorie.
Règles      : un enregistrement par run et par catégorie, écrit à la fin : statut
              'completed' si les pages prévues ont été lues sans erreur (toutes, ou
              max_pages pour un test), 'failed' avec l'erreur sinon.
              Un run sans enregistrement a été tué (machine arrêtée) : traité comme
              échoué.
              Seuls les runs completed, hors test, au comptage plausible
              (distinct_urls proche de announced_total) servent en SQL à décider
              qu'une offre a disparu.
              Les compteurs couvrent ce qui a été écrit avant la fin ou l'erreur.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import RunStatus, SourceSlug


class RawJobInfoExtractionLog(ContractModel):
    """Log of one extract_job_infos run."""

    schema_version: Literal["1.0"] = "1.0"
    run_id: str = Field(description="Id of the extraction run (UUID)")
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
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
