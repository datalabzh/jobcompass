"""
test_postgres_db_storage.py

Description : tests du stockage des tables dans PostgreSQL, contre le vrai
              conteneur (docker compose -f infra/docker-compose.yml up -d --wait).
Règles      : tous les tests écrivent dans la zone de test (raw_test), vidée avant
              chacun ; aucun n'écrit dans raw.
              Couvre : ce qui est ajouté est relu, par source, toutes les colonnes ou
              seulement celles demandées ; un bloc JSON revient en dict ; une ligne
              réécrite ne crée pas de doublon ; un ajout ne mélange pas deux
              contrats ; chaque contrat de l'extraction est stockable ; la zone de
              test est à part ; clear_test_zone est refusé pour un stockage réel.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest

from contracts.components.field_types import PayloadFormat, RunStatus
from contracts.jobs.log_raw_job_detail import LogRawJobDetail
from contracts.jobs.log_raw_job_info import LogRawJobInfo
from contracts.jobs.raw_job_detail import RawJobDetail
from contracts.jobs.raw_job_info import RawJobInfo
from storage.postgres_db_storage import PostgresDbStorage

NOW: datetime = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)
A: str = "https://site.test/a"


def job_info(run_id: str = "r1", **changes: Any) -> RawJobInfo:  # noqa: ANN401
    """A test RawJobInfo of source 'fake', with some fields changed."""
    fields: dict[str, Any] = {
        "run_id": run_id,
        "source": "fake",
        "is_test": True,
        "url": A,
        "seen_at": NOW,
    }
    return RawJobInfo(**(fields | changes))


@pytest.fixture
def storage() -> Iterator[PostgresDbStorage]:
    """The test zone of the real Postgres, emptied before the test."""
    test: PostgresDbStorage = PostgresDbStorage(is_test=True)
    test.clear_test_zone()
    yield test


def test_append_then_read(storage: PostgresDbStorage) -> None:
    """A record is written and read back; its JSON blocks come back as dicts."""
    storage.append(
        "raw_job_info",
        [job_info(listing_params={"category": "x"}, card='{"a": 1}')],
    )

    (row,) = storage.read("raw_job_info", "fake")
    assert (row["url"], row["is_test"], row["seen_at"]) == (A, True, NOW)
    assert row["listing_params"] == {"category": "x"}
    assert row["card"] == {"a": 1}


def test_read_other_source_or_empty(storage: PostgresDbStorage) -> None:
    """Nothing written for a source or in a table reads as an empty list."""
    storage.append("raw_job_info", [job_info()])
    assert storage.read("raw_job_info", "other") == []
    assert storage.read("raw_job_detail", "fake") == []


def test_read_given_columns(storage: PostgresDbStorage) -> None:
    """Only the columns asked for are read."""
    storage.append("raw_job_info", [job_info()])
    assert storage.read("raw_job_info", "fake", columns=["url", "seen_at"]) == [
        {"url": A, "seen_at": NOW}
    ]


def test_append_nothing(storage: PostgresDbStorage) -> None:
    """Appending no record writes nothing."""
    storage.append("raw_job_info", [])
    assert storage.read("raw_job_info", "fake") == []


def test_same_line_written_once(storage: PostgresDbStorage) -> None:
    """A line written again (same unique key) is not duplicated."""
    storage.append("raw_job_info", [job_info()])
    storage.append("raw_job_info", [job_info()])
    assert len(storage.read("raw_job_info", "fake")) == 1


def test_one_contract_per_append(storage: PostgresDbStorage) -> None:
    """Records of two different contracts cannot be appended together."""
    failure: LogRawJobDetail = LogRawJobDetail(
        source="fake", is_test=True, url=A, attempted_at=NOW, error="HTTP 404"
    )
    with pytest.raises(ValueError, match="one contract"):
        storage.append("raw_job_info", [job_info(), failure])


def test_every_extraction_contract_is_storable(storage: PostgresDbStorage) -> None:
    """The logs and a RawJobDetail are written and read back."""
    storage.append(
        "log_raw_job_info",
        [
            LogRawJobInfo(
                run_id="r1",
                source="fake",
                is_test=True,
                listing_params={"category": "x"},
                started_at=NOW,
                finished_at=NOW,
                status=RunStatus.COMPLETED,
                announced_total=None,
                pages_read=1,
                jobs_seen=2,
                distinct_urls=2,
            )
        ],
    )
    storage.append(
        "log_raw_job_detail",
        [
            LogRawJobDetail(
                source="fake", is_test=True, url=A, attempted_at=NOW, error="HTTP 404"
            )
        ],
    )
    storage.append(
        "raw_job_detail",
        [
            RawJobDetail(
                source="fake",
                is_test=True,
                url=A,
                hash_html_id="0" * 64,
                content_type="text/html",
                fetched_at=NOW,
                http_status=200,
                scraper="fake_scraper",
                scraper_version="1.0.0",
                payload_format=PayloadFormat.JSON_LD,
                payload='{"@type": "JobPosting"}',
            )
        ],
    )

    (log,) = storage.read("log_raw_job_info", "fake")
    assert (log["status"], log["announced_total"]) == ("completed", None)
    assert storage.read("log_raw_job_detail", "fake")[0]["error"] == "HTTP 404"
    (detail,) = storage.read("raw_job_detail", "fake")
    assert (detail["payload_format"], detail["payload"]) == (
        "json_ld",
        {"@type": "JobPosting"},
    )


def test_test_zone_is_apart(storage: PostgresDbStorage) -> None:
    """What a test storage writes is not seen by a real storage."""
    run_id: str = f"test-{uuid.uuid4()}"
    storage.append("raw_job_info", [job_info(run_id=run_id)])

    real: PostgresDbStorage = PostgresDbStorage(is_test=False)
    real_runs: set[str] = {
        row["run_id"] for row in real.read("raw_job_info", "fake", columns=["run_id"])
    }
    assert run_id not in real_runs


def test_clear_refused_for_real_storage() -> None:
    """clear_test_zone never empties the real tables."""
    with pytest.raises(RuntimeError, match="test zone"):
        PostgresDbStorage(is_test=False).clear_test_zone()
