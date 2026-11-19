"""
i_db_storage.py

Description : ce que doit fournir tout stockage de tables : ajouter et lire des
              enregistrements de contrats.
Règles      : partagé par toutes les briques : le stockage ne connaît aucune table
              en particulier. Une table est un nom (ex. 'raw_job_info') ; chaque
              brique tient la liste de ses tables.
              Les tables sont en ajout seul : une ligne écrite n'est jamais modifiée.
              Une table contient les enregistrements d'un seul contrat ; read renvoie
              les lignes d'une source, sous forme de dictionnaires (nom de colonne ->
              valeur), toutes les colonnes ou seulement celles demandées.
              is_test : un stockage de test écrit et lit dans une zone à part ; les
              données de test et les vraies ne se croisent jamais.
              Création : Classe(is_test=..., **options de la configuration).
              Aucune règle métier ici : un stockage ne fait que stocker et lire.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from contracts import ContractModel


class IDbStorage(ABC):
    """Stores and reads tables of contract records."""

    def __init__(self, is_test: bool) -> None:
        self.is_test: bool = is_test

    @abstractmethod
    def append(self, table: str, records: Sequence[ContractModel]) -> None:
        """Add records of one contract to a table (nothing if there is none)."""

    @abstractmethod
    def read(
        self, table: str, source: str, columns: Sequence[str] | None = None
    ) -> list[dict[str, Any]]:
        """Lines of a table for a source, all columns or only the ones named."""
