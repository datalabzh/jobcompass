"""
fetched_page_dto.py

Description : the answer of a page fetcher for one URL.
Rules       : content = body as received, uncompressed, never modified.
              Any HTTP status is returned as is: the use case decides what is
              a success.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FetchedPage:
    content: bytes
    http_status: int
    content_type: str
