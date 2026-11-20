"""
test_jobup_extraction_uc.py

Description : tests de l'extraction complète de jobup.ch.
Règles      : vrais stockages (zone de test de Postgres et de RustFS, vidée avant
              chaque test), réseau simulé par des pages de résultats construites
              pour le test. Couvre : chaque page écrite et
              journalisée, la limite max_pages, une catégorie en échec qui n'arrête
              pas les autres, la limite max_jobs, le HTML stocké sous son hash avec
              son reçu, les échecs journalisés puis mis de côté, la reprise (rien de
              retéléchargé), la zone de test, les options refusées, le bloc brut
              enregistré avec chaque page (JSON-LD, ou à défaut les paragraphes) et
              signé par le scraper, un plantage qui garde tout ce qui a été écrit
              avant lui.
"""

import json
from typing import Any

import pytest
from conftest import FakeGetPage, Storages, fixed_now, page
from pydantic import ValidationError

from catalog.tables import Table
from contracts.components.field_types import PayloadFormat, RunStatus
from extraction.interfaces.i_get_page import Page
from extraction.interfaces.i_site_extraction_uc import ExtractionReport
from extraction.jobup.jobup_extraction_uc import JobupExtractionUseCase
from storage.postgres_db_storage import PostgresDbStorage
from storage.s3_file_storage import S3FileStorage

LISTING: str = "https://www.jobup.ch/fr/emplois/{category}/?page={page}"
DETAIL: str = "https://www.jobup.ch/fr/emplois/detail/{id}/"


def listing_page(ids: list[str], num_pages: int) -> Page:
    """A jobup result page with these job ids, in its __INIT__ JSON."""
    init: dict[str, Any] = {
        "vacancy": {
            "results": {
                "main": {
                    "meta": {"numPages": num_pages, "totalHits": 99},
                    "results": [{"id": job_id, "title": job_id} for job_id in ids],
                }
            }
        }
    }
    return page(content=f"<script>__INIT__ = {json.dumps(init)};</script>".encode())


def detail_page(job_id: str) -> Page:
    """A jobup detail page with a minimal JSON-LD JobPosting."""
    posting: str = json.dumps({"@type": "JobPosting", "title": job_id})
    return page(
        content=f'<script type="application/ld+json">{posting}</script>'.encode()
    )


def site(pages_by_category: dict[str, list[list[str]]]) -> dict[str, Page]:
    """Result pages per category (a list of job ids per page) and detail pages."""
    pages: dict[str, Page] = {}
    for category, pages_ids in pages_by_category.items():
        for number, ids in enumerate(pages_ids, start=1):
            url: str = LISTING.format(category=category, page=number)
            pages[url] = listing_page(ids, len(pages_ids))
            for job_id in ids:
                pages[DETAIL.format(id=job_id)] = detail_page(job_id)
    return pages


def extraction(
    storages: Storages,
    get_page: FakeGetPage,
    categories: list[str],
    max_pages: int | None = None,
    max_jobs: int | None = None,
) -> JobupExtractionUseCase:
    """A jobup extraction on the fake network."""
    return JobupExtractionUseCase(
        source="jobup",
        get_page=get_page,
        db_storage=storages.db,
        file_storage=storages.files,
        is_test=storages.db.is_test,
        max_pages=max_pages,
        max_jobs=max_jobs,
        max_failures=2,
        now=fixed_now,
        options={"categories": categories},
    )


def test_pages_written_and_logged(storages: Storages) -> None:
    """Every page is written; the category log is completed with its counts."""
    get_page: FakeGetPage = FakeGetPage(site({"it": [["a", "b"], ["c"]]}))

    report: ExtractionReport = extraction(
        storages, get_page, ["it"], max_jobs=0
    ).execute()

    assert report.status == RunStatus.COMPLETED
    assert len(storages.db.read(Table.RAW_JOB_INFO, "jobup")) == 3
    (log,) = storages.db.read(Table.LOG_RAW_JOB_INFO, "jobup")
    assert (log["status"], log["pages_read"], log["distinct_urls"]) == (
        "completed",
        2,
        3,
    )


def test_max_pages_stops_reading(storages: Storages) -> None:
    """With max_pages=1 the second result page is never requested."""
    get_page: FakeGetPage = FakeGetPage(site({"it": [["a", "b"], ["c"]]}))

    extraction(storages, get_page, ["it"], max_pages=1, max_jobs=0).execute()

    assert LISTING.format(category="it", page=2) not in get_page.requested
    assert len(storages.db.read(Table.RAW_JOB_INFO, "jobup")) == 2


def test_failed_category_does_not_stop_others(storages: Storages) -> None:
    """A blocked category is logged as failed; the next one is still read."""
    pages: dict[str, Page] = site({"it": [["a"], ["b"]], "finance": [["c"]]})
    pages[LISTING.format(category="it", page=2)] = page(status=403)

    report: ExtractionReport = extraction(
        storages, FakeGetPage(pages), ["it", "finance"], max_jobs=0
    ).execute()

    assert report.status == RunStatus.FAILED
    assert [log.status for log in report.listings] == [
        RunStatus.FAILED,
        RunStatus.COMPLETED,
    ]
    assert "HTTP 403" in (report.listings[0].error or "")
    assert len(storages.db.read(Table.RAW_JOB_INFO, "jobup")) == 2  # a, then c


