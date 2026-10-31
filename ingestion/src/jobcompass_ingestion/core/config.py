"""
config.py

Description : settings of the ingestion brick.
Rules       : read from environment variables prefixed INGESTION_ (or a .env file),
              default values otherwise.
              Values are validated at startup: a wrong setting stops the brick
              before any request is sent.
              MAX_FETCH_FAILURES = failed attempts before an URL is set aside.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INGESTION_", env_file=".env", extra="ignore"
    )

    max_fetch_failures: int = Field(default=3, ge=1)
    fetch_max_concurrency: int = Field(default=4, ge=1)
    fetch_batch_size: int = Field(default=50, ge=1)
    scraper_version: str = "0.1.0"
    log_level: str = "INFO"
