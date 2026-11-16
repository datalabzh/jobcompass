"""
local_parquet_storage.py

Description : stockage sur disque local : tables en fichiers Parquet, fichiers
              bruts tels quels.
Règles      : chaque ajout écrit un nouveau fichier Parquet :
                <racine>/<table>/source=<source>/date=<date UTC>/part-<id>.parquet
              racine = data_dir pour un vrai passage, data_dir/test pour un test :
              supprimer data_dir/test efface toutes les données de test.
              Schéma Parquet déduit des champs du contrat des enregistrements : tous
              les fichiers d'une table ont les mêmes types, et un nouveau contrat ne
              demande rien ici. Correspondances :
                str, Literal, énumération  -> texte
                bool                        -> booléen
                int                         -> entier 64 bits
                float                       -> réel 64 bits
                datetime (avec fuseau)      -> horodatage UTC, en microsecondes
                dict[str, str]              -> map texte -> texte
              X | None = colonne nullable ; sinon obligatoire. Un type non prévu
              lève TypeError : on l'ajoute ici le jour où un contrat en a besoin.
              Un ajout ne mélange pas deux contrats.
              Fichiers bruts : <racine>/<nom>, écrits dans un fichier temporaire
              puis renommés, pour qu'un fichier ne soit jamais à moitié écrit.
"""

import os
import types
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import AwareDatetime

from contracts import ContractModel
from storage.i_storage import IStorage

Row = dict[str, Any]  # one Parquet row, column name -> value

TIMESTAMP: pa.DataType = pa.timestamp("us", tz="UTC")
STRING_MAP: pa.DataType = pa.map_(pa.string(), pa.string())


class LocalParquetStorage(IStorage):
    """Tables as Parquet files and raw files, under one local folder."""

    def __init__(self, is_test: bool, data_dir: str | Path) -> None:
        super().__init__(is_test)
        self.data_dir: Path = Path(data_dir) / "test" if is_test else Path(data_dir)

    def append(self, table: str, records: Sequence[ContractModel]) -> None:
        """Write the records as one new Parquet file per source."""
        if not records:
            return
        schema: pa.Schema = self._schema_of(records)
        rows: list[Row] = [self._to_row(record) for record in records]
        for source in sorted({row["source"] for row in rows}):
            selected: list[Row] = [row for row in rows if row["source"] == source]
            self._write_parquet(table, source, schema, selected)

    def read(self, table: str, source: str) -> list[dict[str, Any]]:
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

    # --- files ------------------------------------------------------------------

    def _table_dir(self, table: str, source: str) -> Path:
        """Folder of a table for a source."""
        return self.data_dir / table / f"source={source}"

    def _write_parquet(
        self, table: str, source: str, schema: pa.Schema, rows: list[Row]
    ) -> None:
        """Write rows as a new file under today's partition."""
        now: datetime = datetime.now(UTC)
        folder: Path = self._table_dir(table, source) / f"date={now:%Y-%m-%d}"
        folder.mkdir(parents=True, exist_ok=True)
        name: str = f"part-{now:%Y%m%dT%H%M%S%f}-{uuid.uuid4().hex[:8]}.parquet"
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), folder / name)

    def _to_row(self, record: ContractModel) -> Row:
        """A contract record as a Parquet row: dictionaries as map entries."""
        row: Row = record.model_dump()
        for name, value in row.items():
            if isinstance(value, dict):
                row[name] = list(value.items())
        return row

    # --- Parquet schema, deduced from the contract ------------------------------

    def _schema_of(self, records: Sequence[ContractModel]) -> pa.Schema:
        """The Parquet schema of the records' contract; one contract only."""
        contracts: set[type[ContractModel]] = {type(record) for record in records}
        if len(contracts) > 1:
            raise ValueError(f"one contract per append, got {contracts}")
        contract: type[ContractModel] = contracts.pop()
        fields: list[pa.Field] = []
        for name, info in contract.model_fields.items():
            annotation, nullable = self._unwrap_optional(info.annotation)
            fields.append(
                pa.field(name, self._parquet_type(annotation), nullable=nullable)
            )
        return pa.schema(fields)

    def _unwrap_optional(self, annotation: Any) -> tuple[Any, bool]:  # noqa: ANN401
        """(X, True) for X | None, (annotation, False) otherwise."""
        if get_origin(annotation) in (Union, types.UnionType):
            args: list[Any] = [a for a in get_args(annotation) if a is not type(None)]
            if len(args) == 1:
                return args[0], True
        return annotation, False

    def _parquet_type(self, annotation: Any) -> pa.DataType:  # noqa: ANN401
        """The Parquet type of one field annotation."""
        if get_origin(annotation) is Literal:
            return self._parquet_type(type(get_args(annotation)[0]))
        if get_origin(annotation) is dict and get_args(annotation) == (str, str):
            return STRING_MAP
        if annotation in (datetime, AwareDatetime):
            return TIMESTAMP
        if isinstance(annotation, type):
            if issubclass(annotation, bool):  # before int: bool is an int in Python
                return pa.bool_()
            if issubclass(annotation, (str, Enum)):
                return pa.string()
            if issubclass(annotation, int):
                return pa.int64()
            if issubclass(annotation, float):
                return pa.float64()
        raise TypeError(f"no Parquet type for {annotation!r}")
