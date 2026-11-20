"""
extraction_config.py

Description : lecture de la configuration d'un site (extraction/<site>/site.toml).
Règles      : SiteConfigReader.load_site("jobup") -> SiteConfig ; l'appelant ne
              donne que le nom du site.
              N'importe que la brique d'extraction : la commande d'extraction
              s'installe sans la normalisation.
              SiteConfig et ExtractionSection : des données, aucune logique.
              Un site déclare ses deux stockages : [db_storage] et [file_storage].
"""

from typing import Annotated, Any

from pydantic import BaseModel, Field

from entrypoints.config.config_reader import (
    FROZEN,
    ConfigReader,
    DbStorageSection,
    FileStorageSection,
    ImportedClass,
)
from extraction.interfaces.i_site_extraction_uc import ISiteExtractionUseCase


class ExtractionSection(BaseModel):
    """The [extraction] section of a site.toml."""

    model_config = FROZEN

    use_case: Annotated[type[ISiteExtractionUseCase], ImportedClass] = Field(
        alias="class"
    )
    min_delay_between_requests: float = Field(ge=0)
    max_pages: int = Field(ge=1, description="Test limit: result pages per category")
    max_jobs: int = Field(ge=1, description="Test limit: detail pages downloaded")
    options: dict[str, Any] = Field(
        default_factory=dict, description="Site's own settings, checked by the site"
    )


class SiteConfig(BaseModel):
    """A site.toml: its two storages, then the [extraction] section."""

    model_config = FROZEN

    db_storage: DbStorageSection
    file_storage: FileStorageSection
    extraction: ExtractionSection


class SiteConfigReader(ConfigReader):
    """Reads the site.toml of a site."""

    _SITES: str = "extraction"  # package of the sites, one folder each
    _SITE_FILE: str = "site.toml"

    @classmethod
    def load_site(cls, site: str) -> SiteConfig:
        """The configuration of a site (its folder name, e.g. 'jobup')."""
        return cls._load(SiteConfig, cls._folder_file(cls._SITES, site, cls._SITE_FILE))
