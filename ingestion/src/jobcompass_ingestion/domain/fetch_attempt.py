"""
fetch_attempt.py

Description : a failed attempt to fetch an offer, line of the fetch attempt log.
Rules       : only failures are logged: a success is a RawOffer in the manifest.
              An offer is identified by (source, url).
              error = short reason (network error, HTTP status), never the content.
              Internal to ingestion: not a shared contract.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FetchAttempt:
    source: str
    url: str
    attempted_at: datetime
    error: str
