"""
i_use_case.py

Description : ce que fournit tout cas d'utilisation de toute brique : une seule
              méthode publique, execute.
Règles      : un cas d'utilisation reçoit tout ce dont il a besoin à sa création
              (scraper, stockage, réglages...) ; execute le lance et renvoie son
              rapport.
              Tout le reste est privé : les appelants (CLI, Dagster) ne connaissent
              que execute.
              Nommage, pour reconnaître un cas d'utilisation sans ouvrir son
              fichier : toute classe qui en descend, interface comprise, finit par
              UseCase (ex. ISiteExtractionUseCase, JobupExtractionUseCase) et vit
              dans un fichier qui finit par _uc.py (ex. jobup_extraction_uc.py).
              Les deux sont vérifiés dès la définition de la classe (TypeError).
"""

from abc import ABC, abstractmethod

CLASS_SUFFIX: str = "UseCase"
MODULE_SUFFIX: str = "_uc"


class IUseCase(ABC):
    """A business action, run by execute()."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Refuse a use case badly named, or defined in a file badly named."""
        super().__init_subclass__(**kwargs)
        if not cls.__name__.endswith(CLASS_SUFFIX):
            raise TypeError(
                f"{cls.__name__}: a use case name must end with {CLASS_SUFFIX}"
            )
        if not cls.__module__.endswith(MODULE_SUFFIX):
            raise TypeError(
                f"{cls.__name__}: a use case must live in a file ending with "
                f"{MODULE_SUFFIX}.py, not in {cls.__module__}"
            )

    @abstractmethod
    def execute(self) -> object:
        """Run the use case and return its report."""
