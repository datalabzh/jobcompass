"""Named, validated field types shared by the contracts."""

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
