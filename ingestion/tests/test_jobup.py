"""
test_jobup.py

Description : tests of the jobup.ch result page reader.
Rules       : runs on a real result page saved in tests/fixtures (no network);
              a page without the __INIT__ block, or a non-200 answer, is an error.
"""

import json
from pathlib import Path

import pytest
from conftest import FakeFetchPage, page

from jobcompass_ingestion.portals.jobup import (
    ListingPageError,
    listing_reader,
    parse_listing_page,
)

FIXTURE = Path(__file__).parent / "fixtures" / "jobup_listing_page.html"
LISTING = "https://www.jobup.ch/fr/emplois/informatique-telecommunications/?page=1"


def test_parse_real_page():
    result = parse_listing_page(FIXTURE.read_text(encoding="utf-8"))

    assert (result.announced_total, result.num_pages) == (786, 40)
    assert len(result.offers) == 22
    url, payload = result.offers[0]
    assert url == (
        "https://www.jobup.ch/fr/emplois/detail/18943dd6-c820-41e9-9e37-0da70fd57866/"
    )
    assert json.loads(payload)["title"] == "Financial Analyst & AI Engineer"


def test_page_without_data_is_an_error():
    with pytest.raises(ListingPageError):
        parse_listing_page("<html>Access denied</html>")


async def test_reader_builds_url_and_parses():
    fetch_page = FakeFetchPage({LISTING: page(content=FIXTURE.read_bytes())})

    result = await listing_reader(fetch_page, "informatique-telecommunications")(1)

    assert fetch_page.requested == [LISTING]
    assert result.num_pages == 40


async def test_reader_rejects_non_200():
    fetch_page = FakeFetchPage({LISTING: page(status=403)})

    with pytest.raises(ListingPageError):
        await listing_reader(fetch_page, "informatique-telecommunications")(1)
