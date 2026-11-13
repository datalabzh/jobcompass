"""
i_storage.py

Description : what every storage must provide: append and read tables, put and
              check raw files.
Rules       : tables are append only: a written line is never modified.
              A table holds records of one contract; read returns every line of a
              source, as dictionaries (column name -> value).
              Raw files are named by the caller (e.g. job_detail_html/<hash>.html)
              and written whole or not at all.
              No business rule here: a storage only stores and reads.
              Local disk today (LocalParquetStorage), object storage (MinIO) later.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import StrEnum
from typing import Any

from contracts import ContractModel


class Table(StrEnum):
    """The tables of the ingestion brick."""

    JOB_INFO = "job_info"  # JobInfo, one line per job seen per run
    JOB_INFO_EXTRACTION_LOG = "job_info_extraction_log"  # one line per run
    JOB_DETAIL = "job_detail"  # JobDetail, one line per page downloaded
    JOB_DETAIL_EXTRACTION_LOG = "job_detail_extraction_log"  # one per failure


class IStorage(ABC):
    """Stores and reads the ingestion tables and raw files."""

    @abstractmethod
    def append(self, table: Table, records: Sequence[ContractModel]) -> None:
        """Add records to a table (nothing happens if there is none)."""

    @abstractmethod
    def read(self, table: Table, source: str) -> list[dict[str, Any]]:
        """Every line of a table for a source; empty if nothing was written."""

    @abstractmethod
    def put_file(self, name: str, content: bytes) -> None:
        """Store a raw file under its name, whole or not at all."""

    @abstractmethod
    def has_file(self, name: str) -> bool:
        """True if a raw file with this name is already stored."""
