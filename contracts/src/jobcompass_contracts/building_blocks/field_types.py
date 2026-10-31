"""
field_types.py

Description : named, validated field types shared by the contracts.
Rules       : each type carries its validation pattern and description, both
              exported in the JSON Schema.
              SourceSlug  = lowercase letters, digits and underscores, e.g. 'jobup'.
              OfferUrl    = http(s) URL without spaces.
              Sha256Hash  = 64 lowercase hex characters (see raw_content_hash).
"""

from typing import Annotated

from pydantic import Field

SourceSlug = Annotated[
    str, Field(pattern=r"^[a-z0-9_]+$", description="Portal slug, e.g. 'jobup'")
]

OfferUrl = Annotated[
    str, Field(pattern=r"^https?://\S+$", description="Normalized offer URL")
]

Sha256Hash = Annotated[
    str,
    Field(pattern=r"^[0-9a-f]{64}$", description="SHA-256 of the uncompressed content"),
]
