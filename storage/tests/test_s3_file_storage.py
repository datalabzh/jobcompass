"""
test_s3_file_storage.py

Description : tests du stockage des fichiers bruts dans RustFS, contre le vrai
              conteneur (docker compose -f infra/docker-compose.yml up -d --wait).
Règles      : tous les tests écrivent sous test/, vidé avant chacun ; aucun n'écrit
              ailleurs dans le bucket.
              Couvre : un fichier est écrit et retrouvé ; la zone de test est à part ;
              clear_test_zone efface les fichiers de test et est refusé pour un
              stockage réel.
"""

import uuid
from collections.abc import Iterator

import pytest

from storage.s3_file_storage import S3FileStorage


@pytest.fixture
def storage() -> Iterator[S3FileStorage]:
    """The test zone of the real bucket, emptied before the test."""
    test: S3FileStorage = S3FileStorage(is_test=True)
    test.clear_test_zone()
    yield test


def unique_name() -> str:
    """A file name no other run uses."""
    return f"raw_job_detail_html/{uuid.uuid4().hex}.html"


def test_put_then_has(storage: S3FileStorage) -> None:
    """A raw file is stored under its name and found again."""
    name: str = unique_name()
    assert not storage.has_file(name)
    storage.put_file(name, b"<html/>")
    assert storage.has_file(name)


def test_test_zone_is_apart(storage: S3FileStorage) -> None:
    """A file written by a test storage is not seen by a real storage."""
    name: str = unique_name()
    storage.put_file(name, b"<html/>")
    assert not S3FileStorage(is_test=False).has_file(name)


def test_clear_test_zone(storage: S3FileStorage) -> None:
    """clear_test_zone deletes the test files."""
    name: str = unique_name()
    storage.put_file(name, b"<html/>")
    storage.clear_test_zone()
    assert not storage.has_file(name)


def test_clear_refused_for_real_storage() -> None:
    """clear_test_zone never deletes real files."""
    with pytest.raises(RuntimeError, match="test zone"):
        S3FileStorage(is_test=False).clear_test_zone()
