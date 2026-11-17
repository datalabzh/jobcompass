"""
raw_job_detail.py

Description : contrat d'une page de détail d'offre téléchargée avec succès.
Règles      : produit par extract_job_details, consommé par structuring.
              La page est stockée telle quelle, adressée par raw_hash : son chemin de
              stockage se déduit du hash et ne fait volontairement pas partie du
              contrat.
              Les données de la liste (titre, entreprise...) sont absentes : elles
              sont dans RawJobInfo, et lire la page est le travail de structuring.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import JobUrl, Sha256Hash, SourceSlug


class RawJobDetail(ContractModel):
    """One job detail page downloaded with success."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    url: JobUrl
    raw_hash: Sha256Hash
    content_type: str = Field(description="Content-Type of the answer")
    fetched_at: AwareDatetime
    http_status: int = Field(ge=200, le=299)
    scraper_version: str = Field(description="Version of the code that fetched it")
