"""
test_extraction_cli.py

Description : tests des options du point d'entrée de l'extraction.
Règles      : sans option, les limites de site.toml s'appliquent (test) ;
              --max-pages / --max-jobs les remplacent (toujours un test) ; --full
              lève toutes les limites (vrai passage) et refuse d'être combiné.
"""

import argparse

import pytest

from entrypoints.extraction_cli import main, parse_args
from entrypoints.run_limits import RunLimits, resolve_limits

DEFAULTS: dict[str, int] = {"max_pages": 1, "max_jobs": 2}


def limits(*argv: str) -> RunLimits:
    """The limits of `run jobup <argv>` with the defaults of site.toml."""
    args: argparse.Namespace = parse_args(["run", "jobup", *argv])
    return resolve_limits(args, DEFAULTS)


def test_default_is_a_limited_test() -> None:
    """Without option: limits of site.toml, test run."""
    assert limits() == RunLimits({"max_pages": 1, "max_jobs": 2})
    assert limits().is_test


def test_options_adjust_limits() -> None:
    """An option replaces only its own limit; still a test."""
    assert limits("--max-jobs", "10") == RunLimits({"max_pages": 1, "max_jobs": 10})
    assert limits("--max-jobs", "10").is_test


def test_full_has_no_limit() -> None:
    """--full: no limit at all, real run."""
    assert limits("--full") == RunLimits({"max_pages": None, "max_jobs": None})
    assert not limits("--full").is_test


def test_full_with_a_limit_refused() -> None:
    """--full combined with a limit is refused, before any request."""
    with pytest.raises(ValueError, match="--full"):
        limits("--full", "--max-pages", "3")
    assert main(["run", "jobup", "--full", "--max-pages", "3"]) == 2
