"""
s3_file_storage.py

Description : stockage des fichiers bruts dans un stockage objet compatible S3
              (RustFS, conteneur de infra/).
Règles      : connexion lue par la classe dans infra/.env (S3_ACCESS_KEY,
              S3_SECRET_KEY, S3_BUCKET, S3_API_PORT ; hôte localhost par défaut,
              S3_HOST pour le changer) : l'appelant ne fournit que is_test.
              Le bucket existe déjà (créé par rustfs-init).
              Clé d'un fichier = son nom (ex. raw_job_detail_html/<hash>.html),
              précédé de dev/ pour un test (zone de test, comme la base _dev de
              Postgres) : supprimer dev/ efface toutes les données de test.
              Un objet S3 est écrit en entier ou pas du tout : pas de fichier
              temporaire.
              Adressage par chemin (endpoint/bucket/clé), et sommes de contrôle
              envoyées seulement quand elles sont exigées : réglages compatibles
              avec RustFS comme avec S3.
              clear_test_zone supprime tout ce qui est sous dev/ (tests) ; refusé
              pour un stockage réel.
"""

from typing import Any

import boto3
from botocore.client import BaseClient, Config
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict

from storage.infra_env import INFRA_ENV_FILE
from storage.interfaces.i_file_storage import IFileStorage

TEST_PREFIX: str = "dev/"
NOT_FOUND: set[str] = {"404", "NoSuchKey", "NotFound"}


class S3Settings(BaseSettings):
    """Connection to the S3 container, from S3_* in infra/.env."""

    model_config = SettingsConfigDict(
        env_prefix="S3_", env_file=INFRA_ENV_FILE, extra="ignore"
    )

    host: str = "localhost"
    api_port: int = 9000
    access_key: str
    secret_key: str
    bucket: str


class S3FileStorage(IFileStorage):
    """Raw files in an S3 bucket, under dev/ for test runs."""

    def __init__(self, is_test: bool) -> None:
        super().__init__(is_test)
        settings: S3Settings = S3Settings()
        self._bucket: str = settings.bucket
        self._prefix: str = TEST_PREFIX if is_test else ""
        self._client: BaseClient = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.host}:{settings.api_port}",
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            region_name="us-east-1",
            config=Config(
                s3={"addressing_style": "path"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def put_file(self, name: str, content: bytes) -> None:
        """Store a raw file under its name, as one object."""
        self._client.put_object(Bucket=self._bucket, Key=self._key(name), Body=content)

    def has_file(self, name: str) -> bool:
        """True if an object with this name is already stored."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._key(name))
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in NOT_FOUND:
                return False
            raise
        return True

    def clear_test_zone(self) -> None:
        """Delete every object under dev/; refused for a real storage."""
        if not self.is_test:
            raise RuntimeError("clear_test_zone only empties the test zone")
        paginator: Any = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._prefix):
            keys: list[dict[str, str]] = [
                {"Key": item["Key"]} for item in page.get("Contents", [])
            ]
            if keys:
                self._client.delete_objects(
                    Bucket=self._bucket, Delete={"Objects": keys}
                )

    def _key(self, name: str) -> str:
        """The object key of a file name: dev/ first for a test storage."""
        return f"{self._prefix}{name}"
