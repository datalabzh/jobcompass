"""
test_fake_normalization_uc.py

Description : tests de la normalisation factice.
Règles      : vrai stockage (zone de test de Postgres, vidée avant chaque test),
              alimenté avec des RawJobDetail construits pour le test. Couvre :
              compétences déclarées (JSON-LD) et détectées (casse, limites de mots,
              pas de doublon), payload en paragraphes, clé recopiée et signature du
              normaliseur, limite max_jobs, reprise (rien de normalisé deux fois),
              une nouvelle version du scraper qui donne une nouvelle page à
              normaliser, une page illisible sautée sans bloquer les suivantes.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest

from catalog.tables import Table
from contracts.components.field_types import PayloadFormat
from contracts.jobs.raw_job_detail import RawJobDetail
from normalization.fake.fake_normalization_uc import FakeNormalizationUseCase
from normalization.interfaces.i_normalization_uc import NormalizationReport
from storage.postgres_db_storage import PostgresDbStorage

NOW: datetime = datetime(2026, 11, 17, 15, 0, tzinfo=UTC)


@pytest.fixture
def storage() -> Iterator[PostgresDbStorage]:
    """The test zone of the real Postgres, emptied before the test."""
    test: PostgresDbStorage = PostgresDbStorage(is_test=True)
    test.clear_test_zone()
    yield test


def detail(
    name: str,
    description: str = "",
    skills: Any = None,  # noqa: ANN401
    scraper_version: str = "0.1.0",
    paragraphs: list[str] | None = None,
) -> RawJobDetail:
    """A jobup job detail page, identified by its name (one letter)."""
    payload: Any = (
        paragraphs
        if paragraphs is not None
        else {"@type": "JobPosting", "title": f"Job {name}", "description": description}
        | ({"skills": skills} if skills is not None else {})
    )
    return RawJobDetail(
        source="jobup",
        is_test=True,
        url=f"https://www.jobup.ch/fr/emplois/detail/{name}/",
        hash_html_id=name * 64,
        content_type="text/html",
        fetched_at=NOW,
        http_status=200,
        scraper="jobup_extraction",
        scraper_version=scraper_version,
        payload_format=(
            PayloadFormat.PARAGRAPHS
            if paragraphs is not None
            else PayloadFormat.JSON_LD
        ),
        payload=json.dumps(payload),
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
        Table.RAW_JOB_DETAIL,
        [
            detail(
                "a",
                description="We use PYTHON, Postgres and Python again; Javascript.",
                skills=["Python", "Leadership"],
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


def test_declared_skills_as_text(storage: PostgresDbStorage) -> None:
    """A skills key written as text is split on commas."""
    storage.append(Table.RAW_JOB_DETAIL, [detail("a", skills="SQL, Scrum ,")])

    normalization(storage).execute()

    assert skills(storage) == [
        [("SQL", "sql", "declared"), ("Scrum", "scrum", "declared")]
    ]


def test_paragraphs_payload(storage: PostgresDbStorage) -> None:
    """Without JSON-LD, keywords are searched in the paragraphs; none declared."""
    storage.append(
        Table.RAW_JOB_DETAIL,
        [detail("a", paragraphs=["Data Engineer", "Spark et Airflow."])],
    )

    normalization(storage).execute()

    assert skills(storage) == [
        [("Spark", "spark", "detected"), ("Airflow", "airflow", "detected")]
    ]


def test_whole_words_only(storage: PostgresDbStorage) -> None:
    """A keyword inside another word is not a skill (SAP in 'SAPEUR', git)."""
    storage.append(
        Table.RAW_JOB_DETAIL,
        [detail("a", description="Sapeur digital, legitimate. Uses C# and .NET.")],
    )

    normalization(storage).execute()

    assert [canonical for _, canonical, _ in skills(storage)[0]] == ["c#", ".net"]


def test_key_copied_and_signature_recorded(storage: PostgresDbStorage) -> None:
    """Each normalized job copies the key of its page and carries its signature."""
    storage.append(Table.RAW_JOB_DETAIL, [detail("a")])

    normalization(storage).execute()

    (row,) = storage.read(Table.NORMALIZED_JOB, "jobup")
    assert (row["hash_html_id"], row["scraper"], row["scraper_version"]) == (
        "a" * 64,
        "jobup_extraction",
        "0.1.0",
    )
    assert (row["normalizer"], row["normalizer_version"], row["model"]) == (
        "fake_normalization",
        "0.2.0",
        "keyword_list",
    )
    assert row["normalizer_description"].startswith("Fake skills")
    assert row["is_test"]


def test_max_jobs_then_resume(storage: PostgresDbStorage) -> None:
    """max_jobs limits a run; the next run only does what remains."""
    storage.append(Table.RAW_JOB_DETAIL, [detail("a"), detail("b"), detail("c")])

    first: NormalizationReport = normalization(storage, max_jobs=2).execute()
    second: NormalizationReport = normalization(storage).execute()
    third: NormalizationReport = normalization(storage).execute()

    assert (first.normalized, first.remaining) == (2, 1)
    assert (second.normalized, second.remaining) == (1, 0)
    assert (third.normalized, third.remaining) == (0, 0)
    rows: list[dict[str, Any]] = storage.read(Table.NORMALIZED_JOB, "jobup")
    assert sorted(row["hash_html_id"][0] for row in rows) == ["a", "b", "c"]


def test_new_scraper_version_normalized_again(storage: PostgresDbStorage) -> None:
    """The same page extracted by a new scraper version is a new page to normalize."""
    storage.append(Table.RAW_JOB_DETAIL, [detail("a")])
    normalization(storage).execute()
    storage.append(Table.RAW_JOB_DETAIL, [detail("a", scraper_version="0.2.0")])

    report: NormalizationReport = normalization(storage).execute()

    assert report.normalized == 1
    assert len(storage.read(Table.NORMALIZED_JOB, "jobup")) == 2


def test_unreadable_page_skipped(storage: PostgresDbStorage) -> None:
    """A page that cannot be normalized is skipped and counted; the next is done."""
    unreadable: RawJobDetail = RawJobDetail(
        source="jobup",
        is_test=True,
        url="https://www.jobup.ch/fr/emplois/detail/a/",
        hash_html_id="a" * 64,
        content_type="text/html",
        fetched_at=NOW,
        http_status=200,
        scraper="jobup_extraction",
        scraper_version="0.1.0",
        payload_format=PayloadFormat.JSON_LD,
        payload=json.dumps([{"@type": "JobPosting", "title": "Job a"}]),  # a list
    )
    storage.append(Table.RAW_JOB_DETAIL, [unreadable, detail("b")])

    report: NormalizationReport = normalization(storage).execute()

    assert (report.normalized, report.failed, report.remaining) == (1, 1, 0)
    rows: list[dict[str, Any]] = storage.read(Table.NORMALIZED_JOB, "jobup")
    assert [row["hash_html_id"][0] for row in rows] == ["b"]
