"""
test_pending_offers.py

Description : tests of the pending offers rule.
Rules       : covers deduplication, fetched URLs, set aside threshold and order.
"""

from jobcompass_ingestion.domain.pending_offers import compute_pending_offers

A = ("jobup", "https://www.jobup.ch/a")
B = ("jobup", "https://www.jobup.ch/b")
C = ("jobup", "https://www.jobup.ch/c")


def test_discovered_not_fetched_is_pending():
    result = compute_pending_offers(
        [A, B], fetched=[A], failure_counts={}, max_failures=3
    )
    assert result.to_fetch == [B]
    assert result.set_aside == []


def test_repeated_observations_kept_once_in_first_discovery_order():
    result = compute_pending_offers(
        [B, A, B, A, C], fetched=[], failure_counts={}, max_failures=3
    )
    assert result.to_fetch == [B, A, C]


def test_below_threshold_still_pending():
    result = compute_pending_offers(
        [A], fetched=[], failure_counts={A: 2}, max_failures=3
    )
    assert result.to_fetch == [A]


def test_threshold_reached_set_aside():
    result = compute_pending_offers(
        [A, B], fetched=[], failure_counts={A: 3}, max_failures=3
    )
    assert result.to_fetch == [B]
    assert result.set_aside == [A]


def test_fetched_offer_never_set_aside():
    result = compute_pending_offers(
        [A], fetched=[A], failure_counts={A: 5}, max_failures=3
    )
    assert result.to_fetch == []
    assert result.set_aside == []
