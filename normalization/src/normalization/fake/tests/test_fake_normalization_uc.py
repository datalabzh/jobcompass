"""
test_fake_normalization_uc.py

Description : tests de la normalisation factice.
Règles      : vrai stockage dans un dossier temporaire, alimenté avec des
              ExtractedJob construits pour le test. Couvre : compétences déclarées et
              détectées (casse, limites de mots, pas de doublon), signature du
              normaliseur, limite max_jobs, reprise (rien de normalisé deux fois),
              un nouveau parseur qui donne un nouveau job à normaliser, la zone de
              test.
"""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from catalog import Table
from contracts import ExtractedJob
from normalization.fake.fake_normalization_uc import FakeNormalizationUseCase
from normalization.interfaces import NormalizationReport
from storage.postgres_db_storage import PostgresDbStorage

NOW: datetime = datetime(2026, 11, 17, 15, 0, tzinfo=UTC)


@pytest.fixture
def storage(tmp_path: Path) -> PostgresDbStorage:
    """A real storage for real runs, writing into the test's temporary folder."""
    return PostgresDbStorage(is_test=True)  # rewritten at step 3


def extracted(
    name: str,
    description: str = "",
    declared_skills: list[str] | None = None,
    parser_version: str = "1.0.0",
    is_test: bool = False,
) -> ExtractedJob:
    """An extracted jobup job, identified by its name."""
    return ExtractedJob(
        source="jobup",
        is_test=is_test,
        url=f"https://www.jobup.ch/fr/emplois/detail/{name}/",
        raw_hash=name[0] * 64,
        parser="jobup_parser",
        parser_version=parser_version,
        parsed_at=NOW,
        title=f"Job {name}",
        company=None,
        description=description,
        date_posted=date(2026, 11, 17),
        postal_code=None,
        employment_types=[],
        categories=[],
        declared_skills=declared_skills or [],
    )


def normalization(
    storage: PostgresDbStorage, max_jobs: int | None = None
) -> FakeNormalizationUseCase:
    """A fake normalization of jobup."""
    return FakeNormalizationUseCase(
        source="jobup",
        db_storage=storage,
        is_test=storage.is_test,
        max_jobs=max_jobs,
        now=lambda: NOW,
    )


def skills(storage: PostgresDbStorage) -> list[list[tuple[str, str, str]]]:
    """(raw, canonical, origin) of the skills of every normalized job."""
    return [
        [(s["raw"], s["canonical"], s["origin"]) for s in row["skills"]]
        for row in storage.read(Table.NORMALIZED_JOB, "jobup")
    ]


def test_declared_and_detected_skills(storage: PostgresDbStorage) -> None:
    """Declared skills are kept; keywords are found whatever their case, once."""
    storage.append(
        Table.EXTRACTED_JOB,
        [
            extracted(
                "a",
                description="We use PYTHON, Postgres and Python again; Javascript.",
                declared_skills=["Python", "Leadership"],
            )
        ],
    )

    normalization(storage).execute()

    assert skills(storage) == [
        [
            ("Python", "python", "declared"),
            ("Leadership", "leadership", "declared"),
            ("Javascript", "javascript", "detected"),
            ("Postgres", "postgresql", "detected"),
        ]
    ]


def test_whole_words_only(storage: PostgresDbStorage) -> None:
    """A keyword inside another word is not a skill (SAP in 'SAPEUR', git)."""
    storage.append(
        Table.EXTRACTED_JOB,
        [extracted("a", description="Sapeur digital, legitimate. Uses C# and .NET.")],
    )

    normalization(storage).execute()

    assert [canonical for _, canonical, _ in skills(storage)[0]] == ["c#", ".net"]


def test_signature_recorded(storage: PostgresDbStorage) -> None:
    """Each normalized job carries its input and the signature that made it."""
    storage.append(Table.EXTRACTED_JOB, [extracted("a")])

    normalization(storage).execute()

    (row,) = storage.read(Table.NORMALIZED_JOB, "jobup")
    assert (row["raw_hash"], row["parser_version"]) == ("a" * 64, "1.0.0")
    assert (row["normalizer"], row["model"]) == ("fake_normalization", "keyword_list")
    assert row["normalizer_description"].startswith("Fake skills")


def test_max_jobs_then_resume(storage: PostgresDbStorage) -> None:
    """max_jobs limits a run; the next run only does what remains."""
    storage.append(
        Table.EXTRACTED_JOB, [extracted("a"), extracted("b"), extracted("c")]
    )

    first: NormalizationReport = normalization(storage, max_jobs=2).execute()
    second: NormalizationReport = normalization(storage).execute()

    assert (first.normalized, first.remaining) == (2, 1)
    assert (second.normalized, second.remaining) == (1, 0)
    rows: list[dict[str, Any]] = storage.read(Table.NORMALIZED_JOB, "jobup")
    assert sorted(row["raw_hash"][0] for row in rows) == ["a", "b", "c"]


def test_new_parser_version_normalized_again(storage: PostgresDbStorage) -> None:
    """A page parsed by a new parser version is a new job to normalize."""
    storage.append(Table.EXTRACTED_JOB, [extracted("a")])
    normalization(storage).execute()
    storage.append(Table.EXTRACTED_JOB, [extracted("a", parser_version="1.1.0")])

    report: NormalizationReport = normalization(storage).execute()

    assert report.normalized == 1
    assert len(storage.read(Table.NORMALIZED_JOB, "jobup")) == 2


def test_test_run_reads_and_writes_apart(tmp_path: Path) -> None:
    """A test run only sees test jobs, and writes in the test zone."""
    real: PostgresDbStorage = PostgresDbStorage(is_test=False, data_dir=tmp_path)
    test: PostgresDbStorage = PostgresDbStorage(is_test=True, data_dir=tmp_path)
    real.append(Table.EXTRACTED_JOB, [extracted("a")])
    test.append(Table.EXTRACTED_JOB, [extracted("b", is_test=True)])

    normalization(test).execute()

    assert real.read(Table.NORMALIZED_JOB, "jobup") == []
    assert [row["is_test"] for row in test.read(Table.NORMALIZED_JOB, "jobup")] == [
        True
    ]
