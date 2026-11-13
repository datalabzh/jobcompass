"""
test_extract_job_details_step.py

Description : tests of the internal step that downloads the pending detail pages.
Rules       : covers success, failures that do not stop the others, set aside jobs,
              idempotence, same page stored once, limit and batches.
"""

from datetime import timedelta
from pathlib import Path

from conftest import NOW, FakeScraper, save_seen

from contracts import JobDetailExtractionLog, compute_raw_hash
from ingestion.storage.i_storage import Table
from ingestion.storage.local_parquet_storage import LocalParquetStorage
from ingestion.use_cases._steps.extract_job_details_step import (
    DetailsSummary,
    ExtractJobDetailsStep,
)

A: str = "https://site.test/a"
B: str = "https://site.test/b"
C: str = "https://site.test/c"


def run(
    scraper: FakeScraper,
    storage: LocalParquetStorage,
    limit: int | None = None,
    batch_size: int = 50,
) -> DetailsSummary:
    """Run the step with 3 allowed failures, at a fixed time."""
    step: ExtractJobDetailsStep = ExtractJobDetailsStep(
        scraper, storage, 3, batch_size, limit, now=lambda: NOW
    )
    return step.run()


def test_success_stores_page_and_detail(
    storage: LocalParquetStorage, tmp_path: Path
) -> None:
    """A downloaded page is stored by hash and described in job_detail."""
    save_seen(storage, A)

    summary: DetailsSummary = run(FakeScraper({}, details={A: b"<p>a</p>"}), storage)

    assert summary.extracted == 1
    detail: dict[str, object] = storage.read(Table.JOB_DETAIL, "fake")[0]
    assert (detail["url"], detail["scraper_version"]) == (A, "9.9.9")
    raw_hash: str = compute_raw_hash(b"<p>a</p>")
    assert (tmp_path / "job_detail_html" / f"{raw_hash}.html").exists()


def test_failures_logged_without_stopping_others(storage: LocalParquetStorage) -> None:
    """A failing job is logged with its reason; the others are still extracted."""
    save_seen(storage, A, B)

    summary: DetailsSummary = run(FakeScraper({}, details={B: b"b"}), storage)

    assert (summary.extracted, summary.failed) == (1, 1)
    log: dict[str, object] = storage.read(Table.JOB_DETAIL_EXTRACTION_LOG, "fake")[0]
    assert (log["url"], log["error"]) == (A, "HTTP 404")


def test_set_aside_job_not_requested(storage: LocalParquetStorage) -> None:
    """A job with 3 failures is set aside and not requested again."""
    save_seen(storage, A, B)
    failure: JobDetailExtractionLog = JobDetailExtractionLog(
        source="fake", url=A, attempted_at=NOW, error="HTTP 500"
    )
    storage.append(Table.JOB_DETAIL_EXTRACTION_LOG, [failure] * 3)
    scraper: FakeScraper = FakeScraper({}, details={A: b"a", B: b"b"})

    summary: DetailsSummary = run(scraper, storage)

    assert summary.set_aside == 1
    assert scraper.requested == [B]


def test_second_run_extracts_nothing(storage: LocalParquetStorage) -> None:
    """Running again does not request what was already extracted."""
    save_seen(storage, A)
    scraper: FakeScraper = FakeScraper({}, details={A: b"a"})

    run(scraper, storage)
    summary: DetailsSummary = run(scraper, storage)

    assert summary.extracted == 0
    assert scraper.requested == [A]


def test_same_page_stored_once(storage: LocalParquetStorage, tmp_path: Path) -> None:
    """Two jobs with the same content share one page file."""
    save_seen(storage, A, B)

    run(FakeScraper({}, details={A: b"same", B: b"same"}), storage)

    assert len(storage.read(Table.JOB_DETAIL, "fake")) == 2
    assert len(list((tmp_path / "job_detail_html").iterdir())) == 1


def test_limit_batches_and_order(storage: LocalParquetStorage) -> None:
    """Seen once each, first sighting first; limit caps the number of jobs."""
    save_seen(storage, C, at=NOW + timedelta(hours=1))
    save_seen(storage, A, B, A, at=NOW)
    scraper: FakeScraper = FakeScraper({}, details={A: b"a", B: b"b", C: b"c"})

    summary: DetailsSummary = run(scraper, storage, limit=2, batch_size=1)

    assert summary.extracted == 2
    assert scraper.requested == [A, B]
