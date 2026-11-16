"""
i_storage.py

Description : ce que doit fournir tout stockage : ajouter et lire des tables,
              déposer et vérifier des fichiers bruts.
Règles      : partagé par toutes les briques : le stockage ne connaît aucune table
              en particulier. Une table est un nom (ex. 'job_info') ; chaque brique
              tient la liste de ses tables.
              Les tables sont en ajout seul : une ligne écrite n'est jamais modifiée.
              Une table contient les enregistrements d'un seul contrat ; read renvoie
              toutes les lignes d'une source, sous forme de dictionnaires (nom de
              colonne -> valeur).
              Les fichiers bruts sont nommés par l'appelant
              (ex. job_detail_html/<hash>.html) et écrits en entier ou pas du tout.
              is_test : un stockage de test écrit et lit dans une zone à part ; les
              données de test et les vraies ne se croisent jamais.
              Création : Classe(is_test=..., **storage_options de la configuration).
              Aucune règle métier ici : un stockage ne fait que stocker et lire.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from contracts import ContractModel


class IStorage(ABC):
    """Stores and reads tables of contract records, and raw files."""

    def __init__(self, is_test: bool) -> None:
        self.is_test: bool = is_test

    @abstractmethod
    def append(self, table: str, records: Sequence[ContractModel]) -> None:
        """Add records of one contract to a table (nothing if there is none)."""

    @abstractmethod
    def read(self, table: str, source: str) -> list[dict[str, Any]]:
        """Every line of a table for a source; empty if nothing was written."""

    @abstractmethod
    def put_file(self, name: str, content: bytes) -> None:
        """Store a raw file under its name, whole or not at all."""

    @abstractmethod
    def has_file(self, name: str) -> bool:
        """True if a raw file with this name is already stored."""
