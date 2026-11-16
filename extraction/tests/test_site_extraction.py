"""
test_site_extraction.py

Description : tests du cas d'utilisation SiteExtraction (job infos puis job
              details).
Règles      : vrai stockage dans un dossier temporaire, faux site. Couvre : chaque
              page écrite et journalisée, la limite max_pages, une catégorie en
              échec qui n'arrête pas les autres, la limite max_jobs, le HTML stocké
              sous son hash avec son reçu, les échecs journalisés et la mise de
              côté, la reprise (rien de retéléchargé), l'arrêt sur violation de
              contrat.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import FakeJobDetails, FakeJobInfos, fixed_now, save_seen

from contracts import JobDetailExtractionLog, RunStatus
from extraction.contract_checks import ContractViolationError
from extraction.interfaces.i_job_infos_extractor import JobInfoPage
from extraction.interfaces.i_storage import IStorage, Table
from extraction.site_extraction import ExtractionReport, SiteExtraction
from extraction.storage.local_parquet_storage import LocalParquetStorage

A: str = "https://fake.ch/a"
B: str = "https://fake.ch/b"
C: str = "https://fake.ch/c"


def extraction(
    storage: IStorage,
    job_infos: FakeJobInfos | None = None,
    job_details: FakeJobDetails | None = None,
    max_pages: int | None = None,
    max_jobs: int | None = None,
) -> SiteExtraction:
    """A SiteExtraction of the fake site; no category and no page by default."""
    infos: FakeJobInfos = job_infos or FakeJobInfos({})
    return SiteExtraction(
        source="fake",
        job_infos=infos,
        job_details=job_details or FakeJobDetails({}),
        storage=storage,
        categories=list(infos.listings),
        max_pages=max_pages,
        max_jobs=max_jobs,
        max_failures=2,
        batch_size=2,
        now=fixed_now,
    )


def test_pages_written_and_logged(storage: LocalParquetStorage) -> None:
    """Every page is written; the category log is completed with its counts."""
    infos: FakeJobInfos = FakeJobInfos({"it": [[A, B], [C]]})

    report: ExtractionReport = extraction(storage, job_infos=infos).execute()

    assert report.status == RunStatus.COMPLETED
    assert len(storage.read(Table.JOB_INFO, "fake")) == 3
    (log,) = storage.read(Table.JOB_INFO_EXTRACTION_LOG, "fake")
    assert (log["status"], log["pages_read"], log["distinct_urls"]) == (
        "completed",
        2,
        3,
    )


def test_max_pages_stops_reading(storage: LocalParquetStorage) -> None:
    """With max_pages=1 the second page is never asked to the site."""
    infos: FakeJobInfos = FakeJobInfos({"it": [[A, B], [C]]})

    extraction(storage, job_infos=infos, max_pages=1).execute()

    assert infos.pages_produced == 1
    assert len(storage.read(Table.JOB_INFO, "fake")) == 2


def test_failed_category_does_not_stop_others(storage: LocalParquetStorage) -> None:
    """A blocked category is logged as failed; the next one is still read."""
    infos: FakeJobInfos = FakeJobInfos(
        {"it": [[A], [B]], "finance": [[C]]}, blocked={("it", 2)}
    )

    report: ExtractionReport = extraction(storage, job_infos=infos).execute()

    assert report.status == RunStatus.FAILED
    statuses: list[RunStatus] = [log.status for log in report.categories]
    assert statuses == [RunStatus.FAILED, RunStatus.COMPLETED]
    assert "HTTP 403" in (report.categories[0].error or "")
    assert len(storage.read(Table.JOB_INFO, "fake")) == 2  # A, then C


def test_details_limited_and_stored(storage: LocalParquetStorage) -> None:
    """max_jobs limits the downloads; each page is stored with its receipt."""
    save_seen(storage, A, B, C)
    details: FakeJobDetails = FakeJobDetails({A: b"<a>", B: b"<b>", C: b"<c>"})

    report: ExtractionReport = extraction(
        storage, job_details=details, max_jobs=2
    ).execute()

    assert report.details.extracted == 2
    receipts: list[dict[str, object]] = storage.read(Table.JOB_DETAIL, "fake")
    assert [r["url"] for r in receipts] == [A, B]
    assert all(
        storage.has_file(f"job_detail_html/{r['raw_hash']}.html") for r in receipts
    )


def test_nothing_downloaded_twice(storage: LocalParquetStorage) -> None:
    """A second run only downloads what is still to extract."""
    save_seen(storage, A, B)
    extraction(storage, job_details=FakeJobDetails({A: b"<a>"}), max_jobs=1).execute()
    details: FakeJobDetails = FakeJobDetails({A: b"<a>", B: b"<b>"})

    extraction(storage, job_details=details).execute()

    assert details.fake_get_page.requested == [B]


def test_failures_logged_then_set_aside(storage: LocalParquetStorage) -> None:
    """A failing job is logged each time, then set aside after max_failures."""
    save_seen(storage, A)
    for _ in range(2):
        extraction(storage).execute()  # A answers 404

    report: ExtractionReport = extraction(storage).execute()

    assert len(storage.read(Table.JOB_DETAIL_EXTRACTION_LOG, "fake")) == 2
    assert (report.details.failed, report.details.set_aside) == (0, 1)


def test_test_run_writes_apart(tmp_path: Path) -> None:
    """A test run writes its records, flagged is_test, in the test zone only."""
    real: LocalParquetStorage = LocalParquetStorage(False, tmp_path)
    test: LocalParquetStorage = LocalParquetStorage(True, tmp_path)
    infos: FakeJobInfos = FakeJobInfos({"it": [[A]]}, is_test=True)

    extraction(test, job_infos=infos, job_details=FakeJobDetails({}, True)).execute()

    assert real.read(Table.JOB_INFO, "fake") == []
    assert [r["is_test"] for r in test.read(Table.JOB_INFO, "fake")] == [True]


def test_contract_violation_stops_the_run(storage: LocalParquetStorage) -> None:
    """A site returning something else than its contract stops everything."""

    class Broken(FakeJobInfos):
        """Yields a dict instead of a JobInfoPage."""

        def execute(self, category: str, run_id: str) -> Iterator[JobInfoPage]:
            """Yield a wrong object."""
            yield {"url": A}  # type: ignore[misc]

    with pytest.raises(ContractViolationError):
        extraction(storage, job_infos=Broken({"it": [[A]]})).execute()
    assert storage.read(Table.JOB_INFO, "fake") == []


def test_wrong_is_test_flag_rejected(storage: LocalParquetStorage) -> None:
    """Records flagged as test in a real run are refused, not written."""
    save_seen(storage, A)
    details: FakeJobDetails = FakeJobDetails({A: b"<a>"}, is_test=True)

    with pytest.raises(ContractViolationError, match="is_test"):
        extraction(storage, job_details=details).execute()
    assert storage.read(Table.JOB_DETAIL, "fake") == []


def test_failure_log_type(storage: LocalParquetStorage) -> None:
    """A failure is stored as a JobDetailExtractionLog row with its reason."""
    save_seen(storage, A)
    extraction(storage).execute()
    (row,) = storage.read(Table.JOB_DETAIL_EXTRACTION_LOG, "fake")
    assert row["error"] == "HTTP 404"
    assert set(JobDetailExtractionLog.model_fields) == set(row)
