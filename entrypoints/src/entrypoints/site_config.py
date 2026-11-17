"""
site_config.py

Description : lecture du site.toml d'un site, et import des classes qu'il désigne.
Règles      : un site = un dossier extraction/<site>/ contenant son site.toml ; le nom
              du site est le nom du dossier. Ajouter un site ne touche aucun fichier
              partagé.
              site.toml : la partie commune (storage, storage_options) en tête, puis
              une section par brique ([extraction], plus tard [normalization]).
              [extraction.options] est propre au site : lue et validée par la classe
              du site, jamais ici.
              Tout est validé au démarrage, classes comprises (importables et
              conformes à leur interface) : un réglage faux arrête tout avant la
              moindre requête.
"""

import importlib
import importlib.resources
import tomllib
from importlib.resources.abc import Traversable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SITES_PACKAGE: str = "extraction"  # the sites are sub-packages of extraction
SITE_FILE: str = "site.toml"


class ConfigError(Exception):
    """site.toml is wrong or missing: unknown site, class not found or not conform."""


class ExtractionSection(BaseModel):
    """The [extraction] section of a site.toml."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    class_path: str = Field(alias="class", description="module:Class, ISiteExtraction")
    min_delay_between_requests: float = Field(ge=0)
    max_pages: int = Field(ge=1, description="Test limit: result pages per category")
    max_jobs: int = Field(ge=1, description="Test limit: detail pages downloaded")
    options: dict[str, Any] = Field(
        default_factory=dict, description="Site's own settings, checked by the site"
    )


class SiteConfig(BaseModel):
    """A site.toml: what is shared by every brick, then one section per brick."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    storage: str = Field(description="module:Class, IStorage")
    storage_options: dict[str, Any] = Field(default_factory=dict)
    extraction: ExtractionSection


def load_site_config(site: str) -> SiteConfig:
    """Read and validate the site.toml of a site."""
    path: Traversable = _site_folder(site) / SITE_FILE
    if not path.is_file():
        raise ConfigError(f"no {SITE_FILE} for site '{site}', known: {known_sites()}")
    with path.open("rb") as file:
        raw: dict[str, Any] = tomllib.load(file)
    return SiteConfig(**raw)


def known_sites() -> list[str]:
    """Names of the sites that have a site.toml."""
    root: Traversable = importlib.resources.files(SITES_PACKAGE)
    return sorted(
        folder.name
        for folder in root.iterdir()
        if folder.is_dir() and (folder / SITE_FILE).is_file()
    )


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


def _site_folder(site: str) -> Traversable:
    """The folder of a site, inside the sites package."""
    if not site.isidentifier():
        raise ConfigError(f"invalid site name '{site}', known: {known_sites()}")
    return importlib.resources.files(SITES_PACKAGE) / site
