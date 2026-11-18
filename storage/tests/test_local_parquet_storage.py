"""
test_local_parquet_storage.py

Description : tests du stockage Parquet local.
Règles      : ce qui est ajouté est relu, par source ; les fichiers suivent
              l'organisation <table>/source=/date=/part-*.parquet ; un ajout ne
              mélange pas deux contrats ; le schéma Parquet est déduit du contrat
              (types attendus, X | None nullable, listes, dates et contrats dans
              une liste, type non prévu refusé) ; les
              fichiers bruts sont écrits en entier et retrouvés ; un stockage de
              test écrit sous test/ et ne voit pas les vraies données.
"""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contracts import (
    ContractModel,
    LogRawJobDetail,
    LogRawJobInfo,
    NormalizedJob,
    NormalizedSkill,
    PayloadFormat,
    RawJobDetail,
    RawJobInfo,
    RunStatus,
    SkillOrigin,
)
from storage import LocalParquetStorage

NOW: datetime = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)
A: str = "https://site.test/a"


def job_info(url: str = A, is_test: bool = False, **changes: Any) -> RawJobInfo:  # noqa: ANN401
    """A RawJobInfo of source 'fake', with some fields changed."""
    fields: dict[str, Any] = {
        "run_id": "r1",
        "source": "fake",
        "is_test": is_test,
        "url": url,
        "seen_at": NOW,
    }
    return RawJobInfo(**(fields | changes))


@pytest.fixture
def storage(tmp_path: Path) -> LocalParquetStorage:
    """A real storage writing into the test's temporary folder."""
    return LocalParquetStorage(is_test=False, data_dir=tmp_path)


