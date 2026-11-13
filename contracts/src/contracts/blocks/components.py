"""
components.py

Description : the components contracts are made of: closed lists of values, named
              field types and the raw_hash function.
Rules       : enumerations are StrEnum, so Parquet files hold readable values.
              Field types carry their validation pattern and description, both
              exported in the JSON Schema:
                SourceSlug = lowercase letters, digits and underscores, e.g. 'jobup'.
                JobUrl     = http(s) URL without spaces.
                Sha256Hash = 64 lowercase hex characters.
              raw_hash = SHA-256 of the uncompressed content, as lowercase hex.
              Every brick computes it with compute_raw_hash, so the same content
              always gets the same hash and the same storage path.
"""

import hashlib
from enum import StrEnum
from typing import Annotated, TypeAlias

from pydantic import Field

# --- enumerations ---------------------------------------------------------------


class RunStatus(StrEnum):
    """Outcome of one run of an ingestion step."""

    COMPLETED = "completed"  # every page was read without error
    FAILED = "failed"  # the run stopped on an error


# --- field types ----------------------------------------------------------------

SourceSlug: TypeAlias = Annotated[
    str, Field(pattern=r"^[a-z0-9_]+$", description="Portal slug, e.g. 'jobup'")
]

JobUrl: TypeAlias = Annotated[
    str, Field(pattern=r"^https?://\S+$", description="URL of the job detail page")
]

Sha256Hash: TypeAlias = Annotated[
    str,
    Field(pattern=r"^[0-9a-f]{64}$", description="SHA-256 of the uncompressed content"),
]


# --- functions ------------------------------------------------------------------


def compute_raw_hash(content: bytes) -> str:
    """Return the raw_hash of a content: SHA-256 of the uncompressed bytes, hex."""
    return hashlib.sha256(content).hexdigest()
