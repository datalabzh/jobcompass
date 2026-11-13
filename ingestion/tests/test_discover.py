"""
test_discover.py

Description : tests of the discovery step.
Rules       : every page is read and loaded as is; the snapshot record is written
              last and only when every page was read; a failing page leaves the
              pages already read but no snapshot record.
"""

import json

import pyarrow.parquet as pq
import pytest
from conftest import NOW

from jobcompass_ingestion.discover import ListingPage, discover_offers

A = "https://www.jobup.ch/fr/emplois/detail/a/"
B = "https://www.jobup.ch/fr/emplois/detail/b/"
C = "https://www.jobup.ch/fr/emplois/detail/c/"


def offer(url):
    return (url, json.dumps({"url": url}))


def reader(pages, fail_on=None):
    """pages = list of offer lists, page 1 first."""

    async def read_page(number):
        if number == fail_on:
            raise RuntimeError("blocked")
        return ListingPage(
            announced_total=3, num_pages=len(pages), offers=pages[number - 1]
        )

    return read_page


async def run(read_page, store):
    return await discover_offers(
        source="jobup",
        params={"category": "informatique-telecommunications"},
        read_page=read_page,
        store=store,
        now=lambda: NOW,
    )


def read_dataset(tmp_path, name):
    files = sorted((tmp_path / name).rglob("*.parquet"))
    return [row for f in files for row in pq.read_table(f).to_pylist()]


async def test_every_page_loaded_then_snapshot(store, tmp_path):
    pages = [[offer(A), offer(B)], [offer(B), offer(C)]]

    snapshot = await run(reader(pages), store)

    rows = read_dataset(tmp_path, "discovered")
    assert len(rows) == 4
    assert {r["snapshot_id"] for r in rows} == {snapshot.snapshot_id}
    assert json.loads(rows[0]["listing_payload"]) == {"url": A}
    assert (snapshot.pages_read, snapshot.offers_seen, snapshot.distinct_urls) == (
        2,
        4,
        3,
    )
    assert snapshot.announced_total == 3
    assert read_dataset(tmp_path, "discovery_snapshot")[0]["snapshot_id"] == (
        snapshot.snapshot_id
    )


async def test_failing_page_keeps_read_pages_but_no_snapshot(store, tmp_path):
    pages = [[offer(A)], [offer(B)], [offer(C)]]

    with pytest.raises(RuntimeError):
        await run(reader(pages, fail_on=3), store)

    assert len(read_dataset(tmp_path, "discovered")) == 2
    assert read_dataset(tmp_path, "discovery_snapshot") == []


async def test_each_run_is_a_new_snapshot(store, tmp_path):
    first = await run(reader([[offer(A)]]), store)
    second = await run(reader([[offer(A)]]), store)

    assert first.snapshot_id != second.snapshot_id
    assert len(read_dataset(tmp_path, "discovered")) == 2
