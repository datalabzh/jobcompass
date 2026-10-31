"""
test_raw_content_hash.py

Description : tests of the raw_hash computation.
Rules       : the hash is stable, depends only on the content, and is accepted by
              the RawOffer contract.
"""

from datetime import datetime, timezone

from jobcompass_contracts import RawOffer, compute_raw_hash


def test_known_value():
    assert compute_raw_hash(b"") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_same_content_same_hash():
    assert compute_raw_hash(b"<html></html>") == compute_raw_hash(b"<html></html>")


def test_different_content_different_hash():
    assert compute_raw_hash(b"a") != compute_raw_hash(b"b")


def test_hash_accepted_by_raw_offer():
    RawOffer(
        source="jobup",
        url="https://www.jobup.ch/fr/emplois/detail/abc/",
        raw_hash=compute_raw_hash(b"<html></html>"),
        content_type="text/html",
        fetched_at=datetime(2026, 10, 31, tzinfo=timezone.utc),
        http_status=200,
        scraper_version="0.1.0",
    )
