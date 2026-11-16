"""
local_parquet_storage.py

Description : stockage sur disque local : tables en fichiers Parquet, fichiers
              bruts tels quels.
Règles      : chaque ajout écrit un nouveau fichier Parquet :
                <racine>/<table>/source=<source>/date=<date UTC>/part-<id>.parquet
              racine = data_dir pour un vrai passage, data_dir/test pour un test :
              supprimer data_dir/test efface toutes les données de test.
              Schémas Parquet explicites : tous les fichiers d'une table ont les
              mêmes types.
              listing_params (un dict) est stocké en map Parquet.
              Fichiers bruts : <racine>/<nom>, écrits dans un fichier temporaire
              puis renommés, pour qu'un fichier ne soit jamais à moitié écrit.
"""

import os
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from contracts import ContractModel
from extraction.interfaces.i_storage import IStorage, Table

Row = dict[str, Any]  # one Parquet row, column name -> value

_TIMESTAMP: pa.DataType = pa.timestamp("us", tz="UTC")
_PARAMS: pa.DataType = pa.map_(pa.string(), pa.string())

SCHEMAS: dict[Table, pa.Schema] = {
    Table.JOB_INFO: pa.schema(
        [
            ("schema_version", pa.string()),
            ("run_id", pa.string()),
            ("source", pa.string()),
            ("is_test", pa.bool_()),
            ("url", pa.string()),
            ("seen_at", _TIMESTAMP),
            ("listing_params", _PARAMS),
            ("card", pa.string()),
        ]
    ),
    Table.JOB_INFO_EXTRACTION_LOG: pa.schema(
        [
            ("schema_version", pa.string()),
            ("run_id", pa.string()),
            ("source", pa.string()),
            ("is_test", pa.bool_()),
            ("listing_params", _PARAMS),
            ("started_at", _TIMESTAMP),
            ("finished_at", _TIMESTAMP),
            ("status", pa.string()),
            ("error", pa.string()),
            ("announced_total", pa.int64()),
            ("pages_read", pa.int64()),
            ("jobs_seen", pa.int64()),
            ("distinct_urls", pa.int64()),
        ]
    ),
    Table.JOB_DETAIL: pa.schema(
        [
            ("schema_version", pa.string()),
            ("source", pa.string()),
            ("is_test", pa.bool_()),
            ("url", pa.string()),
            ("raw_hash", pa.string()),
            ("content_type", pa.string()),
            ("fetched_at", _TIMESTAMP),
            ("http_status", pa.int16()),
            ("scraper_version", pa.string()),
        ]
    ),
    Table.JOB_DETAIL_EXTRACTION_LOG: pa.schema(
        [
            ("schema_version", pa.string()),
            ("source", pa.string()),
            ("is_test", pa.bool_()),
            ("url", pa.string()),
            ("attempted_at", _TIMESTAMP),
            ("error", pa.string()),
        ]
    ),
}


class LocalParquetStorage(IStorage):
    """Tables as Parquet files and raw files, under one local folder."""

    def __init__(self, is_test: bool, data_dir: str | Path) -> None:
        super().__init__(is_test)
        self.data_dir: Path = Path(data_dir) / "test" if is_test else Path(data_dir)

    def append(self, table: Table, records: Sequence[ContractModel]) -> None:
        """Write the records as one new Parquet file per source."""
        rows: list[Row] = [self._to_row(record) for record in records]
        sources: list[str] = sorted({row["source"] for row in rows})
        for source in sources:
            selected: list[Row] = [row for row in rows if row["source"] == source]
            self._write_parquet(table, source, selected)

    def read(self, table: Table, source: str) -> list[dict[str, Any]]:
        """Every line of a table for a source, all files together."""
        files: list[Path] = sorted(self._table_dir(table, source).rglob("*.parquet"))
        return [row for file in files for row in pq.read_table(file).to_pylist()]

    def put_file(self, name: str, content: bytes) -> None:
        """Write a raw file through a temporary file and a rename."""
        path: Path = self.data_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp: Path = path.with_name(path.name + ".tmp")
        tmp.write_bytes(content)
        os.replace(tmp, path)

    def has_file(self, name: str) -> bool:
        """True if the raw file exists."""
        return (self.data_dir / name).exists()

    def _table_dir(self, table: Table, source: str) -> Path:
        """Folder of a table for a source."""
        return self.data_dir / table.value / f"source={source}"

    def _write_parquet(self, table: Table, source: str, rows: list[Row]) -> None:
        """Write rows as a new file under today's partition."""
        now: datetime = datetime.now(UTC)
        folder: Path = self._table_dir(table, source) / f"date={now:%Y-%m-%d}"
        folder.mkdir(parents=True, exist_ok=True)
        name: str = f"part-{now:%Y%m%dT%H%M%S%f}-{uuid.uuid4().hex[:8]}.parquet"
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMAS[table]), folder / name)

    def _to_row(self, record: ContractModel) -> Row:
        """A contract record as a Parquet row: listing_params as a map."""
        row: Row = record.model_dump()
        if "listing_params" in row:
            row["listing_params"] = list(row["listing_params"].items())
        return row
