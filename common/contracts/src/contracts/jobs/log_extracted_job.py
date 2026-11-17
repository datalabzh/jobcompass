"""
log_extracted_job.py

Description : contrat du journal d'un échec de parsing d'une page de détail.
Règles      : un enregistrement par tentative échouée (ex. pas de JSON-LD) ; un
              succès donne un ExtractedJob à la place.
              Un échec vaut pour (raw_hash, parser, parser_version) : une nouvelle
              version du parseur retente la page.
              error = raison courte, jamais le contenu.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import JobUrl, Sha256Hash, SourceSlug


class LogExtractedJob(ContractModel):
    """One failed parsing of a job detail page."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    url: JobUrl
    raw_hash: Sha256Hash
    parser: str = Field(description="Name of the parser, e.g. 'jobup_jsonld'")
    parser_version: str = Field(description="Version of the parser")
    attempted_at: AwareDatetime
    error: str = Field(description="Short reason of the failure")
