"""
test_extraction_config.py

Description : tests de la lecture de la configuration d'un site (SiteConfigReader).
Règles      : le site.toml versionné de jobup est valide et ses classes sont
              importées ; un site inconnu est refusé avec la liste des sites
              connus ; une classe introuvable ou non conforme à son interface, ou
              une limite de test absente, est refusée.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from entrypoints.config.config_reader import ConfigError
from entrypoints.config.extraction_config import SiteConfig, SiteConfigReader
from extraction.jobup.jobup_extraction_uc import JobupExtractionUseCase
from storage.postgres_db_storage import PostgresDbStorage
from storage.s3_file_storage import S3FileStorage

EXTRACTION: dict[str, Any] = {
    "class": "extraction.jobup.jobup_extraction_uc:JobupExtractionUseCase",
    "min_delay_between_requests": 1.0,
    "max_pages": 1,
    "max_jobs": 2,
}
DB_STORAGE: dict[str, Any] = {"class": "storage.postgres_db_storage:PostgresDbStorage"}
FILE_STORAGE: dict[str, Any] = {"class": "storage.s3_file_storage:S3FileStorage"}


def test_jobup_site() -> None:
    """jobup's site.toml loads, with its classes already imported."""
    jobup: SiteConfig = SiteConfigReader.load_site("jobup")
    assert jobup.db_storage.storage_class is PostgresDbStorage
    assert jobup.file_storage.storage_class is S3FileStorage
    assert jobup.extraction.use_case is JobupExtractionUseCase
    assert (jobup.extraction.max_pages, jobup.extraction.max_jobs) == (1, 2)
    assert jobup.extraction.options["categories"]


def test_unknown_site_refused() -> None:
    """An unknown site is refused, with the known names."""
    with pytest.raises(ConfigError, match="known: \\['jobup'"):
        SiteConfigReader.load_site("nowhere")


def test_unknown_class_refused() -> None:
    """A class that cannot be imported is refused."""
    with pytest.raises(ValidationError, match="class not found"):
        SiteConfig(
            db_storage={"class": "storage:Nowhere"},
            file_storage=FILE_STORAGE,
            extraction=EXTRACTION,
        )


def test_class_with_wrong_interface_refused() -> None:
    """A class that does not implement the expected interface is refused."""
    with pytest.raises(ValidationError, match="IFileStorage"):
        SiteConfig(
            db_storage=DB_STORAGE,
            file_storage={"class": DB_STORAGE["class"]},
            extraction=EXTRACTION,
        )


def test_test_limits_required() -> None:
    """A site without max_jobs is refused (safety net of the test runs)."""
    section: dict[str, Any] = {k: v for k, v in EXTRACTION.items() if k != "max_jobs"}
    with pytest.raises(ValidationError, match="max_jobs"):
        SiteConfig(db_storage=DB_STORAGE, file_storage=FILE_STORAGE, extraction=section)
