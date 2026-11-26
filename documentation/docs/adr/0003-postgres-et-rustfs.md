# ADR-0003 — Stockage : Postgres et RustFS en conteneurs

- **Statut** : Accepté
- **Date** : 2026-11-19
- **Décideur** : David
- **Remplace** : la partie « Parquet et DuckDB » d'[ADR-0002](0002-elt-brut-minimal-dbt.md)

## Contexte

ADR-0002 prévoyait d'écrire les tables brutes en fichiers Parquet, lus par dbt-duckdb. Le projet sera repris
par une équipe, sur plusieurs machines : des fichiers Parquet locaux se partagent mal, n'ont ni contraintes
ni accès concurrent, et le calcul du reste à faire demandait de relire des fichiers. Il faut aussi un stockage
pour le HTML brut des fiches.

## Décision

- **Postgres 17 en conteneur Docker** (`infra/docker-compose.yml`) pour les tables brutes, la configuration
  et les couches dbt (dbt-postgres). Schémas `raw`, `config`, `staging`, `intermediate`, `marts`.
- **RustFS en conteneur**, compatible S3, pour le HTML brut (bucket `jobcompass-raw`), adressé par son
  empreinte.
- Les tables brutes sont créées par des scripts SQL d'initialisation, une colonne par champ du contrat,
  avec une contrainte d'unicité qui rend l'écriture idempotente.

## Alternatives écartées

- **Parquet + DuckDB** : simple pour une personne, mal adapté à une équipe et à des écritures
  concurrentes.
- **MinIO** pour le stockage objet : son édition communautaire n'est plus distribuée.
- **Un entrepôt cloud** : coût et compte à gérer, sans besoin à ce stade.

## Conséquences

- Tout se lance par `docker compose up` ; aucun service externe.
- Le reste à faire se lit dans les tables, et relancer une étape ne crée pas de doublon.
- Un script d'initialisation modifié ne s'applique qu'à un volume vide : les bases existantes se migrent à
  la main.
- DuckDB, Parquet, Neo4j, ClickHouse et Kafka ne sont pas utilisés.
