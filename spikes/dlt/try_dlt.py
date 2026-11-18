"""
try_dlt.py

Description : spike dlt, test 1 : charger des ExtractedJob dans des fichiers
              Parquet locaux avec dlt, le contrat Pydantic servant de schéma.
Règles      : jetable : n'est importé par aucune brique et ne touche pas data/.
              Toute la configuration est passée dans le code (aucun dossier .dlt/,
              télémétrie de dlt désactivée).
              Pages lues : la fiche enregistrée (fixture) et le HTML déjà présent
              dans data/test/raw_job_detail_html/ ; aucun accès réseau.
              Sortie : spikes/dlt/output/ (ignoré par git), effacée à chaque
              lancement.
"""

import os
import shutil
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

os.environ["RUNTIME__DLTHUB_TELEMETRY"] = "false"  # before importing dlt

import dlt  # noqa: E402
import duckdb  # noqa: E402
from contracts import ExtractedJob, compute_raw_hash  # noqa: E402
from extraction.jobup.jobup_parser import JobupJobDetail, JobupParser  # noqa: E402
from interfaces import ParsingError  # noqa: E402

SPIKE_DIR: Path = Path(__file__).resolve().parent
REPO_DIR: Path = SPIKE_DIR.parents[1]
OUTPUT_DIR: Path = SPIKE_DIR / "output"
DATA_DIR: Path = OUTPUT_DIR / "data"  # what will become data/
PIPELINES_DIR: Path = OUTPUT_DIR / "pipelines"  # dlt working folder
HTML_FILES: list[Path] = [
    REPO_DIR
    / "extraction/src/extraction/jobup/tests/fixtures/jobup_detail_page.html",
    *sorted((REPO_DIR / "data/test/raw_job_detail_html").glob("*.html")),
]
SOURCE: str = "jobup"


def extracted_jobs() -> Iterator[ExtractedJob]:
    """Parse every HTML file and yield one ExtractedJob per readable page."""
    parser: JobupParser = JobupParser()
    for path in HTML_FILES:
        content: bytes = path.read_bytes()
        try:
            detail: JobupJobDetail = parser.parse("job_detail", content)
        except ParsingError as error:
            print(f"  skipped {path.name}: {error}")
            continue
        yield ExtractedJob(
            source=SOURCE,
            is_test=True,
            url=f"https://www.jobup.ch/fr/emplois/detail/spike-{path.stem[:8]}/",
            raw_hash=compute_raw_hash(content),
            parser=parser.name,
            parser_version=parser.version,
            parsed_at=datetime.now(UTC),
            title=detail.title,
            company=detail.company,
            description=detail.description,
            date_posted=detail.date_posted,
            postal_code=detail.postal_code,
            employment_types=detail.employment_types,
            categories=detail.categories,
            declared_skills=detail.declared_skills,
        )


def load() -> None:
    """Load the extracted jobs with dlt into local Parquet files."""
    pipeline: dlt.Pipeline = dlt.pipeline(
        pipeline_name=SOURCE,
        pipelines_dir=str(PIPELINES_DIR),
        destination=dlt.destinations.filesystem(bucket_url=DATA_DIR.as_uri()),
        dataset_name=SOURCE,
    )
    resource: dlt.sources.DltResource = dlt.resource(
        extracted_jobs(),
        name="extracted_job",
        columns=ExtractedJob,
        write_disposition="append",
    )
    print(pipeline.run(resource, loader_file_format="parquet"))


def show_files() -> None:
    """Print every file written under the output folder."""
    for path in sorted(OUTPUT_DIR.rglob("*")):
        if path.is_file():
            print(f"  {path.relative_to(OUTPUT_DIR)}  ({path.stat().st_size} B)")


def show_table() -> None:
    """Read the extracted_job table back with DuckDB: its columns and rows."""
    files: str = str(DATA_DIR / SOURCE / "extracted_job" / "*.parquet")
    print(duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{files}')"))
    print(
        duckdb.sql(
            "SELECT title, company, declared_skills, _dlt_load_id, _dlt_id "
            f"FROM read_parquet('{files}')"
        )
    )


def show_hidden_dlt_folders() -> None:
    """Report whether dlt wrote anything outside the output folder."""
    for folder in (Path.cwd() / ".dlt", Path.home() / ".dlt"):
        print(f"  {folder}: {'exists' if folder.exists() else 'absent'}")


def main() -> None:
    """Run test 1 from a clean output folder and show what dlt produced."""
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    print("== load")
    load()
    print("== files written")
    show_files()
    print("== table read back with DuckDB")
    show_table()
    print("== dlt folders outside the output folder")
    show_hidden_dlt_folders()


if __name__ == "__main__":
    main()
