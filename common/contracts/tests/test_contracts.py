"""
test_contracts.py

Description : tests des contrats RawJobInfo, LogRawJobInfo, RawJobDetail,
              LogRawJobDetail et NormalizedJob.
Règles      : couvre les enregistrements valides, les valeurs rejetées (dates sans
              fuseau, hash invalide, statut non 2xx, payload non JSON, format de
              payload inconnu, champ inconnu, is_test absent) et l'aller-retour
              JSON.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from contracts.components.field_types import PayloadFormat, RunStatus, SkillOrigin
from contracts.jobs.log_raw_job_detail import LogRawJobDetail
from contracts.jobs.log_raw_job_info import LogRawJobInfo
from contracts.jobs.normalized_job import NormalizedJob, NormalizedSkill
from contracts.jobs.raw_job_detail import RawJobDetail
from contracts.jobs.raw_job_info import RawJobInfo

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
        "hash_html_id": HASH,
        "content_type": "text/html",
        "fetched_at": NOW,
        "http_status": 200,
        "scraper": "jobup_scraper",
        "scraper_version": "0.1.0",
        "payload_format": PayloadFormat.JSON_LD,
        "payload": '{"@type": "JobPosting", "title": "Data Engineer"}',
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
    """A complete RawJobDetail is accepted, in version 2.0."""
    detail: RawJobDetail = job_detail()
    assert detail.schema_version == "3.0"
    assert detail.payload_format == "json_ld"


def test_job_detail_paragraphs_valid() -> None:
    """Without JSON-LD, the payload is the list of paragraphs, as JSON."""
    detail: RawJobDetail = job_detail(
        payload_format=PayloadFormat.PARAGRAPHS,
        payload='["Data Engineer", "Vos missions : ..."]',
    )
    assert detail.payload_format == "paragraphs"


def test_payload_not_json_rejected() -> None:
    """A payload that is not JSON text is rejected: dbt must parse it."""
    with pytest.raises(ValidationError):
        job_detail(payload="Data Engineer, Geneva")


def test_unknown_payload_format_rejected() -> None:
    """A payload format outside json_ld / paragraphs is rejected."""
    with pytest.raises(ValidationError):
        job_detail(payload_format="html")


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
    """A hash_html_id that is not a SHA-256 is rejected."""
    with pytest.raises(ValidationError):
        job_detail(hash_html_id="not-a-hash")


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


def test_normalized_job_valid() -> None:
    """A NormalizedJob carries its signature and its skills."""
    job: NormalizedJob = NormalizedJob(
        source="jobup",
        is_test=False,
        hash_html_id=HASH,
        scraper="jobup_extraction",
        scraper_version="0.1.0",
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
    assert (job.schema_version, job.skills[0].origin) == ("2.0", "detected")


def test_unknown_skill_origin_rejected() -> None:
    """A skill origin outside declared / detected is rejected."""
    with pytest.raises(ValidationError):
        NormalizedSkill(raw="SQL", canonical="sql", origin="guessed")
