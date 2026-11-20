"""
test_i_normalization_uc.py

Description : tests de la signature exigée par INormalizationUseCase.
Règles      : une normalisation concrète sans signature complète est refusée dès sa
              définition, avec le nom de ce qui manque ; une classe encore
              abstraite n'est pas contrôlée.
"""

from abc import abstractmethod

import pytest

from normalization.interfaces.i_normalization_uc import (
    INormalizationUseCase,
    NormalizationReport,
)


def test_normalization_without_description_refused() -> None:
    """A concrete normalization must declare its whole signature."""
    with pytest.raises(
        TypeError, match="NoDescriptionUseCase must define: model_version, description"
    ):

        class NoDescriptionUseCase(INormalizationUseCase):
            """A normalization that forgot part of its signature."""

            normalizer: str = "no_description"
            normalizer_version: str = "0.1.0"
            model: str = "none"

            def execute(self) -> NormalizationReport:
                """Never run."""
                raise NotImplementedError


def test_abstract_subclass_not_checked() -> None:
    """An intermediate class that keeps execute abstract needs no signature yet."""

    class BaseUseCase(INormalizationUseCase):
        """A shared base for several normalizers."""

        @abstractmethod
        def execute(self) -> NormalizationReport:
            """Still abstract."""

    assert BaseUseCase.__name__ == "BaseUseCase"
