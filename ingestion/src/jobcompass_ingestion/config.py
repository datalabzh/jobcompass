"""
config.py

Description : settings of the ingestion brick.
Rules       : read from environment variables prefixed INGESTION_ (or a .env file),
              default values otherwise.
              Validated at startup: a wrong setting stops the brick before any
              request is sent.
              data_dir = root folder of all ingestion datasets.
              max_fetch_failures = failed attempts before an URL is set aside.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INGESTION_", env_file=".env", extra="ignore"
    )

    data_dir: Path = Path("data")
    max_fetch_failures: int = Field(default=3, ge=1)
    fetch_max_concurrency: int = Field(default=4, ge=1)
    fetch_batch_size: int = Field(default=50, ge=1)
    scraper_version: str = "0.1.0"
    log_level: str = "INFO"
