"""
test_normalization_cli.py

Description : tests du point d'entrée de la normalisation.
Règles      : le normaliseur par défaut est utilisé sans --normalizer ; un
              normaliseur inconnu arrête la commande ; sans option, la limite du
              normalizer.toml s'applique (test) ; --full la lève et refuse d'être
              combiné ; un passage de test normalise les pages de la zone de test
              (vrai Postgres, zone de test vidée avant) ; une erreur imprévue
              arrête la commande en code 3.
"""

import json
from datetime import UTC, datetime

import pytest

from catalog.tables import Table
from contracts.components.field_types import PayloadFormat
from contracts.jobs.raw_job_detail import RawJobDetail
from entrypoints import normalization_cli
from entrypoints.config.normalization_config import NormalizationConfigReader
from entrypoints.normalization_cli import build_normalization, main, parse_args
from entrypoints.run_limits import RunLimits, resolve_limits
from normalization.interfaces.i_normalization_uc import NormalizationReport
from storage.postgres_db_storage import PostgresDbStorage


def limits(*argv: str) -> RunLimits:
    """The limits of `run jobup <argv>` with a test limit of 10 jobs."""
    return resolve_limits(parse_args(["run", "jobup", *argv]), {"max_jobs": 10})


def test_normalizer_option() -> None:
    """--normalizer names a normalizer folder; absent, the default applies."""
    assert parse_args(["run", "jobup"]).normalizer is None
    assert parse_args(["run", "jobup", "--normalizer", "fake"]).normalizer == "fake"


def test_unknown_normalizer_stops() -> None:
    """An unknown normalizer stops the command before reading any data."""
    assert main(["run", "jobup", "--normalizer", "nowhere"]) == 2


def test_limits() -> None:
    """Default limit = test; --full = real run; both together refused."""
    assert limits() == RunLimits({"max_jobs": 10}) and limits().is_test
    assert not limits("--full").is_test
    with pytest.raises(ValueError, match="--full"):
        limits("--full", "--max-jobs", "3")
    assert main(["run", "jobup", "--full", "--max-jobs", "3"]) == 2


def test_test_run_normalizes() -> None:
    """A test run normalizes the job detail pages of the test zone."""
    storage: PostgresDbStorage = PostgresDbStorage(is_test=True)
    storage.clear_test_zone()
    storage.append(
        Table.RAW_JOB_DETAIL,
        [
            RawJobDetail(
                source="jobup",
                is_test=True,
                url="https://www.jobup.ch/fr/emplois/detail/a/",
                hash_html_id="a" * 64,
                content_type="text/html",
                fetched_at=datetime(2026, 11, 17, tzinfo=UTC),
                http_status=200,
                scraper="jobup_extraction",
                scraper_version="0.1.0",
                payload_format=PayloadFormat.JSON_LD,
                payload=json.dumps(
                    {"title": "Data Engineer", "description": "Python and dbt."}
                ),
            )
        ],
    )

    report: NormalizationReport = build_normalization(
        "jobup",
        NormalizationConfigReader.load_normalization(),
        NormalizationConfigReader.load_normalizer("fake"),
        limits(),
    ).execute()

    assert (report.normalized, report.is_test) == (1, True)
    (row,) = storage.read(Table.NORMALIZED_JOB, "jobup")
    assert [s["canonical"] for s in row["skills"]] == ["python", "dbt"]


def test_unexpected_error_is_code_3(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unexpected error stops the run with code 3."""

    class BrokenNormalizationUseCase:
        """A normalization stopped by an unexpected error."""

        def execute(self) -> None:
            """Fail like an unreachable database."""
            raise ConnectionError("database unreachable")

    monkeypatch.setattr(
        normalization_cli,
        "build_normalization",
        lambda *args: BrokenNormalizationUseCase(),
    )
    assert main(["run", "jobup"]) == 3
