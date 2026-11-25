"""
postgres_db_storage.py

Description : stockage des tables dans PostgreSQL (conteneur de infra/).
Règles      : connexion lue par la classe dans infra/.env (POSTGRES_USER,
              POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT ; hôte localhost par
              défaut, POSTGRES_HOST pour le changer) : l'appelant ne fournit que
              is_test.
              Base POSTGRES_DB pour un vrai passage, POSTGRES_DB + "_dev" pour un
              test : deux bases à part, avec les mêmes tables (schéma raw), créées
              par infra/postgres/init. Une donnée de test ne peut pas se mêler aux
              vraies (Postgres ne lit pas d'une base à l'autre).
              append : une ligne par enregistrement, colonnes = champs du contrat ;
              insert ... on conflict do nothing : réécrire une ligne déjà présente
              (même contrainte unique) ne fait rien, un passage relancé ne crée pas
              de doublon. Un ajout ne mélange pas deux contrats.
              Les dict et les listes sont envoyés en jsonb ; le reste en texte,
              converti par Postgres selon le type de la colonne (un texte JSON comme
              card ou payload devient du jsonb). Relu, un jsonb revient en dict ou
              en liste.
              Noms de schéma, table et colonnes passés par psycopg.sql.Identifier :
              aucune concaténation de texte dans les requêtes.
              Une connexion par appel, fermée aussitôt : simple, suffisant pour nos
              volumes.
              clear_test_zone vide toutes les tables brutes de la base _dev
              (tests) ; refusé pour un stockage réel.
"""

from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic_settings import BaseSettings, SettingsConfigDict

from contracts.components.contract_model import ContractModel
from storage.infra_env import INFRA_ENV_FILE
from storage.interfaces.i_db_storage import IDbStorage

SCHEMA: str = "raw"
DEV_DATABASE_SUFFIX: str = "_dev"


class PostgresSettings(BaseSettings):
    """Connection to the Postgres container, from POSTGRES_* in infra/.env."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_", env_file=INFRA_ENV_FILE, extra="ignore"
    )

    host: str = "localhost"
    port: int = 5432
    user: str
    password: str
    db: str


class PostgresDbStorage(IDbStorage):
    """Tables in Postgres, schema raw: real database, or the _dev one for tests."""

    def __init__(self, is_test: bool) -> None:
        super().__init__(is_test)
        self._settings: PostgresSettings = PostgresSettings()
        self._schema: str = SCHEMA
        self._database: str = self._settings.db + (
            DEV_DATABASE_SUFFIX if is_test else ""
        )

    def append(self, table: str, records: Sequence[ContractModel]) -> None:
        """Insert the records; a line already present is left as it is."""
        if not records:
            return
        columns: list[str] = self._columns_of(records)
        query: sql.Composed = sql.SQL(
            "insert into {table} ({columns}) values ({values}) on conflict do nothing"
        ).format(
            table=sql.Identifier(self._schema, table),
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )
        rows: list[list[Any]] = [self._to_row(record, columns) for record in records]
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.executemany(query, rows)

    def read(
        self, table: str, source: str, columns: Sequence[str] | None = None
    ) -> list[dict[str, Any]]:
        """Lines of a table for a source, all columns or only the ones named."""
        selected: sql.Composable = (
            sql.SQL("*")
            if columns is None
            else sql.SQL(", ").join(map(sql.Identifier, columns))
        )
        query: sql.Composed = sql.SQL(
            "select {columns} from {table} where source = %s"
        ).format(columns=selected, table=sql.Identifier(self._schema, table))
        with (
            self._connect() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            cursor.execute(query, (source,))
            return cursor.fetchall()

    def clear_test_zone(self) -> None:
        """Empty every table of the test schema; refused for a real storage."""
        if not self.is_test:
            raise RuntimeError("clear_test_zone only empties the test zone")
        with self._connect() as connection:
            tables: list[tuple[str]] = connection.execute(
                "select tablename from pg_tables where schemaname = %s",
                (self._schema,),
            ).fetchall()
            if tables:
                connection.execute(
                    sql.SQL("truncate {tables}").format(
                        tables=sql.SQL(", ").join(
                            sql.Identifier(self._schema, name) for (name,) in tables
                        )
                    )
                )

    def _connect(self) -> psycopg.Connection:
        """A new connection; committed and closed at the end of its block."""
        return psycopg.connect(
            host=self._settings.host,
            port=self._settings.port,
            user=self._settings.user,
            password=self._settings.password,
            dbname=self._database,
        )

    def _columns_of(self, records: Sequence[ContractModel]) -> list[str]:
        """The columns of the records' contract; one contract only."""
        contracts: set[type[ContractModel]] = {type(record) for record in records}
        if len(contracts) > 1:
            raise ValueError(f"one contract per append, got {contracts}")
        return list(contracts.pop().model_fields)

    def _to_row(self, record: ContractModel, columns: list[str]) -> list[Any]:
        """A record as values in column order: dicts and lists as jsonb."""
        values: dict[str, Any] = record.model_dump(mode="json")
        return [
            Jsonb(values[name])
            if isinstance(values[name], (dict, list))
            else values[name]
            for name in columns
        ]
