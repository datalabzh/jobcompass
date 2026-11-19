"""
i_file_storage.py

Description : ce que doit fournir tout stockage de fichiers bruts : déposer un
              fichier et savoir s'il est déjà là.
Règles      : les fichiers sont nommés par l'appelant
              (ex. raw_job_detail_html/<hash>.html) et écrits en entier ou pas du
              tout ; un fichier déposé n'est jamais modifié.
              is_test : un stockage de test écrit et lit dans une zone à part ; les
              fichiers de test et les vrais ne se croisent jamais.
              Création : Classe(is_test=..., **options de la configuration).
              Aucune règle métier ici : un stockage ne fait que stocker et vérifier.
"""

from abc import ABC, abstractmethod


class IFileStorage(ABC):
    """Stores raw files under a name given by the caller."""

    def __init__(self, is_test: bool) -> None:
        self.is_test: bool = is_test

    @abstractmethod
    def put_file(self, name: str, content: bytes) -> None:
        """Store a raw file under its name, whole or not at all."""

    @abstractmethod
    def has_file(self, name: str) -> bool:
        """True if a raw file with this name is already stored."""
