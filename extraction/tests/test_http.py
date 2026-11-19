"""
test_http.py

Description : tests du téléchargement de page.
Règles      : tout statut HTTP est renvoyé comme une page ; l'absence de réponse lève
              PageFetchError ; le user agent est envoyé ; le délai de politesse est
              respecté. Pas de réseau : les réponses viennent d'un MockTransport httpx.
"""

import time

import httpx
import pytest

from extraction.http import make_get_page
from extraction.interfaces import GetPage, Page, PageFetchError

URL: str = "https://www.example.ch/page"


def get_page_answering(handler: httpx.MockTransport, min_delay: float = 0.0) -> GetPage:
    """A get_page whose answers come from the mock transport."""
    return make_get_page("JobCompass-test", 5.0, min_delay, transport=handler)


def test_status_returned_as_page() -> None:
    """A 404 is a page like any other, with its status and body."""
    transport: httpx.MockTransport = httpx.MockTransport(
        lambda request: httpx.Response(
            404, text="gone", headers={"content-type": "text/html"}
        )
    )
    result: Page = get_page_answering(transport)(URL)
    assert (result.http_status, result.content, result.content_type) == (
        404,
        b"gone",
        "text/html",
    )


def test_user_agent_sent() -> None:
    """Every request carries the configured user agent."""
    agents: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        """Record the user agent and answer 200."""
        agents.append(request.headers["user-agent"])
        return httpx.Response(200)

    get_page_answering(httpx.MockTransport(answer))(URL)
    assert agents == ["JobCompass-test"]


def test_no_answer_raises() -> None:
    """A network error raises PageFetchError."""

    def fail(request: httpx.Request) -> httpx.Response:
        """Simulate a refused connection."""
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(PageFetchError):
        get_page_answering(httpx.MockTransport(fail))(URL)


def test_politeness_delay() -> None:
    """Two requests are at least min_delay seconds apart."""
    get_page: GetPage = get_page_answering(
        httpx.MockTransport(lambda request: httpx.Response(200)), min_delay=0.2
    )
    start: float = time.monotonic()
    get_page(URL)
    get_page(URL)
    assert time.monotonic() - start >= 0.2
