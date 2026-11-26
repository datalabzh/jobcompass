# ADR-0008 — Plusieurs sites : un staging par site, réunis dans intermediate

- **Statut** : Accepté
- **Date** : 2026-11-26
- **Décideur** : David

## Contexte

Le projet prévoit plusieurs portails ([ADR-0001](0001-perimetre-collecte.md)). Les tables brutes sont
communes (colonne `source`), mais chaque portail a son format de carte et de JSON-LD. La logique métier
(offre active, dernière fiche, compétences) est la même pour tous. Les modèles dbt étaient écrits pour jobup
seul.

## Décision

- **Un staging par site** (`dbt/models/staging/<site>/`), qui lit ses clés JSON et sort **les mêmes
  colonnes** que les autres sites.
- Trois modèles **`int_jobs__*_unioned`** réunissent les sites (un CTE par site, `union all`), écrits à la
  main. Toute la logique en aval est écrite une seule fois.
- `is_active` est calculé par site et par catégorie.
- Une table **`config.site`** sert de registre des sites ; un test `relationships` refuse un `site_name`
  non déclaré.

## Alternatives écartées

- **Une chaîne complète par site, réunie dans les marts** : logique métier copiée dans chaque site.
- **Un seul staging pour tous les sites** (`case source when …`) : tous les sites dans le même fichier.
- **La liste des sites dans une variable dbt, avec des unions générées** : moins lisible ; et une table ne
  peut pas piloter les `ref()`, résolus avant toute connexion à la base.

## Conséquences

- Ajouter un site côté dbt = son staging, un CTE et une ligne `union all` dans trois modèles, une ligne dans
  `config.site` (voir le guide [Ajouter un site](../guides/ajouter-un-site.md)).
- Un site oublié dans `config.site` fait échouer `dbt build` avec un message clair.
