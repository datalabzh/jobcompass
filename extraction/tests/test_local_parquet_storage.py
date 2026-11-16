"""
test_local_parquet_storage.py

Description : tests du stockage Parquet local.
Règles      : ce qui est ajouté est relu, par source ; les fichiers suivent
              l'organisation <table>/source=/date=/part-*.parquet ; les fichiers
              bruts sont écrits en entier et retrouvés ; un stockage de test écrit
              sous test/ et ne voit pas les vraies données.
"""

from pathlib import Path
from typing import Any

from conftest import NOW, save_seen

from contracts import JobInfo
from extraction.interfaces.i_storage import Table
from extraction.storage.local_parquet_storage import LocalParquetStorage

A: str = "https://site.test/a"


def test_append_then_read(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """A record is written in a partitioned file and read back unchanged."""
    record: JobInfo = JobInfo(
        run_id="r1",
        source="fake",
        is_test=False,
        url=A,
        seen_at=NOW,
        listing_params={"category": "x"},
        card='{"a": 1}',
    )
    storage.append(Table.JOB_INFO, [record])

    files: list[Path] = list((tmp_path / "job_info" / "source=fake").rglob("*.parquet"))
    assert len(files) == 1 and files[0].parent.name.startswith("date=")
    rows: list[dict[str, Any]] = storage.read(Table.JOB_INFO, "fake")
    assert (rows[0]["url"], rows[0]["card"], rows[0]["is_test"]) == (
        A,
        '{"a": 1}',
        False,
    )
    assert rows[0]["listing_params"] == [("category", "x")]


def test_read_other_source_or_empty(storage: LocalParquetStorage) -> None:
    """Nothing written for a source reads as an empty list."""
    save_seen(storage, A)
    assert storage.read(Table.JOB_INFO, "other") == []
    assert storage.read(Table.JOB_DETAIL, "fake") == []


def test_append_nothing(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """Appending no record writes no file."""
    storage.append(Table.JOB_INFO, [])
    assert not (tmp_path / "job_info").exists()


def test_raw_files(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """A raw file is stored under its name and found again."""
    assert not storage.has_file("job_detail_html/h.html")
    storage.put_file("job_detail_html/h.html", b"<html/>")
    assert storage.has_file("job_detail_html/h.html")
    assert (tmp_path / "job_detail_html" / "h.html").read_bytes() == b"<html/>"


def test_test_zone_is_apart(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """A test storage writes under test/; real and test data never mix."""
    test: LocalParquetStorage = LocalParquetStorage(is_test=True, data_dir=tmp_path)
    save_seen(test, A)
    test.put_file("job_detail_html/h.html", b"<html/>")

    assert (tmp_path / "test" / "job_info").exists()
    assert storage.read(Table.JOB_INFO, "fake") == []
    assert not storage.has_file("job_detail_html/h.html")