def test_details_limited_and_stored(storages: Storages) -> None:
    """max_jobs limits the downloads; each page is stored with its receipt."""
    get_page: FakeGetPage = FakeGetPage(site({"it": [["a", "b", "c"]]}))

    report: ExtractionReport = extraction(
        storages, get_page, ["it"], max_jobs=2
    ).execute()

    assert report.details.extracted == 2
    receipts: list[dict[str, Any]] = storages.db.read(Table.RAW_JOB_DETAIL, "jobup")
    assert [r["url"] for r in receipts] == [
        DETAIL.format(id="a"),
        DETAIL.format(id="b"),
    ]
    assert all(
        storages.files.has_file(f"{Table.RAW_JOB_DETAIL_HTML}/{r['raw_hash']}.html")
        for r in receipts
    )


def test_nothing_downloaded_twice(storages: Storages) -> None:
    """A second run only downloads what is still to extract."""
    pages: dict[str, Page] = site({"it": [["a", "b"]]})
    extraction(storages, FakeGetPage(pages), ["it"], max_jobs=1).execute()
    get_page: FakeGetPage = FakeGetPage(pages)

    extraction(storages, get_page, ["it"]).execute()

    assert [url for url in get_page.requested if "detail" in url] == [
        DETAIL.format(id="b")
    ]


def test_failures_logged_then_set_aside(storages: Storages) -> None:
    """A failing job is logged each time, then set aside after max_failures."""
    pages: dict[str, Page] = site({"it": [["a"]]})
    pages[DETAIL.format(id="a")] = page(status=404)
    for _ in range(2):
        extraction(storages, FakeGetPage(pages), ["it"]).execute()

    report: ExtractionReport = extraction(
        storages, FakeGetPage(pages), ["it"]
    ).execute()

    failures: list[dict[str, Any]] = storages.db.read(Table.LOG_RAW_JOB_DETAIL, "jobup")
    assert [f["error"] for f in failures] == ["HTTP 404", "HTTP 404"]
    assert (report.details.failed, report.details.set_aside) == (0, 1)


def test_test_run_writes_apart(storages: Storages) -> None:
    """A test run writes its records, flagged is_test, in the test zone only."""
    extraction(storages, FakeGetPage(site({"it": [["a"]]})), ["it"]).execute()

    (detail,) = storages.db.read(Table.RAW_JOB_DETAIL, "jobup")
    assert detail["is_test"]
    (info,) = storages.db.read(Table.RAW_JOB_INFO, "jobup", columns=["run_id"])
    real_runs: set[str] = {
        row["run_id"]
        for row in PostgresDbStorage(is_test=False).read(
            Table.RAW_JOB_INFO, "jobup", columns=["run_id"]
        )
    }
    assert info["run_id"] not in real_runs
    html: str = f"{Table.RAW_JOB_DETAIL_HTML}/{detail['raw_hash']}.html"
    assert not S3FileStorage(is_test=False).has_file(html)


def test_wrong_options_refused(storages: Storages) -> None:
    """Options without category are refused before any request."""
    get_page: FakeGetPage = FakeGetPage({})
    with pytest.raises(ValidationError):
        extraction(storages, get_page, []).execute()
    assert get_page.requested == []


def test_payload_stored_and_signed(storages: Storages) -> None:
    """Each page is stored with its JSON-LD block and the scraper that read it."""
    extraction(storages, FakeGetPage(site({"it": [["a", "b"]]})), ["it"]).execute()

    receipts: list[dict[str, Any]] = storages.db.read(Table.RAW_JOB_DETAIL, "jobup")
    assert sorted(r["payload"]["title"] for r in receipts) == ["a", "b"]
    assert {
        (r["payload_format"], r["scraper"], r["scraper_version"]) for r in receipts
    } == {("json_ld", "jobup_extraction", JobupExtractionUseCase.version)}


def test_paragraphs_without_json_ld(storages: Storages) -> None:
    """A page without JSON-LD is stored with its paragraphs: nothing is lost."""
    pages: dict[str, Page] = site({"it": [["a"]]})
    pages[DETAIL.format(id="a")] = page(content=b"<html><p>Data Engineer</p></html>")

    report: ExtractionReport = extraction(
        storages, FakeGetPage(pages), ["it"]
    ).execute()

    assert report.details.extracted == 1
    (receipt,) = storages.db.read(Table.RAW_JOB_DETAIL, "jobup")
    assert receipt["payload_format"] == PayloadFormat.PARAGRAPHS
    assert receipt["payload"] == ["Data Engineer"]


class CrashingGetPage(FakeGetPage):
    """A network that crashes the run (not a mere failure) on one URL."""

    def __init__(self, pages: dict[str, Page], crash_on: str) -> None:
        super().__init__(pages)
        self.crash_on: str = crash_on

    def __call__(self, url: str) -> Page:
        """Crash on the chosen URL, answer normally otherwise."""
        if url == self.crash_on:
            raise RuntimeError("crash")
        return super().__call__(url)


def test_crash_keeps_what_was_written(storages: Storages) -> None:
    """Jobs are written one by one: a crash on the 3rd keeps the first two."""
    pages: dict[str, Page] = site({"it": [["a", "b", "c", "d"]]})
    crashing: CrashingGetPage = CrashingGetPage(pages, DETAIL.format(id="c"))
    with pytest.raises(RuntimeError):
        extraction(storages, crashing, ["it"]).execute()

    get_page: FakeGetPage = FakeGetPage(pages)
    extraction(storages, get_page, ["it"]).execute()

    assert [url for url in get_page.requested if "detail" in url] == [
        DETAIL.format(id="c"),
        DETAIL.format(id="d"),
    ]
    receipts: list[dict[str, Any]] = storages.db.read(Table.RAW_JOB_DETAIL, "jobup")
    assert sorted(r["payload"]["title"] for r in receipts) == [
        "a",
        "b",
        "c",
        "d",
    ]
