"""
__init__.py

Description : API publique des interfaces partagées par les briques JobCompass.
Règles      : les briques importent uniquement d'ici (from interfaces import ...).
              Des interfaces seulement : aucun contrat de données (voir contracts)
              et aucune logique métier.
"""

from interfaces.i_use_case import IUseCase

__all__ = ["IUseCase"]
