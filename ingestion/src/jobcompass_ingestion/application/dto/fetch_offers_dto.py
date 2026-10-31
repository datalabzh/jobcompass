"""
fetch_offers_dto.py

Description : input and output of the fetch offers use case.
Rules       : input = the source to process, and an optional limit on the number
              of URLs (manual runs, tests). No limit = everything pending.
              output = counts only, for the logs and the orchestrator.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FetchOffersInput:
    source: str
    limit: int | None = None


@dataclass(frozen=True)
class FetchOffersOutput:
    fetched: int
    failed: int
    set_aside: int  # URLs skipped because of too many failures
