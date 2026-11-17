"""
log_raw_job_detail.py

Description : contrat du journal d'un échec de téléchargement d'une page de détail.
Règles      : un enregistrement par tentative échouée (pas de réponse ou statut
              non 2xx) ; un succès donne un RawJobDetail à la place.
              Nombre d'échecs d'une offre = son nombre d'enregistrements ; au-delà
              de max_failures, l'offre est mise de côté et n'est plus téléchargée.
              error = raison courte (pas de réponse, statut HTTP), jamais le contenu.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import JobUrl, SourceSlug


class LogRawJobDetail(ContractModel):
    """One failed download of a job detail page."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    url: JobUrl
    attempted_at: AwareDatetime
    error: str = Field(description="Short reason of the failure")
