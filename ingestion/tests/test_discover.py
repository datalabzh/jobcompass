"""
test_discover.py

Description : tests of the discovery step.
Rules       : every observation is written, known URLs included; the discovery
              context is kept in discovery_params.
"""

from conftest import NOW

from jobcompass_contracts import DiscoveryMethod
from jobcompass_ingestion.discover import discover_offers

A = "https://www.jobup.ch/a"
B = "https://www.jobup.ch/b"


def finder(found):
    async def find_offer_urls(method, params):
        return list(found)

    return find_offer_urls


async def run(found, store):
    return await discover_offers(
        source="jobup",
        method=DiscoveryMethod.LISTING,
        params={"category": "702"},
        find_offer_urls=finder(found),
        store=store,
        now=lambda: NOW,
    )


async def test_every_observation_written(store):
    found = [(A, {"page": "1"}), (B, {"page": "1"}), (A, {"page": "2"})]

    summary = await run(found, store)

    assert (summary.observed, summary.distinct_urls) == (3, 2)
    assert len(store.discovered_keys("jobup")) == 3


async def test_known_urls_written_again_on_next_run(store):
    await run([(A, {})], store)
    await run([(A, {})], store)

    assert store.discovered_keys("jobup") == [("jobup", A), ("jobup", A)]


async def test_run_context_kept(store, tmp_path):
    import pyarrow.parquet as pq

    await run([(A, {"page": "3"})], store)

    table = pq.read_table(next((tmp_path / "discovered").rglob("*.parquet")))
    row = table.to_pylist()[0]
    assert row["discovered_at"] == NOW
    assert row["discovery_method"] == "listing"
    assert dict(row["discovery_params"]) == {"category": "702", "page": "3"}
