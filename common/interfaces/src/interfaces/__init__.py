"""
__init__.py

Description : API publique des interfaces de JobCompass, partagées par toutes les
              briques et tous les sites.
Règles      : on importe uniquement d'ici (from interfaces import ...).
              Des interfaces seulement, un fichier par interface : aucun contrat de
              données (voir contracts) et aucune logique métier.
"""

from interfaces.i_get_page import GetPage, Page, PageFetchError
from interfaces.i_site_extraction import (
    DetailsSummary,
    ExtractionReport,
    ISiteExtraction,
)
from interfaces.i_storage import IStorage
from interfaces.i_use_case import IUseCase

__all__ = [
    "DetailsSummary",
    "ExtractionReport",
    "GetPage",
    "ISiteExtraction",
    "IStorage",
    "IUseCase",
    "Page",
    "PageFetchError",
]
