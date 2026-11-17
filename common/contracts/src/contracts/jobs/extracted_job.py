"""
extracted_job.py

Description : contrat d'un job parsé : ce que dit la source, dans des champs communs
              à tous les sites. Produit final de l'extraction.
Règles      : produit par le parseur du site, consommé par la normalisation.
              Identifié par (raw_hash, parser, parser_version) : un nouveau parseur
              ou une nouvelle version ajoute des lignes, les anciennes restent
              pour comparer.
              Aucune interprétation : les valeurs sont celles de la source (texte
              débarrassé du HTML, dates converties) ; comprendre est le travail
              de la normalisation.
              Champ absent de la source = None, ou liste vide pour les listes.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import JobUrl, Sha256Hash, SourceSlug


class ExtractedJob(ContractModel):
    """One job detail page parsed into the fields common to every site."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    url: JobUrl
    raw_hash: Sha256Hash
    parser: str = Field(description="Name of the parser, e.g. 'jobup_jsonld'")
    parser_version: str = Field(description="Version of the parser")
    parsed_at: AwareDatetime
    title: str
    company: str | None
    description: str = Field(description="Text of the job, without HTML")
    date_posted: date | None
    postal_code: str | None
    employment_types: list[str] = Field(description="As given, e.g. 'FULL_TIME'")
    categories: list[str] = Field(description="Categories given by the source")
    declared_skills: list[str] = Field(description="Skills given by the source")
