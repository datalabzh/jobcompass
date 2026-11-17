"""
__init__.py

Description : API publique des interfaces de JobCompass, partagées par toutes les
              briques et tous les sites.
Règles      : on importe uniquement d'ici (from interfaces import ...).
              Des interfaces seulement, un fichier par interface : aucun contrat de
              données (voir contracts) et aucune logique métier.
              Deux familles, deux dossiers :
                use_cases/       ce qui porte le métier : les cas d'utilisation
                                 (IUseCase et ses déclinaisons, une seule méthode
                                 publique execute) et les composants qu'ils
                                 utilisent pour lire les données (IParser).
                                 Les classes concrètes déclarent leur signature
                                 (nom, version...), vérifiée dès leur définition.
                infrastructure/  ce qui parle au monde extérieur : stockage
                                 (IStorage) et réseau (GetPage).
"""

from interfaces.infrastructure.i_get_page import GetPage, Page, PageFetchError
from interfaces.infrastructure.i_storage import IStorage
from interfaces.use_cases.i_normalization import INormalization, NormalizationReport
from interfaces.use_cases.i_parser import IParser, ParsingError
from interfaces.use_cases.i_site_extraction import (
    DetailsSummary,
    ExtractionReport,
    ISiteExtraction,
)
from interfaces.use_cases.i_use_case import IUseCase

__all__ = [
    "DetailsSummary",
    "ExtractionReport",
    "GetPage",
    "INormalization",
    "IParser",
    "ISiteExtraction",
    "IStorage",
    "IUseCase",
    "NormalizationReport",
    "Page",
    "PageFetchError",
    "ParsingError",
]
