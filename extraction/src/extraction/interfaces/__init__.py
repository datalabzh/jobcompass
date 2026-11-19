"""
__init__.py

Description : API publique des interfaces propres à l'extraction.
Règles      : on importe uniquement d'ici (from extraction.interfaces import ...).
              Les interfaces partagées avec d'autres briques restent hors de la
              brique : IUseCase dans interfaces, celles du stockage dans
              storage.interfaces.
"""

from extraction.interfaces.i_get_page import GetPage, Page, PageFetchError
from extraction.interfaces.i_parser import IParser, ParsingError
from extraction.interfaces.i_site_extraction_uc import (
    DetailsSummary,
    ExtractionReport,
    ISiteExtractionUseCase,
)

__all__ = [
    "DetailsSummary",
    "ExtractionReport",
    "GetPage",
    "IParser",
    "ISiteExtractionUseCase",
    "Page",
    "PageFetchError",
    "ParsingError",
]
