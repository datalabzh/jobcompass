"""
__init__.py

Description : API publique des interfaces propres à la normalisation.
Règles      : on importe uniquement d'ici (from normalization.interfaces import ...).
              Les interfaces partagées avec d'autres briques (IStorage, IUseCase)
              restent dans le paquet commun interfaces.
"""

from normalization.interfaces.i_normalization_uc import (
    INormalizationUseCase,
    NormalizationReport,
)

__all__ = [
    "INormalizationUseCase",
    "NormalizationReport",
]
