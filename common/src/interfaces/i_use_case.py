"""
i_use_case.py

Description : ce que fournit tout cas d'utilisation de toute brique : une seule
              méthode publique, execute.
Règles      : un cas d'utilisation reçoit tout ce dont il a besoin à sa création
              (scraper, stockage, réglages...) ; execute le lance et renvoie son
              rapport.
              Tout le reste est privé : les appelants (CLI, Dagster) ne connaissent
              que execute.
"""

from abc import ABC, abstractmethod


class IUseCase(ABC):
    """A business action, run by execute()."""

    @abstractmethod
    def execute(self) -> object:
        """Run the use case and return its report."""
