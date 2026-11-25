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
              Code de sortie 0 (les pages illisibles sont comptées dans failed du
              rapport, sans arrêter le passage) ; 2 si la configuration ou les
              options sont incorrectes (ex. normaliseur inconnu) ; 3 si une erreur
              imprévue a arrêté la normalisation (base injoignable...).
"""

import argparse
import dataclasses
import json
import logging
import sys
from datetime import UTC, datetime
from functools import partial

from entrypoints.config.config_reader import ConfigError, DbStorageSection
from entrypoints.config.normalization_config import (
    NormalizationConfig,
    NormalizationConfigReader,
    NormalizerConfig,
)
from entrypoints.run_limits import RunLimits, add_limit_options, resolve_limits
from normalization.interfaces.i_normalization_uc import (
    INormalizationUseCase,
    NormalizationReport,
)

LIMITS: list[str] = ["max_jobs"]
UNEXPECTED_ERROR: int = 3  # exit code of a run stopped by an unexpected error


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Read the command and its options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="jobcompass-normalization"
    )
    commands: argparse._SubParsersAction = parser.add_subparsers(
        dest="command", required=True
    )
    run: argparse.ArgumentParser = commands.add_parser(
        "run", help="normalize the job detail pages of a source"
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
    db: DbStorageSection = common.db_storage
    return normalizer.use_case(
        source=source,
        db_storage=db.storage_class(is_test=limits.is_test, **db.options),
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
    try:
        report: NormalizationReport = build_normalization(
            args.source, common, normalizer, limits
        ).execute()
    except Exception:
        logging.exception("jobcompass-normalization: unexpected error, run stopped")
        return UNEXPECTED_ERROR
    print(json.dumps(dataclasses.asdict(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
