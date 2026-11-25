"""
settings.py

Description : réglages communs à l'extraction de tous les sites (user agent,
              timeout, échecs tolérés, niveau de log), lus par la commande
              d'extraction.
Règles      : variables EXTRACTION_*, ou fichier extraction/.env (non versionné,
              modèle : extraction/.env.example) ; une variable définie l'emporte
              sur le fichier, et à défaut des deux, les valeurs ci-dessous.
              Chemin du fichier déduit de l'emplacement de ce module : il ne dépend
              pas du dossier d'où l'on lance la commande.
              Les réglages propres à un site restent dans son site.toml.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# extraction/src/extraction/settings.py -> extraction/.env
EXTRACTION_ENV_FILE: Path = Path(__file__).resolve().parents[2] / ".env"


class ExtractionSettings(BaseSettings):
    """Settings common to every site, from EXTRACTION_* variables or defaults."""

    model_config = SettingsConfigDict(
        env_prefix="EXTRACTION_", env_file=EXTRACTION_ENV_FILE, extra="ignore"
    )

    user_agent: str = "JobCompass/0.1 (job market research)"
    http_timeout: float = Field(default=30.0, gt=0)
    max_failures: int = Field(default=3, ge=1)
    log_level: str = "INFO"
