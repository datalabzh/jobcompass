"""
config.py

Description : réglages de la brique extraction, et lecture de sites.toml.
Règles      : ExtractionSettings : variables d'environnement préfixées EXTRACTION_
              (ou fichier .env), valeurs par défaut sinon ; communes à tous les sites.
              sites.toml : par site, les classes à utiliser (job infos, job details,
              stockage), son périmètre et ses limites de test ; versionné dans Git,
              donc tout changement passe en revue.
              Tout est validé au démarrage, classes comprises (importables et
              conformes à leur interface) : un réglage faux arrête la brique avant
              toute requête.
              user_agent identifie JobCompass auprès des sites : y mettre un contact.
              max_failures = téléchargements échoués avant qu'un job soit mis de côté.
"""

import importlib
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SITES_FILE: Path = Path(__file__).resolve().parents[2] / "sites.toml"


class ConfigError(Exception):
    """sites.toml is wrong: unknown site, class not found or not conform."""


class ExtractionSettings(BaseSettings):
    """Settings common to every site, from EXTRACTION_* variables or defaults."""

    model_config = SettingsConfigDict(
        env_prefix="EXTRACTION_", env_file=".env", extra="ignore"
    )

    sites_file: Path = DEFAULT_SITES_FILE
    user_agent: str = "JobCompass/0.1 (job market research)"
    http_timeout: float = Field(default=30.0, gt=0)
    max_failures: int = Field(default=3, ge=1)
    batch_size: int = Field(default=50, ge=1)
    log_level: str = "INFO"


class SiteConfig(BaseModel):
    """One site, as written in sites.toml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_infos: str = Field(description="module:Class of the job infos extractor")
    job_details: str = Field(description="module:Class of the job details extractor")
    storage: str = Field(description="module:Class of the storage")
    storage_options: dict[str, Any] = Field(default_factory=dict)
    categories: list[str] = Field(min_length=1)
    min_delay_between_requests: float = Field(ge=0)
    max_pages: int = Field(ge=1, description="Test limit: result pages per category")
    max_jobs: int = Field(ge=1, description="Test limit: detail pages downloaded")


def load_sites_config(path: Path) -> dict[str, SiteConfig]:
    """Read and validate sites.toml: site name -> its configuration."""
    with path.open("rb") as file:
        raw: dict[str, dict[str, Any]] = tomllib.load(file)
    return {name: SiteConfig(**values) for name, values in raw.items()}


def import_class[T](path: str, interface: type[T]) -> type[T]:
    """The class named 'module:Class', checked to implement the interface."""
    module_name, _, class_name = path.partition(":")
    try:
        found: object = getattr(importlib.import_module(module_name), class_name)
    except (ImportError, AttributeError, ValueError) as error:
        raise ConfigError(f"class not found: '{path}' ({error})") from error
    if not (isinstance(found, type) and issubclass(found, interface)):
        raise ConfigError(f"'{path}' does not implement {interface.__name__}")
    return found
