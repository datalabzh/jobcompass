"""
run_limits.py

Description : limites d'un passage (garde-fous de test), communes à tous les points
              d'entrée.
Règles      : sans option : passage de test, limité par les valeurs de site.toml ;
              une option --max-... remplace sa limite (toujours un test) ;
              --full lève toutes les limites (vrai passage) et ne se combine pas
              avec elles.
              Un passage avec au moins une limite est un test : ses données portent
              is_test = true et vont dans la zone de test du stockage.
"""

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class RunLimits:
    """Limits of a run, by name; None = no limit. Any limit makes it a test."""

    limits: dict[str, int | None]

    @property
    def is_test(self) -> bool:
        """True unless the run has no limit at all (--full)."""
        return any(value is not None for value in self.limits.values())

    def __getitem__(self, name: str) -> int | None:
        """The value of one limit (None = no limit)."""
        return self.limits[name]


def add_limit_options(parser: argparse.ArgumentParser, names: list[str]) -> None:
    """Add --full and one --max-<name> option per limit."""
    for name in names:
        parser.add_argument(f"--{name.replace('_', '-')}", type=int, dest=name)
    parser.add_argument("--full", action="store_true", help="no limit (real run)")


def resolve_limits(args: argparse.Namespace, defaults: dict[str, int]) -> RunLimits:
    """--full: no limit; otherwise each option, or its default from site.toml."""
    given: dict[str, int | None] = {name: getattr(args, name) for name in defaults}
    if args.full:
        if any(value is not None for value in given.values()):
            raise ValueError("--full cannot be combined with a --max-... option")
        return RunLimits({name: None for name in defaults})
    return RunLimits(
        {
            name: value if value is not None else defaults[name]
            for name, value in given.items()
        }
    )
