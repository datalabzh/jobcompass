"""
test_extract_job_infos_step.py

Description : tests of the internal step that records the jobs of a category.
Rules       : every page is written; a 'completed' log ends a full run; a failing
              page keeps the pages already read and gives a 'failed' log, without
              raising.
"""

import json
from typing import Any

from conftest import NOW, FakeScraper

from contracts import JobInfoExtractionLog
from ingestion.storage.i_storage import Table
from ingestion.storage.local_parquet_storage import LocalParquetStorage
from ingestion.use_cases._steps.extract_job_infos_step import (
    ExtractJobInfosStep,
)

A: str = "https://site.test/a"
B: str = "https://site.test/b"
C: str = "https://site.test/c"


def run(scraper: FakeScraper, storage: LocalParquetStorage) -> JobInfoExtractionLog:
    """Run the step on category 'it' at a fixed time."""
    return ExtractJobInfosStep(scraper, storage, now=lambda: NOW).run("it")


def test_every_page_written_then_completed(storage: LocalParquetStorage) -> None:
    """All pages are written with their cards, then a 'completed' log."""
    log: JobInfoExtractionLog = run(FakeScraper({"it": [[A, B], [B, C]]}), storage)

    rows: list[dict[str, Any]] = storage.read(Table.JOB_INFO, "fake")
    assert len(rows) == 4 and {r["run_id"] for r in rows} == {log.run_id}
    assert json.loads(rows[0]["card"]) == {"url": A}
    assert (log.status, log.pages_read, log.jobs_seen, log.distinct_urls) == (
        "completed",
        2,
        4,
        3,
    )
    saved: list[dict[str, Any]] = storage.read(Table.JOB_INFO_EXTRACTION_LOG, "fake")
    assert saved[0]["status"] == "completed"


def test_failing_page_gives_failed_log(storage: LocalParquetStorage) -> None:
    """Page 3 blocked: pages 1-2 kept, a 'failed' log with the error, no raise."""
    scraper: FakeScraper = FakeScraper({"it": [[A], [B], [C]]}, blocked={("it", 3)})

    log: JobInfoExtractionLog = run(scraper, storage)

    assert len(storage.read(Table.JOB_INFO, "fake")) == 2
    assert (log.status, log.pages_read) == ("failed", 2)
    assert "HTTP 403" in str(log.error)


def test_each_run_has_its_own_id(storage: LocalParquetStorage) -> None:
    """Each run records its jobs again, under a new run_id."""
    first: JobInfoExtractionLog = run(FakeScraper({"it": [[A]]}), storage)
    second: JobInfoExtractionLog = run(FakeScraper({"it": [[A]]}), storage)

    assert first.run_id != second.run_id
    assert len(storage.read(Table.JOB_INFO, "fake")) == 2
