"""
test_config.py

Description : tests de la lecture des configurations (Config).
Règles      : les fichiers versionnés (site.toml de jobup, normalization.toml,
              normalizer.toml de fake) sont valides et leurs classes sont importées ;
              un nom inconnu est refusé avec la liste des noms connus ; une classe
              introuvable ou non conforme à son interface, ou une limite de test
              absente, est refusée.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from entrypoints.config import (
    Config,
    ConfigError,
    NormalizationConfig,
    NormalizerConfig,
    SiteConfig,
)
from extraction.jobup.jobup_extraction import JobupExtraction
from normalization.fake.fake_normalization import FakeNormalization
from storage import LocalParquetStorage

EXTRACTION: dict[str, Any] = {
    "class": "extraction.jobup.jobup_extraction:JobupExtraction",
    "min_delay_between_requests": 1.0,
    "max_pages": 1,
    "max_jobs": 2,
}
STORAGE: str = "storage:LocalParquetStorage"


def test_jobup_site() -> None:
    """jobup's site.toml loads, with its classes already imported."""
    jobup: SiteConfig = Config.load_site("jobup")
    assert jobup.storage is LocalParquetStorage
    assert jobup.extraction.use_case is JobupExtraction
    assert (jobup.extraction.max_pages, jobup.extraction.max_jobs) == (1, 2)
    assert jobup.extraction.options["categories"]


def test_normalization_and_default_normalizer() -> None:
    """The common file names a default normalizer, whose file loads."""
    common: NormalizationConfig = Config.load_normalization()
    assert common.storage is LocalParquetStorage
    fake: NormalizerConfig = Config.load_normalizer(common.default)
    assert fake.use_case is FakeNormalization


def test_unknown_names_refused() -> None:
    """An unknown site or normalizer is refused, with the known names."""
    with pytest.raises(ConfigError, match="known: \\['jobup'"):
        Config.load_site("nowhere")
    with pytest.raises(ConfigError, match="known: \\['fake'"):
        Config.load_normalizer("../fake")


def test_unknown_class_refused() -> None:
    """A class that cannot be imported is refused."""
    with pytest.raises(ValidationError, match="class not found"):
        SiteConfig(storage="storage:Nowhere", extraction=EXTRACTION)


def test_class_with_wrong_interface_refused() -> None:
    """A class that does not implement the expected interface is refused."""
    with pytest.raises(ValidationError, match="IStorage"):
        SiteConfig(
            storage="extraction.jobup.jobup_extraction:JobupExtraction",
            extraction=EXTRACTION,
        )


def test_test_limits_required() -> None:
    """A site without max_jobs is refused (safety net of the test runs)."""
    section: dict[str, Any] = {k: v for k, v in EXTRACTION.items() if k != "max_jobs"}
    with pytest.raises(ValidationError, match="max_jobs"):
        SiteConfig(storage=STORAGE, extraction=section)
