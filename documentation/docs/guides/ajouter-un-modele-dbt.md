# Ajouter un modèle dbt

Ce guide ajoute un modèle d'analyse (un intermédiaire ou un mart). Les règles d'écriture sont dans
[Conventions dbt](../conventions/dbt.md) : ce guide donne l'ordre de travail. Pour le staging d'un nouveau
site, voir [Ajouter un site](ajouter-un-site.md).

## 1. Choisir la couche et le nom

| Couche | Quand | Nom | Matérialisation |
|---|---|---|---|
| `staging` | mettre à plat **une** table brute, sans jointure | `stg_<source>__<entite>` | vue |
| `intermediate` | jointures, regroupements, étapes de préparation | `int_<domaine>__<entite>_<action>` | vue |
| `marts` | un produit final, interrogé par les analyses | `<domaine>__<entite>` | table |

Le domaine est le dossier (`jobs`, `skills`, bientôt `clusters`…). Avant de créer, regarder les modèles
existants : souvent, il suffit de **lire un modèle existant** plutôt que d'en dupliquer la logique. Les
modèles sur les offres partent de `int_jobs__job_infos_aggregated` et `int_jobs__job_details_unioned`,
qui couvrent déjà tous les sites.

## 2. Écrire le `.sql`

Dans `dbt/models/<couche>/<domaine>/<nom>.sql` :

- un en-tête `Model Name / Description / Rules` (copier celui d'un modèle voisin) ;
- un CTE d'import par modèle lu, nommé comme lui, avec seulement les colonnes utiles ;
- puis les étapes, et un CTE `final` aux colonnes groupées par type (ids, strings, numerics, arrays,
  booleans, dates, timestamps) ;
- une clé `hash_<objet>_id` calculée avec `dbt_utils.generate_surrogate_key` si le modèle a une nouvelle
  granularité.

## 3. Construire

```bash
uv run --env-file infra/.env --package jobcompass-dbt dbt build --project-dir dbt --profiles-dir dbt --target dev --select <nom>
```

`--select +<nom>` construit aussi ce dont il dépend, `--select <nom>+` ce qui en dépend.

## 4. Documenter et tester : le `.yml`

À côté du `.sql`, un `<nom>.yml` du même nom : une description pour le modèle, et pour **chaque** colonne
une description, son `data_type` et ses tests. La clé du modèle a toujours `unique` et `not_null`. Les
types se lisent sur la vue construite :

```sql
\d+ intermediate.<nom>
```

## 5. Contrôler et commiter

```bash
git add dbt/models/<couche>/<domaine>/<nom>.*        # pre-commit ne voit que les fichiers suivis
uv run pre-commit run --all-files
```

Les contrôles vérifient le style SQL (SQLFluff), la présence des descriptions et des tests, et les noms
(dbt-checkpoint). Pour corriger le style automatiquement :

```bash
uv run pre-commit run sqlfluff-fix --all-files --hook-stage manual
```

## Check-list

La liste complète est dans [Conventions dbt, partie 10](../conventions/dbt.md#10-check-list-avant-chaque-commit).
