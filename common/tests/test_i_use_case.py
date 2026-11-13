"""
test_i_use_case.py

Description : tests of the IUseCase interface.
Rules       : a use case without execute cannot be created; one with it can.
"""

import pytest

from interfaces import IUseCase


def test_execute_is_required() -> None:
    """A class that does not implement execute cannot be instantiated."""

    class Incomplete(IUseCase):
        """A use case missing execute."""

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]


def test_execute_returns_report() -> None:
    """A complete use case runs through execute."""

    class Hello(IUseCase):
        """A use case returning a fixed report."""

        def execute(self) -> str:
            """Return 'done'."""
            return "done"

    assert Hello().execute() == "done"
