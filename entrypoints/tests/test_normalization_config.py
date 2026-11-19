"""
test_normalization_config.py

Description : tests de la lecture des configurations de la normalisation
              (NormalizationConfigReader).
Règles      : normalization.toml et le normalizer.toml de fake, versionnés, sont
              valides et leurs classes sont importées ; un normaliseur inconnu est
              refusé avec la liste des normaliseurs connus.
"""

import pytest

from entrypoints.config.config_reader import ConfigError
from entrypoints.config.normalization_config import (
    NormalizationConfig,
    NormalizationConfigReader,
    NormalizerConfig,
)
from normalization.fake.fake_normalization_uc import FakeNormalizationUseCase
from storage.postgres_db_storage import PostgresDbStorage


def test_normalization_and_default_normalizer() -> None:
    """The common file names a default normalizer, whose file loads."""
    common: NormalizationConfig = NormalizationConfigReader.load_normalization()
    assert common.db_storage.storage_class is PostgresDbStorage
    fake: NormalizerConfig = NormalizationConfigReader.load_normalizer(common.default)
    assert fake.use_case is FakeNormalizationUseCase


def test_unknown_normalizer_refused() -> None:
    """An unknown normalizer is refused, with the known names."""
    with pytest.raises(ConfigError, match="known: \\['fake'"):
        NormalizationConfigReader.load_normalizer("../fake")
