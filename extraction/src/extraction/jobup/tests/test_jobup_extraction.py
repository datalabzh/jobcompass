"""
test_jobup_extraction.py

Description : tests de l'extraction complète de jobup.ch.
Règles      : vrai stockage dans un dossier temporaire, réseau simulé par des pages
              de résultats construites pour le test. Couvre : chaque page écrite et
              journalisée, la limite max_pages, une catégorie en échec qui n'arrête
              pas les autres, la limite max_jobs, le HTML stocké sous son hash avec
              son reçu, les échecs journalisés puis mis de côté, la reprise (rien de
              retéléchargé), la zone de test, les options refusées, le bloc brut
              enregistré avec chaque page (JSON-LD, ou à défaut les paragraphes) et
              signé par le scraper, un plantage qui garde tout ce qui a été écrit
              avant lui.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import FakeGetPage, fixed_now, page
from pydantic import ValidationError

from catalog import Table
from contracts import PayloadFormat, RunStatus
from extraction.jobup.jobup_extraction import JobupExtraction
from interfaces import ExtractionReport, Page
from storage import LocalParquetStorage

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
    storage: LocalParquetStorage,
    get_page: FakeGetPage,
    categories: list[str],
    max_pages: int | None = None,
    max_jobs: int | None = None,
) -> JobupExtraction:
    """A jobup extraction on the fake network."""
    return JobupExtraction(
        source="jobup",
        get_page=get_page,
        storage=storage,
        is_test=storage.is_test,
        max_pages=max_pages,
        max_jobs=max_jobs,
        max_failures=2,
        now=fixed_now,
        options={"categories": categories},
    )


def test_pages_written_and_logged(storage: LocalParquetStorage) -> None:
    """Every page is written; the category log is completed with its counts."""
    get_page: FakeGetPage = FakeGetPage(site({"it": [["a", "b"], ["c"]]}))

    report: ExtractionReport = extraction(
        storage, get_page, ["it"], max_jobs=0
    ).execute()

    assert report.status == RunStatus.COMPLETED
    assert len(storage.read(Table.RAW_JOB_INFO, "jobup")) == 3
    (log,) = storage.read(Table.LOG_RAW_JOB_INFO, "jobup")
    assert (log["status"], log["pages_read"], log["distinct_urls"]) == (
        "completed",
        2,
        3,
    )


def test_max_pages_stops_reading(storage: LocalParquetStorage) -> None:
    """With max_pages=1 the second result page is never requested."""
    get_page: FakeGetPage = FakeGetPage(site({"it": [["a", "b"], ["c"]]}))

    extraction(storage, get_page, ["it"], max_pages=1, max_jobs=0).execute()

    assert LISTING.format(category="it", page=2) not in get_page.requested
    assert len(storage.read(Table.RAW_JOB_INFO, "jobup")) == 2


def test_failed_category_does_not_stop_others(storage: LocalParquetStorage) -> None:
    """A blocked category is logged as failed; the next one is still read."""
    pages: dict[str, Page] = site({"it": [["a"], ["b"]], "finance": [["c"]]})
    pages[LISTING.format(category="it", page=2)] = page(status=403)

    report: ExtractionReport = extraction(
        storage, FakeGetPage(pages), ["it", "finance"], max_jobs=0
    ).execute()

    assert report.status == RunStatus.FAILED
    assert [log.status for log in report.listings] == [
        RunStatus.FAILED,
        RunStatus.COMPLETED,
    ]
    assert "HTTP 403" in (report.listings[0].error or "")
    assert len(storage.read(Table.RAW_JOB_INFO, "jobup")) == 2  # a, then c


def test_details_limited_and_stored(storage: LocalParquetStorage) -> None:
    """max_jobs limits the downloads; each page is stored with its receipt."""
    get_page: FakeGetPage = FakeGetPage(site({"it": [["a", "b", "c"]]}))

    report: ExtractionReport = extraction(
        storage, get_page, ["it"], max_jobs=2
    ).execute()

    assert report.details.extracted == 2
    receipts: list[dict[str, Any]] = storage.read(Table.RAW_JOB_DETAIL, "jobup")
    assert [r["url"] for r in receipts] == [
        DETAIL.format(id="a"),
        DETAIL.format(id="b"),
    ]
    assert all(
        storage.has_file(f"{Table.RAW_JOB_DETAIL_HTML}/{r['raw_hash']}.html")
        for r in receipts
    )


def test_nothing_downloaded_twice(storage: LocalParquetStorage) -> None:
    """A second run only downloads what is still to extract."""
    pages: dict[str, Page] = site({"it": [["a", "b"]]})
    extraction(storage, FakeGetPage(pages), ["it"], max_jobs=1).execute()
    get_page: FakeGetPage = FakeGetPage(pages)

    extraction(storage, get_page, ["it"]).execute()

    assert [url for url in get_page.requested if "detail" in url] == [
        DETAIL.format(id="b")
    ]


def test_failures_logged_then_set_aside(storage: LocalParquetStorage) -> None:
    """A failing job is logged each time, then set aside after max_failures."""
    pages: dict[str, Page] = site({"it": [["a"]]})
    pages[DETAIL.format(id="a")] = page(status=404)
    for _ in range(2):
        extraction(storage, FakeGetPage(pages), ["it"]).execute()

    report: ExtractionReport = extraction(storage, FakeGetPage(pages), ["it"]).execute()

    failures: list[dict[str, Any]] = storage.read(Table.LOG_RAW_JOB_DETAIL, "jobup")
    assert [f["error"] for f in failures] == ["HTTP 404", "HTTP 404"]
    assert (report.details.failed, report.details.set_aside) == (0, 1)


def test_test_run_writes_apart(tmp_path: Path) -> None:
    """A test run writes its records, flagged is_test, in the test zone only."""
    real: LocalParquetStorage = LocalParquetStorage(is_test=False, data_dir=tmp_path)
    test: LocalParquetStorage = LocalParquetStorage(is_test=True, data_dir=tmp_path)

    extraction(test, FakeGetPage(site({"it": [["a"]]})), ["it"]).execute()

    assert real.read(Table.RAW_JOB_INFO, "jobup") == []
    assert [r["is_test"] for r in test.read(Table.RAW_JOB_DETAIL, "jobup")] == [True]


def test_wrong_options_refused(storage: LocalParquetStorage) -> None:
    """Options without category are refused before any request."""
    get_page: FakeGetPage = FakeGetPage({})
    with pytest.raises(ValidationError):
        extraction(storage, get_page, []).execute()
    assert get_page.requested == []


def test_payload_stored_and_signed(storage: LocalParquetStorage) -> None:
    """Each page is stored with its JSON-LD block and the scraper that read it."""
    extraction(storage, FakeGetPage(site({"it": [["a", "b"]]})), ["it"]).execute()

    receipts: list[dict[str, Any]] = storage.read(Table.RAW_JOB_DETAIL, "jobup")
    assert [json.loads(r["payload"])["title"] for r in receipts] == ["a", "b"]
    assert {
        (r["payload_format"], r["scraper"], r["scraper_version"]) for r in receipts
    } == {("json_ld", "jobup_extraction", JobupExtraction.version)}


def test_paragraphs_without_json_ld(storage: LocalParquetStorage) -> None:
    """A page without JSON-LD is stored with its paragraphs: nothing is lost."""
    pages: dict[str, Page] = site({"it": [["a"]]})
    pages[DETAIL.format(id="a")] = page(content=b"<html><p>Data Engineer</p></html>")

    report: ExtractionReport = extraction(storage, FakeGetPage(pages), ["it"]).execute()

    assert report.details.extracted == 1
    (receipt,) = storage.read(Table.RAW_JOB_DETAIL, "jobup")
    assert receipt["payload_format"] == PayloadFormat.PARAGRAPHS
    assert json.loads(receipt["payload"]) == ["Data Engineer"]


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


def test_crash_keeps_what_was_written(storage: LocalParquetStorage) -> None:
    """Jobs are written one by one: a crash on the 3rd keeps the first two."""
    pages: dict[str, Page] = site({"it": [["a", "b", "c", "d"]]})
    crashing: CrashingGetPage = CrashingGetPage(pages, DETAIL.format(id="c"))
    with pytest.raises(RuntimeError):
        extraction(storage, crashing, ["it"]).execute()

    get_page: FakeGetPage = FakeGetPage(pages)
    extraction(storage, get_page, ["it"]).execute()

    assert [url for url in get_page.requested if "detail" in url] == [
        DETAIL.format(id="c"),
        DETAIL.format(id="d"),
    ]
    receipts: list[dict[str, Any]] = storage.read(Table.RAW_JOB_DETAIL, "jobup")
    assert sorted(json.loads(r["payload"])["title"] for r in receipts) == [
        "a",
        "b",
        "c",
        "d",
    ]
