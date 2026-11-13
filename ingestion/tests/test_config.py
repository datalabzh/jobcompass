"""
test_config.py

Description : tests of the ingestion settings.
Rules       : default values apply when no environment variable is set.
"""

from jobcompass_ingestion.config import IngestionSettings


def test_default_settings():
    settings = IngestionSettings(_env_file=None)
    assert settings.max_fetch_failures == 3
    assert str(settings.data_dir) == "data"
