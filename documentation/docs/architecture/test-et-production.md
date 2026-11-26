# Test et production

## La règle

**Par défaut, tout va en test.** Sans option explicite, aucune commande ne peut écrire en production ni
charger un site entier. Il faut le demander : `--full` pour l'extraction et la normalisation,
`--target real` pour dbt, `PIPELINE_MODE=full` pour la planification.

## Les deux zones

| | Test | Production |
|---|---|---|
| Base Postgres | `jobcompass_dev` | `jobcompass` |
| RustFS | préfixe `dev/` dans le bucket | à la racine du bucket |
| Colonne `is_test` | `true` | `false` |

Les deux bases ont exactement les mêmes tables. Postgres ne lit pas d'une base à l'autre : une donnée de test
ne peut pas se mêler aux vraies.

## Comment chaque brique l'applique

| Brique | Test (défaut) | Production |
|---|---|---|
| extraction | `run jobup` : limites du `site.toml` (jobup : 1 page, 2 fiches) ; `--max-pages`, `--max-jobs` pour les changer | `run jobup --full` |
| normalisation | `run jobup` : limite du `normalizer.toml` (10 fiches) ; `--max-jobs` pour la changer | `run jobup --full` |
| dbt | `--target dev` (défaut du profil) | `--target real` |
| planification | `PIPELINE_MODE=test` (défaut) | `PIPELINE_MODE=full` dans `orchestration/.env` |

Un passage avec au moins une limite est toujours un test. `--full` lève toutes les limites et ne se combine
pas avec elles.

## Les tests automatiques

Les tests Python écrivent eux aussi dans la base de test, et **la vident avant chaque test**
(`clear_test_zone`). Lancer les tests efface donc les données des passages en mode test : il suffit de
relancer un passage pour les retrouver. La production n'est jamais touchée : vider une zone réelle est
refusé.

Voir [Conventions des tests](../conventions/tests.md).
