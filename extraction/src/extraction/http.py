"""
http.py

Description : télécharge une page, de la même façon pour tous les sites
              (implémentation de GetPage, voir interfaces/i_get_page.py).
Règles      : un user agent identifiable, un timeout, les redirections suivies.
              Politesse : au moins min_delay secondes entre deux requêtes.
              La page est renvoyée quel que soit son statut HTTP (404, 500...) :
              décider de ce que signifie un statut est le travail de l'appelant.
              PageFetchError uniquement quand aucune réponse n'a été reçue (réseau,
              timeout).
              Ni retry ni cache : un échec est journalisé et retenté au run suivant.
"""

import time

import httpx

from extraction.interfaces.i_get_page import GetPage, Page, PageFetchError


def make_get_page(
    user_agent: str,
    timeout: float,
    min_delay: float,
    transport: httpx.BaseTransport | None = None,
) -> GetPage:
    """Build the get_page function used by the use cases.

    transport is only given by the tests, to answer without network.
    """
    client: httpx.Client = httpx.Client(
        headers={"User-Agent": user_agent},
        timeout=timeout,
        follow_redirects=True,
        transport=transport,
    )
    last_request: list[float] = [0.0]  # time of the previous request

    def get_page(url: str) -> Page:
        """Download one page, after waiting for the politeness delay."""
        wait_politeness_delay(last_request[0], min_delay)
        last_request[0] = time.monotonic()
        try:
            response: httpx.Response = client.get(url)
        except httpx.HTTPError as error:
            raise PageFetchError(f"{type(error).__name__}: {error}") from error
        return Page(
            content=response.content,
            http_status=response.status_code,
            content_type=response.headers.get("content-type", ""),
        )

    return get_page


def wait_politeness_delay(last_request: float, min_delay: float) -> None:
    """Sleep until min_delay seconds have passed since last_request."""
    remaining: float = last_request + min_delay - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)
