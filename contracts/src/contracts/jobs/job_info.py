"""
job_info.py

Description : contrat d'une offre telle que vue sur une page de résultats d'un
              portail (sa carte), avant le téléchargement de sa page de détail.
Règles      : produit par extract_job_infos, un enregistrement par offre et par run
              d'extraction : la même offre est réenregistrée à chaque run (sa durée
              de vie s'en déduit).
              Une offre est identifiée par (source, url).
              run_id = le run d'extraction auquel appartient l'enregistrement (voir
              JobInfoExtractionLog).
              listing_params = contexte du run, ex. {'category': '...'}.
              card = l'offre exactement comme donnée par la page de résultats (texte
              JSON brut, jamais modifié) ; ses champs sont lus plus tard, en SQL.
              is_test = écrit par un passage de test (limité) : jamais pris en
              compte, stocké dans une zone à part.
"""

from typing import Literal

from pydantic import AwareDatetime, Field

from contracts.blocks.components import JobUrl, SourceSlug
from contracts.blocks.contract_model import ContractModel


class JobInfo(ContractModel):
    """A job as seen on a portal result page."""

    schema_version: Literal["1.0"] = "1.0"
    run_id: str = Field(description="Id of the extraction run (UUID)")
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    url: JobUrl
    seen_at: AwareDatetime = Field(description="Time the result page was read")
    listing_params: dict[str, str] = Field(
        default_factory=dict, description="Context of the run, e.g. the category"
    )
    card: str | None = Field(
        default=None, description="Raw JSON of the job as given by the result page"
    )
