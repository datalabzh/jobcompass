# ADR-0005 — Test et production : deux bases, test par défaut

- **Statut** : Accepté
- **Date** : 2026-11-20
- **Décideur** : David

## Contexte

Pendant le développement, on lance sans cesse des passages limités. Ils ne doivent jamais se mêler aux
vraies données, ni charger un site entier par erreur. Une simple colonne `is_test` se filtre mal partout et
s'oublie.

## Décision

- **Deux bases** dans le même Postgres, avec les mêmes tables : `jobcompass` (production) et
  `jobcompass_dev` (test). Dans RustFS, le test est sous le préfixe `dev/`.
- **Par défaut, tout va en test** : sans option, une commande est limitée (configuration du site ou du
  normaliseur) et écrit dans la base de test. `--full` lève les limites et écrit en production ; dbt suit la
  même règle (`--target dev` par défaut, `--target real`), et la planification aussi (`PIPELINE_MODE`).
- Les lignes de test portent aussi `is_test = true`.

## Alternatives écartées

- Un schéma de test dans la même base : les requêtes peuvent mélanger les schémas.
- La colonne `is_test` seule : à filtrer dans chaque modèle, oubli facile.

## Conséquences

- Une donnée de test ne peut pas apparaître en production : Postgres ne lit pas d'une base à l'autre.
- Les tests automatiques vident la base de test avant chaque test.
