"""
test_extract_job_details.py

Description : tests of the ExtractJobDetails use case.
Rules       : execute records the jobs of every category, then downloads their
              detail pages; a failing category is reported and does not stop the
              other categories nor the downloads.
"""

from conftest import NOW, FakeScraper

from ingestion.storage.i_storage import Table
from ingestion.storage.local_parquet_storage import LocalParquetStorage
from ingestion.use_cases.extract_job_details import (
    ExtractJobDetails,
    ExtractJobDetailsReport,
)

A: str = "https://site.test/a"
B: str = "https://site.test/b"
C: str = "https://site.test/c"


def execute(
    scraper: FakeScraper, storage: LocalParquetStorage
) -> ExtractJobDetailsReport:
    """Run the use case at a fixed time."""
    return ExtractJobDetails(scraper, storage, now=lambda: NOW).execute()


def test_all_categories_then_details(storage: LocalParquetStorage) -> None:
    """Jobs of both categories are recorded, then all their pages downloaded."""
    scraper: FakeScraper = FakeScraper(
        {"it": [[A]], "finance": [[B]]}, details={A: b"a", B: b"b"}
    )

    report: ExtractJobDetailsReport = execute(scraper, storage)

    assert report.status == "completed"
    assert [log.listing_params["category"] for log in report.categories] == [
        "it",
        "finance",
    ]
    assert report.details.extracted == 2
    assert len(storage.read(Table.JOB_DETAIL, "fake")) == 2


def test_failing_category_reported_others_continue(
    storage: LocalParquetStorage,
) -> None:
    """'it' blocked: 'finance' is still recorded and its pages downloaded."""
    scraper: FakeScraper = FakeScraper(
        {"it": [[A]], "finance": [[B, C]]},
        details={B: b"b", C: b"c"},
        blocked={("it", 1)},
    )

    report: ExtractJobDetailsReport = execute(scraper, storage)

    assert report.status == "failed"
    assert [log.status for log in report.categories] == ["failed", "completed"]
    assert report.details.extracted == 2
