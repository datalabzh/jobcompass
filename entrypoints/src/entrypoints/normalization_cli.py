"""
normalization_cli.py

Description : point d'entrée en ligne de commande de la normalisation, appelé à la
              main ou par Dagster.
Règles      : jobcompass-normalization run <source> [--normalizer NOM] [--max-jobs N]
              jobcompass-normalization run <source> [--normalizer NOM] --full
              La commande ne connaît que la source à normaliser (ex. jobup) et, en
              option, le normaliseur (nom de son dossier) ; sans option, celui
              désigné par default dans normalization.toml. La classe et ses
              réglages viennent du normalizer.toml du normaliseur, le stockage du
              normalization.toml commun, tous deux lus par
              NormalizationConfigReader.
              Limites : voir run_limits.py (sans option = test limité par le
              normalizer.toml ; un test ne lit et n'écrit que la zone de test).
              La dernière ligne affichée est le rapport JSON (lu par Dagster).
              Code de sortie 0 ; 2 si la configuration ou les options sont
              incorrectes (ex. normaliseur inconnu).
"""

import argparse
import dataclasses
import json
import sys
from datetime import UTC, datetime
from functools import partial

from entrypoints.config.config_reader import ConfigError
from entrypoints.config.normalization_config import (
    NormalizationConfig,
    NormalizationConfigReader,
    NormalizerConfig,
)
from entrypoints.run_limits import RunLimits, add_limit_options, resolve_limits
from normalization.interfaces import INormalizationUseCase, NormalizationReport

LIMITS: list[str] = ["max_jobs"]


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Read the command and its options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="jobcompass-normalization"
    )
    commands: argparse._SubParsersAction = parser.add_subparsers(
        dest="command", required=True
    )
    run: argparse.ArgumentParser = commands.add_parser(
        "run", help="normalize the extracted jobs of a source"
    )
    run.add_argument("source", help="source to normalize, e.g. jobup")
    run.add_argument(
        "--normalizer", help="folder name of the normalizer (default: see toml)"
    )
    add_limit_options(run, LIMITS)
    return parser.parse_args(argv)


def build_normalization(
    source: str,
    common: NormalizationConfig,
    normalizer: NormalizerConfig,
    limits: RunLimits,
) -> INormalizationUseCase:
    """The normalization class of a normalizer, with its settings."""
    return normalizer.use_case(
        source=source,
        storage=common.storage(is_test=limits.is_test, **common.storage_options),
        is_test=limits.is_test,
        max_jobs=limits["max_jobs"],
        now=partial(datetime.now, UTC),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the command, print its JSON report; return the exit code."""
    args: argparse.Namespace = parse_args(argv)
    try:
        common: NormalizationConfig = NormalizationConfigReader.load_normalization()
        normalizer: NormalizerConfig = NormalizationConfigReader.load_normalizer(
            args.normalizer or common.default
        )
        limits: RunLimits = resolve_limits(args, {"max_jobs": normalizer.max_jobs})
    except (ConfigError, ValueError) as error:
        print(f"jobcompass-normalization: error: {error}", file=sys.stderr)
        return 2
    report: NormalizationReport = build_normalization(
        args.source, common, normalizer, limits
    ).execute()
    print(json.dumps(dataclasses.asdict(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
