"""
config.py

Description : lecture des configurations de JobCompass (fichiers TOML) : celle d'un
              site, la commune de la normalisation, celle d'un normaliseur.
Règles      : une seule classe, Config, et trois points d'entrée :
                Config.load_site("jobup")        extraction/jobup/site.toml
                Config.load_normalization()      normalization/normalization.toml
                Config.load_normalizer("fake")   normalization/fake/normalizer.toml
              L'appelant ne donne que le nom du site ou du normaliseur : où sont les
              fichiers, comment les lire et les vérifier est la popote interne de
              Config.
              Un dossier = un site ou un normaliseur : en ajouter un ne touche
              aucun fichier partagé.
              Les classes désignées dans un TOML ("module:Classe") sont importées à
              la lecture et vérifiées contre leur interface : les configurations
              renvoyées contiennent directement des classes.
              Tout est validé au chargement : fichier absent, nom inconnu, réglage
              faux ou classe introuvable lèvent ConfigError, avant toute requête et
              toute écriture.
              SiteConfig, NormalizationConfig, NormalizerConfig : ce que renvoie
              Config (des données, aucune logique).
"""

import importlib
import importlib.resources
import tomllib
from importlib.resources.abc import Traversable
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from interfaces import INormalization, ISiteExtraction, IStorage


class ConfigError(Exception):
    """A configuration is missing or wrong: unknown name, bad value, bad class."""


def _import_class(path: object) -> object:
    """The class named 'module:Class'; other values are left to the validation."""
    if not isinstance(path, str):
        return path
    module_name, _, class_name = path.partition(":")
    try:
        return getattr(importlib.import_module(module_name), class_name)
    except (ImportError, AttributeError, ValueError) as error:
        raise ValueError(f"class not found: '{path}' ({error})") from error


_ImportedClass = BeforeValidator(_import_class)  # "module:Class" -> the class
_FROZEN = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


# --- what Config returns --------------------------------------------------------


class ExtractionSection(BaseModel):
    """The [extraction] section of a site.toml."""

    model_config = _FROZEN

    use_case: Annotated[type[ISiteExtraction], _ImportedClass] = Field(alias="class")
    min_delay_between_requests: float = Field(ge=0)
    max_pages: int = Field(ge=1, description="Test limit: result pages per category")
    max_jobs: int = Field(ge=1, description="Test limit: detail pages downloaded")
    options: dict[str, Any] = Field(
        default_factory=dict, description="Site's own settings, checked by the site"
    )


class SiteConfig(BaseModel):
    """A site.toml: the storage, then the [extraction] section."""

    model_config = _FROZEN

    storage: Annotated[type[IStorage], _ImportedClass]
    storage_options: dict[str, Any] = Field(default_factory=dict)
    extraction: ExtractionSection


class NormalizationConfig(BaseModel):
    """normalization.toml: what every normalizer shares."""

    model_config = _FROZEN

    storage: Annotated[type[IStorage], _ImportedClass]
    storage_options: dict[str, Any] = Field(default_factory=dict)
    default: str = Field(description="Normalizer used without --normalizer")


class NormalizerConfig(BaseModel):
    """A normalizer.toml: the class and the settings of one normalizer."""

    model_config = _FROZEN

    use_case: Annotated[type[INormalization], _ImportedClass] = Field(alias="class")
    max_jobs: int = Field(ge=1, description="Test limit: jobs normalized per run")


# --- reading --------------------------------------------------------------------


class Config:
    """Reads the TOML configurations of JobCompass; three entry points."""

    _SITES: str = "extraction"  # package of the sites, one folder each
    _SITE_FILE: str = "site.toml"
    _NORMALIZATION: str = "normalization"  # package of the normalizers
    _NORMALIZATION_FILE: str = "normalization.toml"
    _NORMALIZER_FILE: str = "normalizer.toml"

    @classmethod
    def load_site(cls, site: str) -> SiteConfig:
        """The configuration of a site (its folder name, e.g. 'jobup')."""
        path: Traversable = cls._folder_file(cls._SITES, site, cls._SITE_FILE)
        return cls._load(SiteConfig, path)

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

    @classmethod
    def _folder_file(cls, package: str, folder: str, file_name: str) -> Traversable:
        """The file of a folder; ConfigError, with the known names, if absent."""
        root: Traversable = importlib.resources.files(package)
        path: Traversable = root / folder / file_name
        if not folder.isidentifier() or not path.is_file():
            known: list[str] = cls._known(root, file_name)
            raise ConfigError(f"unknown name '{folder}', known: {known}")
        return path

    @classmethod
    def _known(cls, root: Traversable, file_name: str) -> list[str]:
        """The folders of a package that have the given file."""
        return sorted(
            folder.name
            for folder in root.iterdir()
            if folder.is_dir() and (folder / file_name).is_file()
        )

    @classmethod
    def _load[T: BaseModel](cls, model: type[T], path: Traversable) -> T:
        """Read a TOML file and validate it into the model; ConfigError if wrong."""
        if not path.is_file():
            raise ConfigError(f"missing configuration file: {path}")
        with path.open("rb") as file:
            raw: dict[str, Any] = tomllib.load(file)
        try:
            return model(**raw)
        except ValidationError as error:
            raise ConfigError(f"{path}: {error}") from error
