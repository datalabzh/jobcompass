"""
extraction_cli.py

Description : point d'entrée en ligne de commande de l'extraction, appelé à la main
              ou par Dagster.
Règles      : jobcompass-extraction run <site> [--max-pages N] [--max-jobs N]
              jobcompass-extraction run <site> --full
              La commande ne connaît que le nom du site : la classe d'extraction du
              site, le stockage et leurs réglages viennent de
              extraction/<site>/site.toml, lu par SiteConfigReader. Tout le processus
              appartient au site.
              Limites : voir run_limits.py (sans option = test limité par site.toml).
              Réglages communs à tous les sites : ExtractionSettings, variables
              EXTRACTION_* ou extraction/.env (voir extraction/settings.py).
              user_agent identifie JobCompass auprès des sites : y mettre un contact.
              La dernière ligne affichée est le rapport JSON (lu par Dagster).
              Code de sortie 0 si completed, 1 si une catégorie a échoué, 2 si la
              configuration ou les options sont incorrectes, 3 si une erreur
              imprévue a arrêté l'extraction (stockage injoignable...) : le code 1
              reste réservé à l'échec d'une catégorie, que l'orchestration
              distingue d'un arrêt.
"""

import argparse
import dataclasses
import json
import logging
import sys
from datetime import UTC, datetime
from functools import partial
from typing import Any

from pydantic import BaseModel

from contracts.components.field_types import RunStatus
from entrypoints.config.config_reader import (
    ConfigError,
    DbStorageSection,
    FileStorageSection,
)
from entrypoints.config.extraction_config import SiteConfig, SiteConfigReader
from entrypoints.run_limits import RunLimits, add_limit_options, resolve_limits
from extraction.http import make_get_page
from extraction.interfaces.i_get_page import GetPage
from extraction.interfaces.i_site_extraction_uc import (
    ExtractionReport,
    ISiteExtractionUseCase,
)
from extraction.settings import ExtractionSettings

LIMITS: list[str] = ["max_pages", "max_jobs"]
UNEXPECTED_ERROR: int = 3  # exit code of a run stopped by an unexpected error


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Read the command and its options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="jobcompass-extraction"
    )
    commands: argparse._SubParsersAction = parser.add_subparsers(
        dest="command", required=True
    )
    run: argparse.ArgumentParser = commands.add_parser(
        "run", help="extract a site: raw job infos, then raw job details"
    )
    run.add_argument("site", help="folder name of the site, e.g. jobup")
    add_limit_options(run, LIMITS)
    return parser.parse_args(argv)


def build_extraction(
    site: str, config: SiteConfig, limits: RunLimits, settings: ExtractionSettings
) -> ISiteExtractionUseCase:
    """The extraction class of a site, with the settings of its site.toml."""
    section = config.extraction
    db: DbStorageSection = config.db_storage
    files: FileStorageSection = config.file_storage
    get_page: GetPage = make_get_page(
        settings.user_agent, settings.http_timeout, section.min_delay_between_requests
    )
    return section.use_case(
        source=site,
        get_page=get_page,
        db_storage=db.storage_class(is_test=limits.is_test, **db.options),
        file_storage=files.storage_class(is_test=limits.is_test, **files.options),
        is_test=limits.is_test,
        max_pages=limits["max_pages"],
        max_jobs=limits["max_jobs"],
        max_failures=settings.max_failures,
        now=partial(datetime.now, UTC),
        options=section.options,
    )


def to_json(value: Any) -> Any:  # noqa: ANN401 (any value json cannot write)
    """JSON form of what json cannot write itself: contracts, dates."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return str(value)


def main(argv: list[str] | None = None) -> int:
    """Run the command, print its JSON report; return the exit code."""
    args: argparse.Namespace = parse_args(argv)
    settings: ExtractionSettings = ExtractionSettings()
    logging.basicConfig(level=settings.log_level, stream=sys.stderr)
    try:
        config: SiteConfig = SiteConfigReader.load_site(args.site)
        defaults: dict[str, int] = {
            "max_pages": config.extraction.max_pages,
            "max_jobs": config.extraction.max_jobs,
        }
        limits: RunLimits = resolve_limits(args, defaults)
    except (ConfigError, ValueError) as error:
        print(f"jobcompass-extraction: error: {error}", file=sys.stderr)
        return 2
    try:
        report: ExtractionReport = build_extraction(
            args.site, config, limits, settings
        ).execute()
    except Exception:
        logging.exception("jobcompass-extraction: unexpected error, run stopped")
        return UNEXPECTED_ERROR
    print(json.dumps(dataclasses.asdict(report), default=to_json))
    return 0 if report.status == RunStatus.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
