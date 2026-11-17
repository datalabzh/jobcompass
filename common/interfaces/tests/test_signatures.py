"""
test_signatures.py

Description : tests des signatures exigées par IParser et INormalization.
Règles      : une classe concrète sans signature complète est refusée dès sa
              définition, avec le nom de ce qui manque ; une classe complète est
              acceptée ; une classe encore abstraite n'est pas contrôlée.
"""

from abc import abstractmethod

import pytest

from interfaces import INormalization, IParser, NormalizationReport


def test_parser_without_version_refused() -> None:
    """A concrete parser must declare name and version."""
    with pytest.raises(TypeError, match="NoVersion must define: version"):

        class NoVersion(IParser):
            """A parser that forgot its version."""

            name: str = "no_version"

            def parse(self, kind: str, content: bytes) -> object:
                """Return nothing."""
                return None


def test_complete_parser_accepted() -> None:
    """A parser with its signature and parse can be created."""

    class Complete(IParser):
        """A complete parser."""

        name: str = "complete"
        version: str = "1.0.0"

        def parse(self, kind: str, content: bytes) -> object:
            """Return the content."""
            return content

    assert Complete().parse("job_detail", b"x") == b"x"


def test_normalization_without_description_refused() -> None:
    """A concrete normalization must declare its whole signature."""
    with pytest.raises(TypeError, match="must define: model_version, description"):

        class NoDescription(INormalization):
            """A normalization that forgot part of its signature."""

            normalizer: str = "no_description"
            normalizer_version: str = "0.1.0"
            model: str = "none"

            def execute(self) -> NormalizationReport:
                """Never run."""
                raise NotImplementedError


def test_abstract_subclass_not_checked() -> None:
    """An intermediate class that keeps execute abstract needs no signature yet."""

    class Base(INormalization):
        """A shared base for several normalizers."""

        @abstractmethod
        def execute(self) -> NormalizationReport:
            """Still abstract."""

    assert Base.__name__ == "Base"
