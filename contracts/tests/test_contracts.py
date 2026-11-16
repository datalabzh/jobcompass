"""
test_contracts.py

Description : tests des contrats JobInfo, JobInfoExtractionLog, JobDetail et
              JobDetailExtractionLog.
Règles      : couvre les enregistrements valides, les valeurs rejetées (dates sans
              fuseau, hash invalide, statut non 2xx, champ inconnu, is_test absent)
              et l'aller-retour JSON.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from contracts import (
    JobDetail,
    JobDetailExtractionLog,
    JobInfo,
    JobInfoExtractionLog,
    RunStatus,
)

NOW: datetime = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
URL: str = (
    "https://www.jobup.ch/fr/emplois/detail/6fa1cc88-7f8c-4806-ba04-d4369180c2e4/"
)
HASH: str = "a" * 64
RUN: str = "0b9f3c2e-6a4e-4f0e-9d7a-2f4b8c1d5e6f"


def job_detail(**changes: object) -> JobDetail:
    """A valid JobDetail, with some fields changed."""
    fields: dict[str, object] = {
        "source": "jobup",
        "is_test": False,
        "url": URL,
        "raw_hash": HASH,
        "content_type": "text/html",
        "fetched_at": NOW,
        "http_status": 200,
        "scraper_version": "0.1.0",
    }
    return JobDetail(**(fields | changes))


def test_job_info_valid() -> None:
    """A complete JobInfo is accepted, in version 1.0."""
    info: JobInfo = JobInfo(
        run_id=RUN,
        source="jobup",
        is_test=False,
        url=URL,
        seen_at=NOW,
        listing_params={"category": "informatique-telecommunications"},
        card='{"id": "6fa1cc88"}',
    )
    assert info.schema_version == "1.0"


def test_job_info_extraction_log_valid() -> None:
    """A failed run is logged with its error and partial counts."""
    log: JobInfoExtractionLog = JobInfoExtractionLog(
        run_id=RUN,
        source="jobup",
        is_test=False,
        started_at=NOW,
        finished_at=NOW,
        status=RunStatus.FAILED,
        error="HTTP 403",
        pages_read=11,
        jobs_seen=220,
        distinct_urls=218,
    )
    assert log.status == "failed"
    assert log.announced_total is None


def test_job_detail_valid() -> None:
    """A complete JobDetail is accepted."""
    assert job_detail().http_status == 200


def test_job_detail_extraction_log_valid() -> None:
    """A failed download is logged with its reason."""
    log: JobDetailExtractionLog = JobDetailExtractionLog(
        source="jobup", is_test=False, url=URL, attempted_at=NOW, error="HTTP 404"
    )
    assert log.error == "HTTP 404"


def test_naive_datetime_rejected() -> None:
    """A date without time zone is rejected."""
    with pytest.raises(ValidationError):
        JobInfo(
            run_id=RUN,
            source="jobup",
            is_test=False,
            url=URL,
            seen_at=datetime(2026, 11, 13),
        )


def test_invalid_hash_rejected() -> None:
    """A raw_hash that is not a SHA-256 is rejected."""
    with pytest.raises(ValidationError):
        job_detail(raw_hash="not-a-hash")


def test_non_2xx_detail_rejected() -> None:
    """A JobDetail is a success: a non-2xx status is rejected."""
    with pytest.raises(ValidationError):
        job_detail(http_status=404)


def test_unknown_field_rejected() -> None:
    """A field not declared in the contract is rejected."""
    with pytest.raises(ValidationError):
        JobInfo(
            run_id=RUN,
            source="jobup",
            is_test=False,
            url=URL,
            seen_at=NOW,
            company="X",
        )


def test_is_test_required() -> None:
    """is_test has no default: every record says if it comes from a test run."""
    with pytest.raises(ValidationError):
        JobInfo(run_id=RUN, source="jobup", url=URL, seen_at=NOW)


def test_roundtrip_json() -> None:
    """A record written to JSON and read back is unchanged."""
    detail: JobDetail = job_detail()
    assert JobDetail.model_validate_json(detail.model_dump_json()) == detail
