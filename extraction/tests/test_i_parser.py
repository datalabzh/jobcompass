"""
test_i_parser.py

Description : tests de la signature exigée par IParser.
Règles      : un parseur concret sans signature complète est refusé dès sa
              définition, avec le nom de ce qui manque ; un parseur complet est
              accepté.
"""

import pytest

from extraction.interfaces import IParser


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
