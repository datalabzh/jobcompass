"""
__init__.py

Description : API publique des interfaces propres à la normalisation.
Règles      : on importe uniquement d'ici (from normalization.interfaces import ...).
              Les interfaces partagées avec d'autres briques restent hors de la
              brique : IUseCase dans interfaces, celles du stockage dans
              storage.interfaces.
"""

from normalization.interfaces.i_normalization_uc import (
    INormalizationUseCase,
    NormalizationReport,
)

__all__ = [
    "INormalizationUseCase",
    "NormalizationReport",
]
