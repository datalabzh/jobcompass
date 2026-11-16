"""
__init__.py

Description : API publique du stockage partagé par les briques JobCompass.
Règles      : les briques importent uniquement d'ici (from storage import ...),
              jamais depuis les modules : l'organisation interne peut changer
              librement.
"""

from storage.i_storage import IStorage
from storage.local_parquet_storage import LocalParquetStorage

__all__ = ["IStorage", "LocalParquetStorage"]
