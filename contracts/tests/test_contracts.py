"""
test_contracts.py

Description : tests of the DiscoveredOffer, DiscoverySnapshot and RawOffer contracts.
Rules       : covers valid records, rejected values (naive dates, bad hash,
              unknown field) and the JSON round trip.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from jobcompass_contracts import (
    DiscoveredOffer,
    DiscoveryMethod,
    DiscoverySnapshot,
    RawOffer,
)

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
URL = "https://www.jobup.ch/fr/emplois/detail/6fa1cc88-7f8c-4806-ba04-d4369180c2e4/"
HASH = "a" * 64
SNAPSHOT = "0b9f3c2e-6a4e-4f0e-9d7a-2f4b8c1d5e6f"


def test_discovered_offer_valid():
    offer = DiscoveredOffer(
        snapshot_id=SNAPSHOT,
        source="jobup",
        url=URL,
        discovered_at=NOW,
        discovery_method=DiscoveryMethod.LISTING,
        discovery_params={"category": "702"},
        listing_payload='{"id": "6fa1cc88"}',
    )
    assert offer.schema_version == "1.0"


def test_discovery_snapshot_valid():
    snapshot = DiscoverySnapshot(
        snapshot_id=SNAPSHOT,
        source="jobup",
        discovery_method="listing",
        discovery_params={"category": "702"},
        started_at=NOW,
        finished_at=NOW,
        announced_total=786,
        pages_read=40,
        offers_seen=802,
        distinct_urls=786,
    )
    assert snapshot.announced_total == 786


def test_raw_offer_valid():
    raw = RawOffer(
        source="jobup",
        url=URL,
        raw_hash=HASH,
        content_type="text/html",
        fetched_at=NOW,
        http_status=200,
        scraper_version="0.1.0",
    )
    assert raw.source_lastmod is None


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        DiscoveredOffer(
            snapshot_id=SNAPSHOT,
            source="jobup",
            url=URL,
            discovered_at=datetime(2026, 10, 31),
            discovery_method="listing",
        )


def test_invalid_hash_rejected():
    with pytest.raises(ValidationError):
        RawOffer(
            source="jobup",
            url=URL,
            raw_hash="not-a-hash",
            content_type="text/html",
            fetched_at=NOW,
            http_status=200,
            scraper_version="0.1.0",
        )


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        DiscoveredOffer(
            snapshot_id=SNAPSHOT,
            source="jobup",
            url=URL,
            discovered_at=NOW,
            discovery_method="listing",
            company="Swissquote",
        )


def test_roundtrip_json():
    raw = RawOffer(
        source="jobup",
        url=URL,
        raw_hash=HASH,
        content_type="text/html",
        fetched_at=NOW,
        http_status=200,
        scraper_version="0.1.0",
    )
    assert RawOffer.model_validate_json(raw.model_dump_json()) == raw
