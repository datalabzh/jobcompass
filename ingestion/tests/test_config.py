"""
test_config.py

Description : tests of the ingestion settings and of scrapers.toml.
Rules       : defaults apply without environment variables; the versioned
              scrapers.toml is valid; a site without category is rejected.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ingestion.config import (
    DEFAULT_SCRAPERS_FILE,
    IngestionSettings,
    ScraperConfig,
    load_scrapers_config,
)


def test_default_settings() -> None:
    """Without environment variables, the documented defaults apply."""
    settings: IngestionSettings = IngestionSettings(_env_file=None)
    assert settings.max_failures == 3
    assert settings.scrapers_file == DEFAULT_SCRAPERS_FILE


def test_versioned_scrapers_file_is_valid() -> None:
    """The scrapers.toml of the repo loads, with jobup and its delay."""
    config: dict[str, ScraperConfig] = load_scrapers_config(DEFAULT_SCRAPERS_FILE)
    assert "informatique-telecommunications" in config["jobup"].categories
    assert config["jobup"].min_delay_between_requests >= 1.0


def test_site_without_category_rejected(tmp_path: Path) -> None:
    """A site with an empty category list stops the program."""
    path: Path = tmp_path / "scrapers.toml"
    path.write_text("[jobup]\ncategories = []\nmin_delay_between_requests = 1.0\n")
    with pytest.raises(ValidationError):
        load_scrapers_config(path)
