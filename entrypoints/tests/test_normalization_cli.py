"""
test_normalization_cli.py

Description : tests du point d'entrée de la normalisation.
Règles      : le normaliseur par défaut est utilisé sans --normalizer ; un
              normaliseur inconnu arrête la commande ; sans option, la limite du
              normalizer.toml s'applique (test) ; --full la lève et refuse d'être
              combiné ; un passage complet normalise les jobs extraits d'une
              source.
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from catalog import Table
from contracts import ExtractedJob
from entrypoints.config.normalization_config import (
    NormalizationConfig,
    NormalizationConfigReader,
)
from entrypoints.normalization_cli import build_normalization, main, parse_args
from entrypoints.run_limits import RunLimits, resolve_limits
from normalization.interfaces import NormalizationReport
from storage import LocalParquetStorage


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


def test_full_run_normalizes(tmp_path: Path) -> None:
    """A full run normalizes the extracted jobs of the source, as real data."""
    storage: LocalParquetStorage = LocalParquetStorage(is_test=False, data_dir=tmp_path)
    storage.append(
        Table.EXTRACTED_JOB,
        [
            ExtractedJob(
                source="jobup",
                is_test=False,
                url="https://www.jobup.ch/fr/emplois/detail/a/",
                raw_hash="a" * 64,
                parser="jobup_parser",
                parser_version="1.0.0",
                parsed_at=datetime(2026, 11, 17, tzinfo=UTC),
                title="Data Engineer",
                company=None,
                description="Python and dbt.",
                date_posted=date(2026, 11, 17),
                postal_code=None,
                employment_types=[],
                categories=[],
                declared_skills=[],
            )
        ],
    )
    common: NormalizationConfig = (
        NormalizationConfigReader.load_normalization().model_copy(
            update={"storage_options": {"data_dir": str(tmp_path)}}
        )
    )

    report: NormalizationReport = build_normalization(
        "jobup",
        common,
        NormalizationConfigReader.load_normalizer("fake"),
        limits("--full"),
    ).execute()

    assert (report.normalized, report.is_test) == (1, False)
    (row,) = storage.read(Table.NORMALIZED_JOB, "jobup")
    assert [s["canonical"] for s in row["skills"]] == ["python", "dbt"]
