"""
dbt_utils.py

Description : macros dbt_utils simulées pour le templater Jinja de SQLFluff.
Règles      : chaque fonction renvoie un SQL valide de même forme que la vraie
              macro, pour que SQLFluff analyse le modèle sans dbt ni base.
              Utilisé uniquement par SQLFluff (library_path de .sqlfluff).
"""


def generate_surrogate_key(field_list: list[str]) -> str:
    """Stand-in for dbt_utils.generate_surrogate_key: an md5 of the fields."""
    fields: str = " || '-' || ".join(field_list)
    return f"md5({fields})"


def star(*_args: object, **_kwargs: object) -> str:
    """Stand-in for dbt_utils.star: every column (from=, except= ignored)."""
    return "*"
