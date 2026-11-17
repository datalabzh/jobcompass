"""
__init__.py

Description : API publique du catalogue des tables de JobCompass.
Règles      : on importe uniquement d'ici (from catalog import Table).
"""

from catalog.tables import Table

__all__ = ["Table"]
