"""
raw_job_detail.py

Description : contrat d'une page de détail d'offre téléchargée avec succès, avec son
              bloc de données brut.
Règles      : produit par le scraper du site, au téléchargement ; consommé par le
              staging dbt (ADR-0002 : Python dépose le brut, dbt met en forme).
              La page est stockée telle quelle, adressée par hash_html_id : son chemin
              de stockage se déduit du hash et ne fait volontairement pas partie du
              contrat.
              Une ligne = une extraction d'une page par une version du scraper :
              unique sur (hash_html_id, scraper, scraper_version).
              Les données de la liste sont absentes : elles sont dans RawJobInfo.
              payload = le bloc de données de la page, tel quel, toujours en texte
              JSON (vérifié) ; payload_format dit lequel :
                json_ld    = le JSON-LD de la page, jamais modifié ;
                paragraphs = à défaut, la liste des paragraphes du HTML (texte),
                             dans l'ordre de la page.
              Aucun champ n'est choisi ni renommé ici : c'est le travail de dbt.
              scraper + scraper_version = le code qui a téléchargé et extrait la
              page. Extraction modifiée = nouvelle version : on relit le HTML stocké
              et on ajoute des lignes ; le staging garde la version la plus récente.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

import json
from typing import Literal

from pydantic import AwareDatetime, Field, field_validator

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import (
    JobUrl,
    PayloadFormat,
    Sha256Hash,
    SourceSlug,
)


class RawJobDetail(ContractModel):
    """One job detail page downloaded with success, with its raw data block."""

    schema_version: Literal["3.0"] = "3.0"
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    url: JobUrl
    hash_html_id: Sha256Hash
    content_type: str = Field(description="Content-Type of the answer")
    fetched_at: AwareDatetime
    http_status: int = Field(ge=200, le=299)
    scraper: str = Field(description="Name of the scraper, e.g. 'jobup_scraper'")
    scraper_version: str = Field(description="Version of the code that fetched it")
    payload_format: PayloadFormat
    payload: str = Field(description="Raw data block of the page, as JSON text")

    @field_validator("payload")
    @classmethod
    def payload_is_json(cls, payload: str) -> str:
        """Refuse a payload that is not JSON text: dbt must always parse it."""
        json.loads(payload)  # ValueError (JSONDecodeError) -> ValidationError
        return payload
