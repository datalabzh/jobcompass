"""
__init__.py

Description : implémentations du stockage partagé par les briques JobCompass
              (l'interface IStorage est dans interfaces).
Règles      : les briques importent uniquement d'ici (from storage import ...),
              jamais depuis les modules : l'organisation interne peut changer
              librement.
"""

from storage.local_parquet_storage import LocalParquetStorage

__all__ = ["LocalParquetStorage"]
