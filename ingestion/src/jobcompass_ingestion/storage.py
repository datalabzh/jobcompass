"""
storage.py

Description : the datasets of the ingestion brick, and the raw content storage.
Rules       : three datasets, append only, a written line is never modified:
                discovered/      DiscoveredOffer, one line per observation
                raw/manifest/    RawOffer, one line per successful fetch
                fetch_attempts/  FetchAttempt, one line per failed fetch
              Each append writes a new file:
                <dataset>/source=<source>/date=<UTC date>/part-<time>-<id>.parquet
              Explicit Parquet schemas, so every file of a dataset has the same types.
              Raw content stored unchanged in raw/html/<raw_hash>.html, written to a
              temporary file then renamed: a content file is never half written.
              Same hash = same content: putting an existing hash is useless.
              Local disk for now (data_dir); object storage later.
"""

import os
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from jobcompass_contracts import DiscoveredOffer, RawOffer

OfferKey = tuple[str, str]  # (source, url): identifies an offer


@dataclass(frozen=True)
class FetchAttempt:
    """A failed attempt to fetch an offer. Internal to ingestion, not a contract.

    Only failures are logged: a success is a RawOffer in the manifest.
    error = short reason (no answer, HTTP status), never the content.
    """

    source: str
    url: str
    attempted_at: datetime
    error: str


_TIMESTAMP = pa.timestamp("us", tz="UTC")

DISCOVERED_SCHEMA = pa.schema(
    [
        ("schema_version", pa.string()),
        ("source", pa.string()),
        ("url", pa.string()),
        ("discovered_at", _TIMESTAMP),
        ("discovery_method", pa.string()),
        ("discovery_params", pa.map_(pa.string(), pa.string())),
    ]
)

RAW_OFFER_SCHEMA = pa.schema(
    [
        ("schema_version", pa.string()),
        ("source", pa.string()),
        ("url", pa.string()),
        ("raw_hash", pa.string()),
        ("content_type", pa.string()),
        ("fetched_at", _TIMESTAMP),
        ("http_status", pa.int16()),
        ("scraper_version", pa.string()),
        ("source_lastmod", _TIMESTAMP),
    ]
)

FETCH_ATTEMPT_SCHEMA = pa.schema(
    [
        ("source", pa.string()),
        ("url", pa.string()),
        ("attempted_at", _TIMESTAMP),
        ("error", pa.string()),
    ]
)


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)

    # --- writes -------------------------------------------------------------

    def append_discovered(self, offers: Sequence[DiscoveredOffer]) -> None:
        rows = [o.model_dump() for o in offers]
        for row in rows:
            row["discovery_params"] = list(row["discovery_params"].items())
        self._append("discovered", DISCOVERED_SCHEMA, rows)

    def append_raw_offers(self, raw_offers: Sequence[RawOffer]) -> None:
        self._append(
            "raw/manifest", RAW_OFFER_SCHEMA, [r.model_dump() for r in raw_offers]
        )

    def append_fetch_attempts(self, attempts: Sequence[FetchAttempt]) -> None:
        self._append(
            "fetch_attempts", FETCH_ATTEMPT_SCHEMA, [asdict(a) for a in attempts]
        )

    def put_content(self, raw_hash: str, content: bytes) -> None:
        path = self._content_path(raw_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(content)
        os.replace(tmp, path)

    # --- reads --------------------------------------------------------------

    def discovered_keys(self, source: str) -> list[OfferKey]:
        """Every observation, in order of discovery, duplicates included."""
        table = self._read("discovered", source, ["url", "discovered_at"])
        if table is None:
            return []
        table = table.sort_by("discovered_at")
        return [(source, url) for url in table.column("url").to_pylist()]

    def fetched_keys(self, source: str) -> set[OfferKey]:
        table = self._read("raw/manifest", source, ["url"])
        if table is None:
            return set()
        return {(source, url) for url in table.column("url").to_pylist()}

    def failure_counts(self, source: str) -> dict[OfferKey, int]:
        table = self._read("fetch_attempts", source, ["url"])
        if table is None:
            return {}
        counts = table.group_by("url").aggregate([("url", "count")])
        return {
            (source, url): count
            for url, count in zip(
                counts.column("url").to_pylist(),
                counts.column("url_count").to_pylist(),
                strict=True,
            )
        }

    def has_content(self, raw_hash: str) -> bool:
        return self._content_path(raw_hash).exists()

    # --- internals ----------------------------------------------------------

    def _append(self, dataset: str, schema: pa.Schema, rows: list[dict]) -> None:
        if not rows:
            return
        now = datetime.now(UTC)
        for source in sorted({row["source"] for row in rows}):
            folder = (
                self.data_dir / dataset / f"source={source}" / f"date={now:%Y-%m-%d}"
            )
            folder.mkdir(parents=True, exist_ok=True)
            name = f"part-{now:%Y%m%dT%H%M%S%f}-{uuid.uuid4().hex[:8]}.parquet"
            selected = [row for row in rows if row["source"] == source]
            table = pa.Table.from_pylist(selected, schema=schema)
            pq.write_table(table, folder / name)

    def _read(self, dataset: str, source: str, columns: list[str]) -> pa.Table | None:
        folder = self.data_dir / dataset / f"source={source}"
        files = sorted(folder.rglob("*.parquet"))
        if not files:
            return None
        return pa.concat_tables(pq.read_table(f, columns=columns) for f in files)

    def _content_path(self, raw_hash: str) -> Path:
        return self.data_dir / "raw" / "html" / f"{raw_hash}.html"
