"""
cli.py

Description : point d'entrée unique de la brique extraction, appelé à la main,
              par Dagster ou par python -m extraction.<site>.
Règles      : jobcompass-extraction run <site> [--max-pages N] [--max-jobs N]
              jobcompass-extraction run <site> --full
              La commande ne connaît que le nom du site : les classes (job infos,
              job details, stockage) et leurs réglages viennent de sites.toml.
              Sans option : passage de test, limité par max_pages et max_jobs de
              sites.toml ; --max-pages / --max-jobs ajustent ces limites (toujours
              un test) ; --full lève toutes les limites (vrai passage), et ne se
              combine pas avec elles.
              La dernière ligne affichée est le rapport JSON (lu par Dagster).
              Code de sortie 0 si completed, 1 si une catégorie a échoué.
              Nouveau site = une section dans sites.toml, rien à changer ici.
"""

import argparse
import dataclasses
import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from typing import Any

from pydantic import BaseModel

from contracts import RunStatus
from extraction.config import (
    ConfigError,
    ExtractionSettings,
    SiteConfig,
    import_class,
    load_sites_config,
)
from extraction.http import GetPage, make_get_page
from extraction.interfaces.i_job_details_extractor import IJobDetailsExtractor
from extraction.interfaces.i_job_infos_extractor import IJobInfosExtractor
from extraction.interfaces.i_storage import IStorage
from extraction.site_extraction import ExtractionReport, SiteExtraction


@dataclass(frozen=True)
class RunLimits:
    """Limits of a run: None = no limit. A run with limits is a test."""

    max_pages: int | None
    max_jobs: int | None

    @property
    def is_test(self) -> bool:
        """True unless the run has no limit at all (--full)."""
        return self.max_pages is not None or self.max_jobs is not None


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Read the command and its options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="jobcompass-extraction"
    )
    commands: argparse._SubParsersAction = parser.add_subparsers(
        dest="command", required=True
    )
    run: argparse.ArgumentParser = commands.add_parser(
        "run", help="extract a site: job infos, then job details"
    )
    run.add_argument("site", help="section name in sites.toml, e.g. jobup")
    run.add_argument("--max-pages", type=int, help="result pages per category")
    run.add_argument("--max-jobs", type=int, help="detail pages to download")
    run.add_argument("--full", action="store_true", help="no limit (real run)")
    args: argparse.Namespace = parser.parse_args(argv)
    if args.full and (args.max_pages is not None or args.max_jobs is not None):
        parser.error("--full cannot be combined with --max-pages or --max-jobs")
    return args


def resolve_limits(args: argparse.Namespace, site: SiteConfig) -> RunLimits:
    """--full: no limit; otherwise the options, or the limits of sites.toml."""
    if args.full:
        return RunLimits(max_pages=None, max_jobs=None)
    return RunLimits(
        max_pages=args.max_pages if args.max_pages is not None else site.max_pages,
        max_jobs=args.max_jobs if args.max_jobs is not None else site.max_jobs,
    )


def build_extraction(
    name: str, site: SiteConfig, limits: RunLimits, settings: ExtractionSettings
) -> SiteExtraction:
    """The use case of a site, with the classes and settings of sites.toml."""
    get_page: GetPage = make_get_page(
        settings.user_agent, settings.http_timeout, site.min_delay_between_requests
    )
    now: partial[datetime] = partial(datetime.now, UTC)
    common: dict[str, object] = {
        "get_page": get_page,
        "source": name,
        "is_test": limits.is_test,
        "now": now,
    }
    storage_class: type[IStorage] = import_class(site.storage, IStorage)
    return SiteExtraction(
        source=name,
        job_infos=import_class(site.job_infos, IJobInfosExtractor)(**common),
        job_details=import_class(site.job_details, IJobDetailsExtractor)(**common),
        storage=storage_class(is_test=limits.is_test, **site.storage_options),
        categories=site.categories,
        max_pages=limits.max_pages,
        max_jobs=limits.max_jobs,
        max_failures=settings.max_failures,
        batch_size=settings.batch_size,
        now=now,
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
    sites: dict[str, SiteConfig] = load_sites_config(settings.sites_file)
    if args.site not in sites:
        raise ConfigError(f"unknown site '{args.site}', known: {sorted(sites)}")
    site: SiteConfig = sites[args.site]
    extraction: SiteExtraction = build_extraction(
        args.site, site, resolve_limits(args, site), settings
    )
    report: ExtractionReport = extraction.execute()
    print(json.dumps(dataclasses.asdict(report), default=to_json))
    return 0 if report.status == RunStatus.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
