"""
normalization_config.py

Description : lecture des configurations de la normalisation : la commune
              (normalization/normalization.toml) et celle d'un normaliseur
              (normalization/<normaliseur>/normalizer.toml).
Règles      : NormalizationConfigReader.load_normalization()      -> commune
              NormalizationConfigReader.load_normalizer("fake")   -> un normaliseur
              N'importe que la brique de normalisation : la commande de
              normalisation s'installe sans l'extraction.
              NormalizationConfig et NormalizerConfig : des données, aucune logique.
"""

import importlib.resources
from importlib.resources.abc import Traversable
from typing import Annotated, Any

from pydantic import BaseModel, Field

from entrypoints.config_reader import FROZEN, ConfigReader, ImportedClass
from interfaces import IStorage
from normalization.interfaces import INormalization


class NormalizationConfig(BaseModel):
    """normalization.toml: what every normalizer shares."""

    model_config = FROZEN

    storage: Annotated[type[IStorage], ImportedClass]
    storage_options: dict[str, Any] = Field(default_factory=dict)
    default: str = Field(description="Normalizer used without --normalizer")


class NormalizerConfig(BaseModel):
    """A normalizer.toml: the class and the settings of one normalizer."""

    model_config = FROZEN

    use_case: Annotated[type[INormalization], ImportedClass] = Field(alias="class")
    max_jobs: int = Field(ge=1, description="Test limit: jobs normalized per run")


class NormalizationConfigReader(ConfigReader):
    """Reads the common normalization.toml and the normalizer.toml files."""

    _NORMALIZATION: str = "normalization"  # package of the normalizers
    _NORMALIZATION_FILE: str = "normalization.toml"
    _NORMALIZER_FILE: str = "normalizer.toml"

    @classmethod
    def load_normalization(cls) -> NormalizationConfig:
        """The configuration shared by every normalizer."""
        root: Traversable = importlib.resources.files(cls._NORMALIZATION)
        return cls._load(NormalizationConfig, root / cls._NORMALIZATION_FILE)

    @classmethod
    def load_normalizer(cls, normalizer: str) -> NormalizerConfig:
        """The configuration of a normalizer (its folder name, e.g. 'fake')."""
        path: Traversable = cls._folder_file(
            cls._NORMALIZATION, normalizer, cls._NORMALIZER_FILE
        )
        return cls._load(NormalizerConfig, path)
