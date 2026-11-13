"""
config.py

Description : settings of the ingestion brick, and the per-site scope file.
Rules       : IngestionSettings: environment variables prefixed INGESTION_ (or a
              .env file), default values otherwise.
              scrapers.toml: per site, the categories to read and the politeness
              delay; versioned in Git, so a change of scope goes through review.
              Both are validated at startup: a wrong setting stops the brick before
              any request is sent.
              user_agent identifies JobCompass to the sites: set a contact in it.
              max_failures = failed downloads before a job is set aside.
"""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SCRAPERS_FILE: Path = Path(__file__).resolve().parents[2] / "scrapers.toml"


class IngestionSettings(BaseSettings):
    """Settings of the ingestion brick, from INGESTION_* variables or defaults."""

    model_config = SettingsConfigDict(
        env_prefix="INGESTION_", env_file=".env", extra="ignore"
    )

    data_dir: Path = Path("data")
    scrapers_file: Path = DEFAULT_SCRAPERS_FILE
    user_agent: str = "JobCompass/0.1 (job market research)"
    http_timeout: float = Field(default=30.0, gt=0)
    max_failures: int = Field(default=3, ge=1)
    batch_size: int = Field(default=50, ge=1)
    log_level: str = "INFO"


class ScraperConfig(BaseModel):
    """Scope of one site, as written in scrapers.toml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    categories: list[str] = Field(min_length=1)
    min_delay_between_requests: float = Field(ge=0)


def load_scrapers_config(path: Path) -> dict[str, ScraperConfig]:
    """Read and validate scrapers.toml: site name -> its scope."""
    with path.open("rb") as file:
        raw: dict[str, dict[str, object]] = tomllib.load(file)
    return {name: ScraperConfig(**values) for name, values in raw.items()}
