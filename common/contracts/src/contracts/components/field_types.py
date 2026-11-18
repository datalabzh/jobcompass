"""
field_types.py

Description : les composants dont sont faits les contrats : listes fermées de
              valeurs (RunStatus, SkillOrigin, PayloadFormat), types de champs nommés et
              fonction raw_hash.
Règles      : les énumérations sont des StrEnum, pour que les fichiers Parquet
              contiennent des valeurs lisibles.
              Les types de champs portent leur motif de validation et leur
              description, tous deux exportés dans le JSON Schema :
                SourceSlug = minuscules, chiffres et underscores, ex. 'jobup'.
                JobUrl     = URL http(s) sans espace.
                Sha256Hash = 64 caractères hexadécimaux minuscules.
              raw_hash = SHA-256 du contenu non compressé, en hexadécimal minuscule.
              Toutes les briques le calculent avec compute_raw_hash : un même contenu
              a toujours le même hash et le même chemin de stockage.
"""

import hashlib
from enum import StrEnum
from typing import Annotated, TypeAlias

from pydantic import Field

# --- enumerations ---------------------------------------------------------------


class RunStatus(StrEnum):
    """Outcome of one run of an extraction step."""

    COMPLETED = "completed"  # the planned pages were read without error
    FAILED = "failed"  # the run stopped on an error


class SkillOrigin(StrEnum):
    """Where a skill of a normalized job comes from."""

    DECLARED = "declared"  # given as such by the source (e.g. a skills field)
    DETECTED = "detected"  # found in the text by the normalizer


class PayloadFormat(StrEnum):
    """What the payload of a job detail page holds."""

    JSON_LD = "json_ld"  # the JSON-LD of the page, as is
    PARAGRAPHS = "paragraphs"  # no JSON-LD: the paragraphs of the HTML, in order


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
