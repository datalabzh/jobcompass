"""
cli.py

Description : command line of the ingestion brick, called by hand or by Dagster.
Rules       : one command, one use case:
                extract-job-details --scraper jobup [--limit N]
              Builds what the use case needs (storage, HTTP, scraper with its scope
              from scrapers.toml), then calls execute().
              The last line printed is the JSON report of the run (read by Dagster).
              Exit code 0 when completed, 1 when any category failed.
              New site = one entry in SCRAPERS + one section in scrapers.toml.
"""

import argparse
import dataclasses
import json
import logging
import sys

from contracts import RunStatus
from ingestion.config import (
    IngestionSettings,
    ScraperConfig,
    load_scrapers_config,
)
from ingestion.http import GetPage, make_get_page
from ingestion.scrapers.i_scraper import IScraper
from ingestion.scrapers.jobup_scraper import JobupScraper
from ingestion.storage.local_parquet_storage import LocalParquetStorage
from ingestion.use_cases.extract_job_details import (
    ExtractJobDetails,
    ExtractJobDetailsReport,
)

SCRAPERS: dict[str, type[IScraper]] = {
    scraper.name: scraper for scraper in [JobupScraper]
}


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Read the command and its options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="jobcompass-ingestion"
    )
    commands: argparse._SubParsersAction = parser.add_subparsers(
        dest="command", required=True
    )
    extract: argparse.ArgumentParser = commands.add_parser(
        "extract-job-details", help="raw detail pages of the jobs of a site"
    )
    extract.add_argument("--scraper", required=True, choices=sorted(SCRAPERS))
    extract.add_argument(
        "--limit", type=int, default=None, help="max pages to download"
    )
    return parser.parse_args(argv)


def build_scraper(name: str, settings: IngestionSettings) -> IScraper:
    """The scraper of a site, with its HTTP client and its scope."""
    scope: ScraperConfig = load_scrapers_config(settings.scrapers_file)[name]
    get_page: GetPage = make_get_page(
        settings.user_agent, settings.http_timeout, scope.min_delay_between_requests
    )
    return SCRAPERS[name](get_page, scope.categories)


def main(argv: list[str] | None = None) -> int:
    """Run the command, print its JSON report; return the exit code."""
    args: argparse.Namespace = parse_args(argv)
    settings: IngestionSettings = IngestionSettings()
    logging.basicConfig(level=settings.log_level, stream=sys.stderr)
    use_case: ExtractJobDetails = ExtractJobDetails(
        scraper=build_scraper(args.scraper, settings),
        storage=LocalParquetStorage(settings.data_dir),
        max_failures=settings.max_failures,
        batch_size=settings.batch_size,
        limit=args.limit,
    )
    report: ExtractJobDetailsReport = use_case.execute()
    print(json.dumps(dataclasses.asdict(report), default=str))
    return 0 if report.status == RunStatus.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
