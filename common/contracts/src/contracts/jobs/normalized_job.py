"""
normalized_job.py

Description : contrat d'un job normalisé : ce que l'on comprend du job (compétences
              canoniques). Produit final de la normalisation.
Règles      : produit par la normalisation, commune à tous les sites ; consommé par
              l'analytics.
              Rattaché à l'ExtractedJob dont il vient par (raw_hash, parser_version).
              Signé : normaliseur et modèle, chacun avec sa version, et une phrase
              qui dit ce qu'ils font (normalizer_description), pour s'y retrouver
              en lisant la table ; un nouveau normaliseur ou modèle ajoute des
              lignes, les anciennes restent.
              skills = liste de NormalizedSkill (forme brute, forme canonique,
              origine) ; aplatie en une ligne par compétence en SQL.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.components.contract_model import ContractModel
from contracts.components.field_types import (
    JobUrl,
    Sha256Hash,
    SkillOrigin,
    SourceSlug,
)


class NormalizedSkill(ContractModel):
    """One skill of a normalized job."""

    raw: str = Field(description="Skill as written in the source, e.g. 'Postgres'")
    canonical: str = Field(description="Canonical form, e.g. 'postgresql'")
    origin: SkillOrigin


class NormalizedJob(ContractModel):
    """One extracted job, understood: its canonical skills."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    url: JobUrl
    raw_hash: Sha256Hash
    parser_version: str = Field(description="Version of the parser of the input")
    normalizer: str = Field(description="Name of the normalizer")
    normalizer_version: str = Field(description="Version of the normalizer")
    model: str = Field(description="Name of the model used, e.g. 'keyword_list'")
    model_version: str = Field(description="Version of the model")
    normalizer_description: str = Field(
        description="What the normalizer and its model do, in one sentence"
    )
    normalized_at: AwareDatetime
    skills: list[NormalizedSkill]
