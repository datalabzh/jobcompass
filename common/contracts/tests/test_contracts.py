"""
test_contracts.py

Description : tests des contrats RawJobInfo, LogRawJobInfo, RawJobDetail,
              LogRawJobDetail, ExtractedJob, LogExtractedJob et
              NormalizedJob.
Règles      : couvre les enregistrements valides, les valeurs rejetées (dates sans
              fuseau, hash invalide, statut non 2xx, champ inconnu, is_test absent)
              et l'aller-retour JSON.
"""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from contracts import (
    ExtractedJob,
    LogExtractedJob,
    LogRawJobDetail,
    LogRawJobInfo,
    NormalizedJob,
    NormalizedSkill,
    RawJobDetail,
    RawJobInfo,
    RunStatus,
    SkillOrigin,
)

NOW: datetime = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
URL: str = (
    "https://www.jobup.ch/fr/emplois/detail/6fa1cc88-7f8c-4806-ba04-d4369180c2e4/"
)
HASH: str = "a" * 64
RUN: str = "0b9f3c2e-6a4e-4f0e-9d7a-2f4b8c1d5e6f"


def job_detail(**changes: object) -> RawJobDetail:
    """A valid RawJobDetail, with some fields changed."""
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
    return RawJobDetail(**(fields | changes))


def test_job_info_valid() -> None:
    """A complete RawJobInfo is accepted, in version 1.0."""
    info: RawJobInfo = RawJobInfo(
        run_id=RUN,
        source="jobup",
        is_test=False,
        url=URL,
        seen_at=NOW,
        listing_params={"category": "informatique-telecommunications"},
        card='{"id": "6fa1cc88"}',
    )
    assert info.schema_version == "1.0"


def test_log_raw_job_info_valid() -> None:
    """A failed run is logged with its error and partial counts."""
    log: LogRawJobInfo = LogRawJobInfo(
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
    """A complete RawJobDetail is accepted."""
    assert job_detail().http_status == 200


def test_log_raw_job_detail_valid() -> None:
    """A failed download is logged with its reason."""
    log: LogRawJobDetail = LogRawJobDetail(
        source="jobup", is_test=False, url=URL, attempted_at=NOW, error="HTTP 404"
    )
    assert log.error == "HTTP 404"


def test_naive_datetime_rejected() -> None:
    """A date without time zone is rejected."""
    with pytest.raises(ValidationError):
        RawJobInfo(
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
    """A RawJobDetail is a success: a non-2xx status is rejected."""
    with pytest.raises(ValidationError):
        job_detail(http_status=404)


def test_unknown_field_rejected() -> None:
    """A field not declared in the contract is rejected."""
    with pytest.raises(ValidationError):
        RawJobInfo(
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
        RawJobInfo(run_id=RUN, source="jobup", url=URL, seen_at=NOW)


def test_roundtrip_json() -> None:
    """A record written to JSON and read back is unchanged."""
    detail: RawJobDetail = job_detail()
    assert RawJobDetail.model_validate_json(detail.model_dump_json()) == detail


def extracted_job(**changes: object) -> ExtractedJob:
    """A valid ExtractedJob, with some fields changed."""
    fields: dict[str, object] = {
        "source": "jobup",
        "is_test": False,
        "url": URL,
        "raw_hash": HASH,
        "parser": "jobup_jsonld",
        "parser_version": "1.0.0",
        "parsed_at": NOW,
        "title": "Data Engineer",
        "company": "Acme SA",
        "description": "Python, SQL and Airflow.",
        "date_posted": date(2026, 11, 10),
        "postal_code": "1201",
        "employment_types": ["FULL_TIME"],
        "categories": ["Informatique"],
        "declared_skills": [],
    }
    return ExtractedJob(**(fields | changes))


def test_extracted_job_valid() -> None:
    """A complete ExtractedJob is accepted; absent values are None or empty."""
    job: ExtractedJob = extracted_job(company=None, date_posted=None, categories=[])
    assert job.schema_version == "1.0"
    assert job.company is None and job.categories == []


def test_extracted_job_fields_required() -> None:
    """Optional values must be given explicitly (None), never forgotten."""
    fields: dict[str, object] = extracted_job().model_dump()
    del fields["company"]
    with pytest.raises(ValidationError):
        ExtractedJob(**fields)


def test_log_extracted_job_valid() -> None:
    """A failed parsing is logged with its parser and reason."""
    log: LogExtractedJob = LogExtractedJob(
        source="jobup",
        is_test=False,
        url=URL,
        raw_hash=HASH,
        parser="jobup_jsonld",
        parser_version="1.0.0",
        attempted_at=NOW,
        error="no JSON-LD JobPosting",
    )
    assert log.error == "no JSON-LD JobPosting"


def test_normalized_job_valid() -> None:
    """A NormalizedJob carries its signature and its skills."""
    job: NormalizedJob = NormalizedJob(
        source="jobup",
        is_test=False,
        url=URL,
        raw_hash=HASH,
        parser_version="1.0.0",
        normalizer="fake_normalization",
        normalizer_version="0.1.0",
        model="keyword_list",
        model_version="0.1.0",
        normalizer_description="Keywords found in the text.",
        normalized_at=NOW,
        skills=[
            NormalizedSkill(
                raw="Postgres", canonical="postgresql", origin=SkillOrigin.DETECTED
            )
        ],
    )
    assert job.skills[0].origin == "detected"


def test_unknown_skill_origin_rejected() -> None:
    """A skill origin outside declared / detected is rejected."""
    with pytest.raises(ValidationError):
        NormalizedSkill(raw="SQL", canonical="sql", origin="guessed")


def test_extracted_job_roundtrip_json() -> None:
    """An ExtractedJob written to JSON and read back is unchanged."""
    job: ExtractedJob = extracted_job()
    assert ExtractedJob.model_validate_json(job.model_dump_json()) == job
