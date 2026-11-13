"""
conftest.py

Description : shared test helpers of the ingestion brick.
Rules       : tests use the real Store in a temporary folder (no fake storage);
              only the network is faked, by fake_fetch_page.
"""

from datetime import UTC, datetime

import pytest

from jobcompass_contracts import DiscoveredOffer
from jobcompass_ingestion.fetch import FetchedPage, PageFetchError
from jobcompass_ingestion.storage import Store

NOW = datetime(2026, 11, 13, 6, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


def discovered(*urls, source="jobup", at=NOW):
    return [
        DiscoveredOffer(
            snapshot_id="s1",
            source=source,
            url=url,
            discovered_at=at,
            discovery_method="listing",
        )
        for url in urls
    ]


def page(status=200, content=b"<html>offer</html>"):
    return FetchedPage(content=content, http_status=status, content_type="text/html")


class FakeFetchPage:
    """Answers set up in advance; URL absent = no answer. Records requested URLs."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    async def __call__(self, url):
        self.requested.append(url)
        if url not in self.pages:
            raise PageFetchError("connection refused")
        return self.pages[url]
