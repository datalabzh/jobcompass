"""
__init__.py

Description : API publique des interfaces partagées par plusieurs briques de
              JobCompass.
Règles      : on importe uniquement d'ici (from interfaces import ...).
              Seules les interfaces utilisées par plusieurs briques vivent ici ;
              une interface propre à une brique vit dans cette brique (ex.
              extraction.interfaces, normalization.interfaces).
              Des interfaces seulement, un fichier par interface : aucun contrat de
              données (voir contracts) et aucune logique métier.
"""

from interfaces.i_storage import IStorage
from interfaces.i_use_case import IUseCase

__all__ = [
    "IStorage",
    "IUseCase",
]
