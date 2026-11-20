"""
test_hash_html_id.py

Description : tests du calcul de hash_html_id.
Règles      : le hash est stable, ne dépend que du contenu, et est accepté par le
              contrat RawJobDetail.
"""

from datetime import UTC, datetime

from contracts.components.field_types import PayloadFormat, compute_hash_html_id
from contracts.jobs.raw_job_detail import RawJobDetail


def test_known_value() -> None:
    """The hash of empty content is the known SHA-256 value."""
    assert compute_hash_html_id(b"") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_same_content_same_hash() -> None:
    """The same content always gives the same hash."""
    assert compute_hash_html_id(b"<html></html>") == compute_hash_html_id(
        b"<html></html>"
    )


def test_different_content_different_hash() -> None:
    """Different contents give different hashes."""
    assert compute_hash_html_id(b"a") != compute_hash_html_id(b"b")


def test_hash_accepted_by_job_detail() -> None:
    """A computed hash is a valid RawJobDetail hash_html_id."""
    RawJobDetail(
        source="jobup",
        is_test=False,
        url="https://www.jobup.ch/fr/emplois/detail/abc/",
        hash_html_id=compute_hash_html_id(b"<html></html>"),
        content_type="text/html",
        fetched_at=datetime(2026, 10, 31, tzinfo=UTC),
        http_status=200,
        scraper="jobup_scraper",
        scraper_version="0.1.0",
        payload_format=PayloadFormat.PARAGRAPHS,
        payload="[]",
    )