def test_append_then_read(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """A record is written in a partitioned file and read back unchanged."""
    record: RawJobInfo = job_info(listing_params={"category": "x"}, card='{"a": 1}')
    storage.append("raw_job_info", [record])

    files: list[Path] = list(
        (tmp_path / "raw_job_info" / "source=fake").rglob("*.parquet")
    )
    assert len(files) == 1 and files[0].parent.name.startswith("date=")
    (row,) = storage.read("raw_job_info", "fake")
    assert (row["url"], row["card"], row["is_test"], row["seen_at"]) == (
        A,
        '{"a": 1}',
        False,
        NOW,
    )
    assert row["listing_params"] == [("category", "x")]


def test_read_other_source_or_empty(storage: LocalParquetStorage) -> None:
    """Nothing written for a source or a table reads as an empty list."""
    storage.append("raw_job_info", [job_info()])
    assert storage.read("raw_job_info", "other") == []
    assert storage.read("raw_job_detail", "fake") == []


def test_append_nothing(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """Appending no record writes no file."""
    storage.append("raw_job_info", [])
    assert not (tmp_path / "raw_job_info").exists()


def test_one_contract_per_append(storage: LocalParquetStorage) -> None:
    """Records of two different contracts cannot be appended together."""
    failure: LogRawJobDetail = LogRawJobDetail(
        source="fake", is_test=False, url=A, attempted_at=NOW, error="HTTP 404"
    )
    with pytest.raises(ValueError, match="one contract"):
        storage.append("raw_job_info", [job_info(), failure])


def test_raw_files(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """A raw file is stored under its name and found again."""
    assert not storage.has_file("raw_job_detail_html/h.html")
    storage.put_file("raw_job_detail_html/h.html", b"<html/>")
    assert storage.has_file("raw_job_detail_html/h.html")
    assert (tmp_path / "raw_job_detail_html" / "h.html").read_bytes() == b"<html/>"


def test_test_zone_is_apart(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """A test storage writes under test/; real and test data never mix."""
    test: LocalParquetStorage = LocalParquetStorage(is_test=True, data_dir=tmp_path)
    test.append("raw_job_info", [job_info(is_test=True)])
    test.put_file("raw_job_detail_html/h.html", b"<html/>")

    assert (tmp_path / "test" / "raw_job_info").exists()
    assert storage.read("raw_job_info", "fake") == []
    assert not storage.has_file("raw_job_detail_html/h.html")


def test_schema_deduced_from_contract(
    storage: LocalParquetStorage, tmp_path: Path
) -> None:
    """The written file has the types of the contract; only X | None is nullable."""
    log: LogRawJobInfo = LogRawJobInfo(
        run_id="r1",
        source="fake",
        is_test=False,
        listing_params={"category": "x"},
        started_at=NOW,
        finished_at=NOW,
        status=RunStatus.COMPLETED,
        announced_total=None,
        pages_read=1,
        jobs_seen=2,
        distinct_urls=2,
    )
    storage.append("log", [log])

    (file,) = (tmp_path / "log").rglob("*.parquet")
    schema: pa.Schema = pq.read_schema(file)
    assert schema.names == list(LogRawJobInfo.model_fields)
    assert schema.field("schema_version").type == pa.string()  # Literal
    assert schema.field("status").type == pa.string()  # enumeration
    assert schema.field("is_test").type == pa.bool_()
    assert schema.field("pages_read").type == pa.int64()
    assert schema.field("started_at").type == pa.timestamp("us", tz="UTC")
    assert schema.field("listing_params").type == pa.map_(pa.string(), pa.string())
    assert schema.field("announced_total").nullable
    assert not schema.field("pages_read").nullable


def test_every_contract_is_storable(storage: LocalParquetStorage) -> None:
    """A RawJobDetail (status code, hash, version) is written and read back."""
    detail: RawJobDetail = RawJobDetail(
        source="fake",
        is_test=False,
        url=A,
        raw_hash="0" * 64,
        content_type="text/html",
        fetched_at=NOW,
        http_status=200,
        scraper="fake_scraper",
        scraper_version="1.0.0",
        payload_format=PayloadFormat.JSON_LD,
        payload='{"@type": "JobPosting"}',
    )
    storage.append("raw_job_detail", [detail])
    assert storage.read("raw_job_detail", "fake")[0]["http_status"] == 200


def test_unknown_type_rejected(storage: LocalParquetStorage) -> None:
    """A field type with no Parquet equivalent raises TypeError."""

    class Odd(ContractModel):
        """A contract with a bytes field, not supported yet."""

        source: str
        values: bytes

    with pytest.raises(TypeError, match="no Parquet type"):
        storage.append("odd", [Odd(source="fake", values=b"1")])


def test_lists_dates_and_nested_contracts(storage: LocalParquetStorage) -> None:
    """Lists, dates and a list of contracts are written and read back."""

    class Item(ContractModel):
        """A small contract held in a list."""

        name: str
        origin: RunStatus

    class Holder(ContractModel):
        """A contract with a date, a list of texts and a list of contracts."""

        source: str
        day: date | None
        tags: list[str]
        items: list[Item]

    holder: Holder = Holder(
        source="fake",
        day=date(2026, 11, 17),
        tags=["a", "b"],
        items=[Item(name="x", origin=RunStatus.COMPLETED)],
    )
    storage.append("holder", [holder])

    (row,) = storage.read("holder", "fake")
    assert row["day"] == date(2026, 11, 17)
    assert row["tags"] == ["a", "b"]
    assert row["items"] == [{"name": "x", "origin": "completed"}]


def test_normalization_contract_storable(storage: LocalParquetStorage) -> None:
    """A NormalizedJob is written and read back."""
    normalized: NormalizedJob = NormalizedJob(
        source="fake",
        is_test=False,
        url=A,
        raw_hash="0" * 64,
        parser_version="1.0.0",
        normalizer="fake_normalization",
        normalizer_version="0.1.0",
        model="keyword_list",
        model_version="0.1.0",
        normalizer_description="Keywords found in the text.",
        normalized_at=NOW,
        skills=[
            NormalizedSkill(
                raw="Python", canonical="python", origin=SkillOrigin.DETECTED
            )
        ],
    )
    storage.append("normalized_job", [normalized])

    assert storage.read("normalized_job", "fake")[0]["skills"] == [
        {"raw": "Python", "canonical": "python", "origin": "detected"}
    ]
