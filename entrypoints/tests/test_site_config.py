"""
test_site_config.py

Description : tests de la lecture des site.toml et de l'import des classes.
Règles      : le site.toml versionné de jobup est valide et ses classes s'importent ;
              un site inconnu ou sans limite de test est rejeté ; une classe
              introuvable ou non conforme à son interface est une ConfigError.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from entrypoints.site_config import (
    ConfigError,
    SiteConfig,
    import_class,
    known_sites,
    load_site_config,
)
from extraction.jobup.jobup_extraction import JobupExtraction
from interfaces import ISiteExtraction, IStorage

EXTRACTION: dict[str, Any] = {
    "class": "a:B",
    "min_delay_between_requests": 1.0,
    "max_pages": 1,
    "max_jobs": 2,
}


def test_jobup_site_file_is_valid() -> None:
    """jobup's site.toml loads; its classes import and implement their interface."""
    jobup: SiteConfig = load_site_config("jobup")
    section = jobup.extraction
    assert section.min_delay_between_requests >= 1.0
    assert (section.max_pages, section.max_jobs) == (1, 2)
    assert import_class(section.class_path, ISiteExtraction) is JobupExtraction
    assert section.options["categories"]
    import_class(jobup.storage, IStorage)


def test_known_sites() -> None:
    """A site is any folder of extraction with a site.toml."""
    assert "jobup" in known_sites()


def test_unknown_site_rejected() -> None:
    """A site without site.toml is a ConfigError listing the known sites."""
    with pytest.raises(ConfigError, match="jobup"):
        load_site_config("nowhere")


def test_test_limits_required() -> None:
    """A site without max_pages / max_jobs is refused (safety net)."""
    section: dict[str, Any] = {k: v for k, v in EXTRACTION.items() if k != "max_jobs"}
    with pytest.raises(ValidationError, match="max_jobs"):
        SiteConfig(storage="a:D", extraction=section)


def test_unknown_class_rejected() -> None:
    """A class that cannot be imported is a ConfigError."""
    with pytest.raises(ConfigError, match="not found"):
        import_class("extraction.jobup.nowhere:Nothing", IStorage)


def test_class_with_wrong_interface_rejected() -> None:
    """A class that does not implement the expected interface is a ConfigError."""
    with pytest.raises(ConfigError, match="IStorage"):
        import_class("extraction.jobup.jobup_extraction:JobupExtraction", IStorage)
