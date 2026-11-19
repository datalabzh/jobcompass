"""
test_i_use_case_uc.py

Description : tests de l'interface IUseCase.
Règles      : un cas d'utilisation sans execute ne peut pas être créé ; avec
              execute, il le peut. Toute classe qui descend d'IUseCase, abstraite
              ou non, est refusée dès sa définition si son nom ne finit pas par
              UseCase ou si son fichier ne finit pas par _uc.py.
              Ce fichier définit des cas d'utilisation : il finit donc par _uc.
"""

from abc import abstractmethod

import pytest

from interfaces import IUseCase


def test_execute_is_required() -> None:
    """A class that does not implement execute cannot be instantiated."""

    class IncompleteUseCase(IUseCase):
        """A use case missing execute."""

    with pytest.raises(TypeError):
        IncompleteUseCase()  # type: ignore[abstract]


def test_execute_returns_report() -> None:
    """A complete use case runs through execute."""

    class HelloUseCase(IUseCase):
        """A use case returning a fixed report."""

        def execute(self) -> str:
            """Return 'done'."""
            return "done"

    assert HelloUseCase().execute() == "done"


def test_name_without_suffix_refused() -> None:
    """A concrete use case must be named ...UseCase."""
    with pytest.raises(TypeError, match="Hello: a use case name must end with"):

        class Hello(IUseCase):
            """A use case badly named."""

            def execute(self) -> str:
                """Return 'done'."""
                return "done"


def test_abstract_subclass_also_checked() -> None:
    """An interface of use cases must be named ...UseCase too."""
    with pytest.raises(TypeError, match="ISomething: a use case name must end with"):

        class ISomething(IUseCase):
            """An interface for a family of use cases, badly named."""

            @abstractmethod
            def execute(self) -> str:
                """Still abstract."""


def test_file_without_suffix_refused() -> None:
    """A use case defined outside a ..._uc.py file is refused."""

    def execute(self: IUseCase) -> str:
        """Return 'done'."""
        return "done"

    with pytest.raises(TypeError, match="must live in a file ending with _uc.py"):
        type(
            "ElsewhereUseCase",
            (IUseCase,),
            {"__module__": "somewhere.elsewhere", "execute": execute},
        )
