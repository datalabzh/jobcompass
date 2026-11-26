# ADR-0004 — Identifiants : un seul hash calculé en Python

- **Statut** : Accepté
- **Date** : 2026-11-19
- **Décideur** : David

## Contexte

Les briques et dbt ont besoin d'identifiants stables pour les offres, les fiches, les passages, les
normalisations. Calculés à plusieurs endroits, ils risquent de diverger.

## Décision

- Un seul identifiant est calculé en Python : **`hash_html_id`**, SHA-256 du HTML d'une fiche
  (`compute_hash_html_id`, dans `common/contracts/`). C'est aussi le nom du fichier dans le stockage objet.
- Tous les autres sont calculés **dans le staging dbt**, avec `dbt_utils.generate_surrogate_key`, et
  nommés `hash_<objet>_id` (`hash_job_id` = source + URL, `hash_job_detail_id` = hash_html_id + scraper
  + version…).
- La normalisation recopie telle quelle la clé de la fiche (`hash_html_id`, `scraper`, `scraper_version`) :
  elle ne calcule rien.

## Alternatives écartées

- Des identifiants calculés par chaque brique : règles dupliquées, risque d'écart.
- Des identifiants séquentiels en base : dépendent de l'ordre d'écriture, différents entre la base de test
  et la production.

## Conséquences

- Les tables brutes n'ont pas de colonne d'identifiant haché, seulement des contraintes d'unicité sur leurs
  colonnes naturelles.
- Depuis n'importe quel mart, `hash_html_id` mène directement au HTML d'origine.
