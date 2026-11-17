"""
i_get_page.py

Description : ce que reçoit tout extracteur pour télécharger une page : une
              fonction get_page(url) -> Page.
Règles      : la page est renvoyée quel que soit son statut HTTP (404, 500...) :
              décider de ce que signifie un statut est le travail de l'appelant.
              PageFetchError uniquement quand aucune réponse n'a été reçue (réseau,
              timeout).
              L'implémentation (user agent, délai de politesse) est dans
              extraction/http.py ; les tests en fournissent une fausse.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    """Answer received for one URL: body unchanged, any HTTP status."""

    content: bytes
    http_status: int
    content_type: str


class PageFetchError(Exception):
    """No HTTP answer was received for the URL (network error, timeout)."""


GetPage = Callable[[str], Page]
