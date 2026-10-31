from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from jobcompass_contracts import DiscoveredOffer, DiscoveryMethod, RawOffer

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
URL = "https://www.jobup.ch/fr/emplois/detail/6fa1cc88-7f8c-4806-ba04-d4369180c2e4/"
HASH = "a" * 64


def test_discovered_offer_valid():
    offer = DiscoveredOffer(
        source="jobup",
        url=URL,
        discovered_at=NOW,
        discovery_method=DiscoveryMethod.LISTING,
        discovery_params={"category": "702", "page": "1"},
    )
    assert offer.schema_version == "1.0"


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
