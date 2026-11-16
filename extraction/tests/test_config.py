"""
test_config.py

Description : tests des réglages de l'extraction et de sites.toml.
Règles      : les valeurs par défaut s'appliquent sans variable d'environnement ;
              le sites.toml versionné est valide et ses classes s'importent ; un
              site sans catégorie ou sans limite de test est rejeté ; une classe
              introuvable ou non conforme à son interface est une ConfigError.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from extraction.config import (
    DEFAULT_SITES_FILE,
    ConfigError,
    ExtractionSettings,
    SiteConfig,
    import_class,
    load_sites_config,
)
from extraction.interfaces.i_job_details_extractor import IJobDetailsExtractor
from extraction.interfaces.i_job_infos_extractor import IJobInfosExtractor
from extraction.interfaces.i_storage import IStorage
from extraction.jobup.jobup_job_infos import JobupJobInfos

JOBUP: str = """
[jobup]
job_infos = "a:B"
job_details = "a:C"
storage = "a:D"
categories = ["it"]
min_delay_between_requests = 1.0
"""


def test_default_settings() -> None:
    """Without environment variables, the documented defaults apply."""
    settings: ExtractionSettings = ExtractionSettings(_env_file=None)
    assert settings.max_failures == 3
    assert settings.sites_file == DEFAULT_SITES_FILE


def test_versioned_sites_file_is_valid() -> None:
    """sites.toml loads; jobup has a delay, test limits and importable classes."""
    jobup: SiteConfig = load_sites_config(DEFAULT_SITES_FILE)["jobup"]
    assert jobup.min_delay_between_requests >= 1.0
    assert (jobup.max_pages, jobup.max_jobs) == (1, 2)
    assert import_class(jobup.job_infos, IJobInfosExtractor) is JobupJobInfos
    import_class(jobup.job_details, IJobDetailsExtractor)
    import_class(jobup.storage, IStorage)


def test_test_limits_required(tmp_path: Path) -> None:
    """A site without max_pages / max_jobs stops the program (safety net)."""
    path: Path = tmp_path / "sites.toml"
    path.write_text(JOBUP)
    with pytest.raises(ValidationError, match="max_pages"):
        load_sites_config(path)


def test_site_without_category_rejected(tmp_path: Path) -> None:
    """A site with an empty category list stops the program."""
    path: Path = tmp_path / "sites.toml"
    path.write_text(
        JOBUP.replace('["it"]', "[]") + "max_pages = 1\nmax_jobs = 2\n"
    )
    with pytest.raises(ValidationError):
        load_sites_config(path)


def test_unknown_class_rejected() -> None:
    """A class that cannot be imported is a ConfigError."""
    with pytest.raises(ConfigError, match="not found"):
        import_class("extraction.jobup.nowhere:Nothing", IStorage)


def test_class_with_wrong_interface_rejected() -> None:
    """A class that does not implement the expected interface is a ConfigError."""
    with pytest.raises(ConfigError, match="IStorage"):
        import_class("extraction.jobup.jobup_job_infos:JobupJobInfos", IStorage)
