"""
test_local_parquet_storage.py

Description : tests of the local Parquet storage.
Rules       : what is appended is read back, per source; files follow the
              <table>/source=/date=/part-*.parquet layout; raw files are written
              whole and found again.
"""

from pathlib import Path
from typing import Any

from conftest import job_info

from contracts import JobInfo
from ingestion.storage.i_storage import Table
from ingestion.storage.local_parquet_storage import LocalParquetStorage

A: str = "https://site.test/a"


def test_append_then_read(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """A record is written in a partitioned file and read back unchanged."""
    record: JobInfo = job_info(A)[0].model_copy(
        update={"listing_params": {"category": "x"}, "card": '{"a": 1}'}
    )
    storage.append(Table.JOB_INFO, [record])

    files: list[Path] = list((tmp_path / "job_info" / "source=fake").rglob("*.parquet"))
    assert len(files) == 1 and files[0].parent.name.startswith("date=")
    rows: list[dict[str, Any]] = storage.read(Table.JOB_INFO, "fake")
    assert (rows[0]["url"], rows[0]["card"]) == (A, '{"a": 1}')
    assert rows[0]["listing_params"] == [("category", "x")]


def test_read_other_source_or_empty(storage: LocalParquetStorage) -> None:
    """Nothing written for a source reads as an empty list."""
    storage.append(Table.JOB_INFO, job_info(A))
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
