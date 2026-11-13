"""
http.py

Description : downloads a page, the same way for every site.
Rules       : one identifiable user agent, a timeout, redirects followed.
              Politeness: at least min_delay seconds between two requests.
              The page is returned whatever its HTTP status (404, 500...): deciding
              what a status means is the caller's job.
              PageFetchError only when no answer was received (network, timeout).
              No retry, no cache: a failure is logged and retried at the next run.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Page:
    """Answer received for one URL: body unchanged, any HTTP status."""

    content: bytes
    http_status: int
    content_type: str


class PageFetchError(Exception):
    """No HTTP answer was received for the URL (network error, timeout)."""


GetPage = Callable[[str], Page]


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
