"""
i_parser.py

Description : ce que fournit tout parseur : une seule méthode publique, parse, qui
              lit un contenu déjà téléchargé.
Règles      : un parseur ne fait que lire : aucune requête, aucune écriture. C'est
              la classe d'extraction du site qui va chercher les pages et stocke.
              kind = le type de page lu ; chaque site fixe ses types et ce que parse
              renvoie pour chacun (ex. jobup : 'job_info' -> page de résultats,
              'job_detail' -> fiche d'un job).
              Contenu illisible : ParsingError ; l'extraction le journalise et
              continue.
              name et version (la signature) sont enregistrés avec ce que le
              parseur produit : changer ce qui est lu ou comment = monter version.
              Une classe concrète sans signature complète est refusée dès sa
              définition (TypeError), comme une classe sans parse.
              Changer de parseur (autre librairie...) = une nouvelle classe, que la
              classe d'extraction du site utilise à la place de l'ancienne.
"""

from abc import ABC, abstractmethod

SIGNATURE: tuple[str, ...] = ("name", "version")


class ParsingError(Exception):
    """The content could not be read as expected (page changed, data missing...)."""


class IParser(ABC):
    """Reads downloaded content; never requests nor stores anything."""

    name: str  # recorded with what the parser produces, e.g. 'jobup_parser'
    version: str  # change what is read or how = new version

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Refuse a concrete parser that does not declare its whole signature."""
        super().__init_subclass__(**kwargs)
        if getattr(cls.parse, "__isabstractmethod__", False):
            return  # still abstract: its concrete subclasses are checked
        missing: list[str] = [
            name for name in SIGNATURE if not isinstance(getattr(cls, name, None), str)
        ]
        if missing:
            raise TypeError(f"{cls.__name__} must define: {', '.join(missing)}")

    @abstractmethod
    def parse(self, kind: str, content: bytes) -> object:
        """What a page of this kind holds; ParsingError if it cannot be read."""
