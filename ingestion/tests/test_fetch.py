"""
test_fetch.py

Description : tests of the fetch step and of the pending offers rule.
Rules       : covers deduplication, set aside threshold, success, failures that do
              not stop the others, idempotence, content stored once, limit, batches.
"""

from conftest import NOW, FakeFetchPage, discovered, page

from jobcompass_contracts import compute_raw_hash
from jobcompass_ingestion.fetch import compute_pending_offers, fetch_offers
from jobcompass_ingestion.storage import FetchAttempt

A = "https://www.jobup.ch/a"
B = "https://www.jobup.ch/b"
C = "https://www.jobup.ch/c"
KA, KB, KC = ("jobup", A), ("jobup", B), ("jobup", C)


# --- pending offers rule ----------------------------------------------------


def test_discovered_not_fetched_is_pending():
    result = compute_pending_offers([KA, KB], [KA], {}, max_failures=3)
    assert (result.to_fetch, result.set_aside) == ([KB], [])


def test_repeated_observations_kept_once_in_first_order():
    result = compute_pending_offers([KB, KA, KB, KA, KC], [], {}, max_failures=3)
    assert result.to_fetch == [KB, KA, KC]


def test_threshold_reached_set_aside():
    result = compute_pending_offers([KA, KB], [], {KA: 3, KB: 2}, max_failures=3)
    assert (result.to_fetch, result.set_aside) == ([KB], [KA])


def test_fetched_offer_never_set_aside():
    result = compute_pending_offers([KA], [KA], {KA: 5}, max_failures=3)
    assert (result.to_fetch, result.set_aside) == ([], [])


# --- fetch step ---------------------------------------------------------------


async def run(store, fetch_page, limit=None, batch_size=50):
    return await fetch_offers(
        source="jobup",
        fetch_page=fetch_page,
        store=store,
        scraper_version="0.1.0",
        max_failures=3,
        batch_size=batch_size,
        limit=limit,
        now=lambda: NOW,
    )


async def test_success_stores_content_and_manifest(store):
    store.append_discovered(discovered(A))

    summary = await run(store, FakeFetchPage({A: page()}))

    assert summary.fetched == 1
    assert store.fetched_keys("jobup") == {KA}
    assert store.has_content(compute_raw_hash(b"<html>offer</html>"))


async def test_failures_logged_without_stopping_others(store):
    store.append_discovered(discovered(A, B, C))

    summary = await run(store, FakeFetchPage({A: page(), B: page(status=404)}))

    assert (summary.fetched, summary.failed) == (1, 2)
    assert store.failure_counts("jobup") == {KB: 1, KC: 1}


async def test_set_aside_url_not_requested(store):
    store.append_discovered(discovered(A, B))
    store.append_fetch_attempts([FetchAttempt("jobup", A, NOW, "HTTP 500")] * 3)
    fetch_page = FakeFetchPage({A: page(), B: page()})

    summary = await run(store, fetch_page)

    assert summary.set_aside == 1
    assert fetch_page.requested == [B]


async def test_second_run_fetches_nothing(store):
    store.append_discovered(discovered(A))
    fetch_page = FakeFetchPage({A: page()})

    await run(store, fetch_page)
    summary = await run(store, fetch_page)

    assert summary.fetched == 0
    assert fetch_page.requested == [A]


async def test_same_content_stored_once(store, tmp_path):
    store.append_discovered(discovered(A, B))

    await run(store, FakeFetchPage({A: page(), B: page()}))

    assert store.fetched_keys("jobup") == {KA, KB}
    assert len(list((tmp_path / "raw" / "html").iterdir())) == 1


async def test_limit_and_batches(store):
    store.append_discovered(discovered(A, B, C))
    fetch_page = FakeFetchPage({u: page(content=u.encode()) for u in (A, B, C)})

    summary = await run(store, fetch_page, limit=2, batch_size=1)

    assert summary.fetched == 2
    assert fetch_page.requested == [A, B]
