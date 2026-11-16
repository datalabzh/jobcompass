"""
contract_model.py

Description : parent commun de tous les contrats.
Règles      : ne porte aucun champ, seulement les règles communes à tous les contrats.
              Figé (frozen) : une instance de contrat ne peut plus être modifiée
              une fois créée.
              extra="forbid" : tout champ non déclaré dans le contrat est rejeté.
"""

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Parent of every contract: immutable records, unknown fields rejected."""

    model_config = ConfigDict(frozen=True, extra="forbid")
