"""
test_tables.py

Description : tests du catalogue des tables.
Règles      : chaque nom de table est unique et en snake_case (c'est aussi le nom de
              son dossier dans le stockage).
"""

import re

from catalog.tables import Table


def test_table_names_are_unique_snake_case() -> None:
    """Every table name is unique and usable as a folder name."""
    names: list[str] = [str(table) for table in Table]
    assert len(names) == len(set(names))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in names)
