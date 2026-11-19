"""
i_normalization_uc.py

Description : ce que fournit toute normalisation : une classe, avec une seule
              méthode publique, execute.
Règles      : commune à tous les sites : lit la table extracted_job d'une source et
              écrit normalized_job (contrats ExtractedJob -> NormalizedJob).
              Fourni à la création : source, db_storage, is_test, max_jobs
              (None = sans limite), now.
              Jobs à normaliser = jobs extraits - déjà normalisés par ce
              normaliseur, ce modèle et leurs versions ; traités et écrits un par un.
              Chaque NormalizedJob porte la signature du normaliseur et du modèle
              (noms, versions et description en une phrase), déclarée par la
              classe : un nouveau normaliseur ou modèle ajoute des lignes, les
              anciennes restent pour comparer.
              Une classe concrète sans signature complète est refusée dès sa
              définition (TypeError), comme une classe sans execute.
              Changer de normaliseur = une nouvelle classe, déclarée dans
              normalization.toml ; rien d'autre ne change.
              execute renvoie un NormalizationReport (lu par Dagster).
"""

from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from interfaces import IUseCase
from storage.interfaces.i_db_storage import IDbStorage

SIGNATURE: tuple[str, ...] = (
    "normalizer",
    "normalizer_version",
    "model",
    "model_version",
    "description",
)


@dataclass(frozen=True)
class NormalizationReport:
    """What a normalization run did, printed as the JSON summary of the command."""

    source: str
    is_test: bool
    max_jobs: int | None
    normalized: int  # jobs written to normalized_job
    remaining: int  # jobs still to normalize after this run (max_jobs reached)


class INormalizationUseCase(IUseCase):
    """Turns the extracted jobs of a source into normalized jobs."""

    normalizer: str  # name of the normalizer, e.g. 'fake_normalization'
    normalizer_version: str  # change what it does = new version
    model: str  # name of the model used, e.g. 'keyword_list'
    model_version: str  # change the model = new version
    description: str  # what the normalizer and its model do, in one sentence

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Refuse a concrete normalization that does not declare its signature."""
        super().__init_subclass__(**kwargs)
        if getattr(cls.execute, "__isabstractmethod__", False):
            return  # still abstract: its concrete subclasses are checked
        missing: list[str] = [
            name for name in SIGNATURE if not isinstance(getattr(cls, name, None), str)
        ]
        if missing:
            raise TypeError(f"{cls.__name__} must define: {', '.join(missing)}")

    def __init__(
        self,
        source: str,
        db_storage: IDbStorage,
        is_test: bool,
        max_jobs: int | None,
        now: Callable[[], datetime],
    ) -> None:
        self.source: str = source
        self.db_storage: IDbStorage = db_storage
        self.is_test: bool = is_test
        self.max_jobs: int | None = max_jobs
        self.now: Callable[[], datetime] = now

    @abstractmethod
    def execute(self) -> NormalizationReport:
        """Normalize the pending jobs and return the report of the run."""
