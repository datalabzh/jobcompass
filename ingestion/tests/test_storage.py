"""
test_storage.py

Description : tests of the ingestion datasets and raw content storage.
Rules       : what is appended is read back; files follow the
              <dataset>/source=/date=/part-*.parquet layout; content is stored by hash.
"""

from datetime import timedelta

from conftest import NOW, discovered

from jobcompass_contracts import RawOffer, compute_raw_hash
from jobcompass_ingestion.storage import FetchAttempt

A = "https://www.jobup.ch/a"
B = "https://www.jobup.ch/b"


def test_discovered_read_back_in_discovery_order(store):
    store.append_discovered(discovered(B, at=NOW + timedelta(hours=1)))
    store.append_discovered(discovered(A, B, at=NOW))

    assert store.discovered_keys("jobup") == [("jobup", A), ("jobup", B), ("jobup", B)]


def test_discovery_params_kept(store, tmp_path):
    import pyarrow.parquet as pq

    offer = discovered(A)[0].model_copy(update={"discovery_params": {"page": "3"}})
    store.append_discovered([offer])

    files = list((tmp_path / "discovered" / "source=jobup").rglob("part-*.parquet"))
    assert len(files) == 1
    assert files[0].parent.name.startswith("date=")
    assert pq.read_table(files[0]).column("discovery_params").to_pylist() == [
        [("page", "3")]
    ]


def test_fetched_keys(store):
    raw = RawOffer(
        source="jobup",
        url=A,
        raw_hash=compute_raw_hash(b"x"),
        content_type="text/html",
        fetched_at=NOW,
        http_status=200,
        scraper_version="0.1.0",
    )
    store.append_raw_offers([raw])

    assert store.fetched_keys("jobup") == {("jobup", A)}
    assert store.fetched_keys("other") == set()


def test_failure_counts(store):
    store.append_fetch_attempts([FetchAttempt("jobup", A, NOW, "HTTP 500")] * 2)
    store.append_fetch_attempts([FetchAttempt("jobup", B, NOW, "HTTP 404")])

    assert store.failure_counts("jobup") == {("jobup", A): 2, ("jobup", B): 1}


def test_empty_store(store):
    assert store.discovered_keys("jobup") == []
    assert store.failure_counts("jobup") == {}


def test_content_stored_by_hash(store, tmp_path):
    raw_hash = compute_raw_hash(b"<html/>")
    assert not store.has_content(raw_hash)

    store.put_content(raw_hash, b"<html/>")

    assert store.has_content(raw_hash)
    assert (tmp_path / "raw" / "html" / f"{raw_hash}.html").read_bytes() == b"<html/>"
