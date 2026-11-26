# ADR-0006 — Normalisations versionnées, normaliseur courant en table

- **Statut** : Accepté
- **Date** : 2026-11-19
- **Décideur** : David

## Contexte

Le normaliseur va changer souvent (factice, puis modèles NLP successifs). Il faut comparer deux normaliseurs
sur les mêmes fiches, et choisir celui qui alimente les analyses sans recalculer ni effacer quoi que ce soit.

## Décision

- Chaque ligne de `normalized_job` est **signée** : normaliseur, modèle, leurs versions et une phrase de
  description. Une nouvelle version ajoute des lignes ; les anciennes restent.
- Le normaliseur dont les résultats alimentent les marts est désigné dans la table
  **`config.normalizer`** (`is_current`, un seul garanti par un index unique), pas dans une variable dbt.
- Le normaliseur lancé par défaut est désigné dans `normalization.toml` (`default`).

## Alternatives écartées

- Une variable dbt : le choix vivrait dans le code et non dans la base, et différerait selon qui lance dbt.
- Écraser les résultats à chaque nouvelle version : comparaison impossible.

## Conséquences

- Basculer les marts vers un autre normaliseur = une transaction SQL, puis `dbt build`.
- Les deux réglages (`default` et `is_current`) se changent ensemble, par décision d'équipe.
