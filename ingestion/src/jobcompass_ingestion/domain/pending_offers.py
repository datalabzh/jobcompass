"""
pending_offers.py

Description : computes the offers still to fetch for a source.
Rules       : pending = discovered URLs - URLs already fetched with success
              - URLs set aside.
              An offer is identified by (source, url).
              Set aside = MAX_FETCH_FAILURES failed attempts or more, kept for review.
              Discovered URLs may repeat (one line per observation): each offer
              is kept once, in order of first discovery.
              Pure logic: no I/O, inputs given by the use case.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

OfferKey = tuple[str, str]  # (source, url)


@dataclass(frozen=True)
class PendingOffers:
    to_fetch: list[OfferKey]
    set_aside: list[OfferKey]


def compute_pending_offers(
    discovered: Iterable[OfferKey],
    fetched: Iterable[OfferKey],
    failure_counts: Mapping[OfferKey, int],
    max_failures: int,
) -> PendingOffers:
    already_fetched = set(fetched)
    to_fetch: list[OfferKey] = []
    set_aside: list[OfferKey] = []
    for key in dict.fromkeys(discovered):
        if key in already_fetched:
            continue
        if failure_counts.get(key, 0) >= max_failures:
            set_aside.append(key)
        else:
            to_fetch.append(key)
    return PendingOffers(to_fetch=to_fetch, set_aside=set_aside)
