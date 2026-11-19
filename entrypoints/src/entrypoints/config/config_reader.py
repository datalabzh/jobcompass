"""
config_reader.py

Description : ce que partagent les lectures de configuration (fichiers TOML) des
              commandes : lecture et validation d'un fichier, import des classes
              désignées.
Règles      : chaque commande a son propre lecteur (extraction_config,
              normalization_config), qui hérite de ConfigReader : une commande
              n'importe que sa brique.
              Un dossier = un site ou un normaliseur : en ajouter un ne touche
              aucun fichier partagé.
              Les classes désignées dans un TOML ("module:Classe") sont importées à
              la lecture (ImportedClass) et vérifiées contre leur interface : les
              configurations renvoyées contiennent directement des classes.
              Tout est validé au chargement : fichier absent, nom inconnu, réglage
              faux ou classe introuvable lèvent ConfigError, avant toute requête et
              toute écriture.
              Un stockage se décrit par une section : class + options
              (DbStorageSection, FileStorageSection), partagée par les commandes.
"""

import importlib
import importlib.resources
import tomllib
from importlib.resources.abc import Traversable
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from storage.interfaces.i_db_storage import IDbStorage
from storage.interfaces.i_file_storage import IFileStorage


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


ImportedClass = BeforeValidator(_import_class)  # "module:Class" -> the class
FROZEN = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class DbStorageSection(BaseModel):
    """A [db_storage] section: the table storage class and its options."""

    model_config = FROZEN

    storage_class: Annotated[type[IDbStorage], ImportedClass] = Field(alias="class")
    options: dict[str, Any] = Field(default_factory=dict)


class FileStorageSection(BaseModel):
    """A [file_storage] section: the raw file storage class and its options."""

    model_config = FROZEN

    storage_class: Annotated[type[IFileStorage], ImportedClass] = Field(alias="class")
    options: dict[str, Any] = Field(default_factory=dict)


class ConfigReader:
    """Reads and validates TOML files; parent of the readers of each command."""

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
