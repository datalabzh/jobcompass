# Conventions dbt : règles à respecter dans ce projet

Ce document fixe les conventions dbt de JobCompass. Elles s'appuient sur les guides de dbt Labs :

- [How we structure our dbt projects](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- [How we style our dbt models](https://docs.getdbt.com/best-practices/how-we-style/1-how-we-style-our-dbt-models)
- [How we style our SQL](https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql)

**Consigne pour Claude** : appliquer toutes ces règles à chaque modèle, `.yml`, macro ou snapshot écrit
dans ce projet.

Dans ce document, `<source>` désigne une source de données (un site : `jobup`…), `<domaine>` un domaine
métier (`jobs`, `skills`…), `<entite>` l'objet décrit par un modèle (`job_details`, `clusters`…).

Le projet dbt est dans `transformation/` ; la base est **DuckDB** ; les sources sont les fichiers
Parquet bruts déposés par l'extraction Python (ADR-0002).

---

## 1. Couches, dossiers et nommage des fichiers

### Trois couches

| Couche | Rôle | Préfixe du modèle | Matérialisation par défaut |
|---|---|---|---|
| `staging` | une source, mise à plat et renommée, sans jointure | `stg_` | vue |
| `intermediate` | jointures, calculs, étapes de préparation | `int_` | vue |
| `marts` | produits finaux lus par l'analyse ou les applications | aucun | table |

Bronze = les Parquet bruts (sources) ; silver = staging et intermédiaires ; gold = marts.

### Le double underscore

Le double underscore `__` sépare **le contexte** (source ou domaine) **de l'objet** : on lit tout de suite
d'où vient le modèle et ce qu'il contient.

- Staging : `stg_<source>__<entite>` (ex. `stg_jobup__job_details`).
- Intermédiaire : `int_<domaine>__<entite>_<action>` (ex. `int_jobs__job_details_unioned`).
- Mart : `<domaine>__<entite>` (ex. `jobs__job_offers`).
- Snapshot : `<domaine>__snap_<entite>` (ex. `jobs__snap_job_offers`).

Un simple underscore sépare les mots à l'intérieur d'une partie.

### Dossiers

```
transformation/
  dbt_project.yml
  profiles.yml
  packages.yml
  models/
    staging/
      jobup/
        src_jobup.yml
        stg_jobup.yml
        stg_jobup__job_details.sql
        stg_jobup__job_infos.sql
    intermediate/
      jobs/
        int_jobs__job_details_unioned.sql
        int_jobs__job_details_unioned.yml
    marts/
      jobs/
        jobs__job_offers.sql
        jobs__job_offers.yml
  snapshots/
    jobs__snap_job_offers.sql
    jobs__snap_job_offers.yml
  macros/
    my_macro.sql
    my_macro.yml
```

- Tout en minuscules, en `snake_case`. Des underscores dans les noms de modèles, jamais de points.
- **Staging** : un dossier par source (un site). Dans ce dossier :
  - `src_<source>.yml` : déclaration des tables sources ;
  - `stg_<source>.yml` : description **des modèles de staging et de leurs colonnes** (pas des tables
    sources) ;
  - un fichier `stg_<source>__<entite>.sql` par modèle.
- Dans `src_<source>.yml`, la clé `sources: - name:` porte le nom du dossier.
- **Intermédiaires et marts** : un dossier par domaine métier. Chaque modèle a un `.yml` du même nom, à
  côté de son `.sql`.
- Un modèle de staging lit **une seule** source. Un modèle de staging par table source.
- Une macro a son `.yml` de description à côté d'elle.
- Versions de modèles : suffixe `_v1`, `_v2`.

### Avant de développer

- Regarder les sources, staging et modèles existants, et les **réutiliser** plutôt que d'en créer des
  doublons.
- Avant de modifier un modèle, regarder dans le DAG les modèles enfants impactés.

---

## 2. Nommage des modèles et des colonnes

- Modèles au **pluriel** quand c'est possible (`job_details`, `clusters`).
- **Une clé primaire par modèle**, nommée `<objet>_id`, de type texte, testée `unique` et `not_null`.
  - Si une colonne existante est déjà unique à la granularité du modèle, c'est elle la clé : **pas de
    clé de synthèse en plus**.
  - Si l'unicité porte sur plusieurs colonnes, créer une clé de synthèse avec
    `dbt_utils.generate_surrogate_key`.
- Même nom de clé dans tous les modèles (`job_detail_id` partout, jamais `id`).
- Noms **métier** plutôt que noms de la source (`company_name`, même si le JSON-LD dit
  `hiringOrganization.name`).
- Ni abréviation ni alias court (`company`, pas `comp` ; `job_details`, pas `jd`).
- `snake_case` partout : schémas, tables, colonnes.
- Pas de mot réservé SQL comme nom de colonne (`date`, `type`, `name`…) : le préciser (`posted_date`,
  `payload_format`, `company_name`).
- Booléens : préfixe `is_` ou `has_`.
- Dates : `<événement>_date` (`posted_date`).
- Timestamps : `<événement>_at` (`fetched_at`), en UTC ; sinon suffixe de fuseau (`posted_at_cet`).
- Événements au passé : `created`, `updated`, `deleted`, `fetched`.
- Montants en décimal (`19.99`) ; sinon suffixe d'unité (`salary_in_cents`).

### Colonnes groupées par type

Dans le `select` final, les colonnes sont groupées et précédées d'un commentaire `---------- <type>`,
**dans cet ordre** :

1. `ids`
2. `strings`
3. `numerics`
4. `arrays`
5. `booleans`
6. `dates`
7. `timestamps`

Les hash et le JSON brut (texte) sont rangés en `strings`. Pas de groupe qui mélange les types (pas de
groupe `technical`, `hashes` ou `load`).

---

## 3. Écriture SQL

### Règles générales

- Squelette : `with`, puis les CTE, puis `select * from <dernière CTE>`.
- **CTE d'import** en tête de fichier : chaque `ref()` est dans une CTE **nommée comme le modèle lu**,
  qui ne sélectionne que les colonnes utiles, avec un `where` pour filtrer dès que possible.
- Une CTE fait une seule chose, et son nom dit ce qu'elle fait (`job_details_joined_to_job_infos`).
- Une CTE copiée dans plusieurs modèles devient un modèle intermédiaire.
- Commentaires de CTE en Jinja : `{# ... #}` (ils ne partent pas dans le SQL compilé).
- `as` explicite pour tout alias de colonne ou de table.
- Mots-clés, fonctions et noms de colonnes **en minuscules**.
- Indentation de 4 espaces, lignes de 80 caractères au plus, virgules en fin de ligne.
- Champs simples avant les agrégats et les fonctions de fenêtre.
- Agréger le plus tôt possible, sur le plus petit volume, avant les jointures.
- `group by 1, 2` (par position) plutôt que par nom ; au-delà de quelques colonnes, revoir le modèle.
- `union all` plutôt que `union`, sauf dédoublonnage voulu.
- Jointures :
  - type explicite : `inner join`, `left join`, jamais `join` seul ;
  - pas d'alias de table court : dès qu'il y a deux tables, préfixer chaque colonne par le **nom
    complet** de sa CTE ;
  - toujours de gauche à droite : pas de `right join` ;
  - pas de `using`, toujours `on`.

### En-tête de fichier

Chaque modèle commence par un en-tête `Model Name / Description / Rules` (les règles métier appliquées,
en clair) :

```sql
-- ---------------------------------------------------------------------------
-- Model Name: jobs__job_offers.sql
-- Description: one row per job offer, with its latest detail page.
-- Rules: offers never downloaded kept with has_detail = false.
-- ---------------------------------------------------------------------------
```

### Staging

- Modèle en deux CTE : `source`, puis `renamed`, puis `select * from renamed`.
- **Mise à plat et renommage uniquement** : typage, nettoyage (`trim`, `nullif`, `lower`), extraction de
  champs JSON. **Aucune jointure** (elles vont dans les intermédiaires), **aucune agrégation**.
- Écarter dès le staging les lignes inutiles en aval (lignes supprimées, anciennes extractions d'une
  même page), sauf si un modèle en aval en a besoin.
- Contenu de la CTE `source` :
  - pas de colonne à exclure : `select * from {{ source(...) }}` ;
  - des colonnes à exclure : `dbt_utils.star(..., except=[...])` (partie 4).

```sql
-- ---------------------------------------------------------------------------
-- Model Name: stg_jobup__job_details.sql
-- Description: jobup job detail pages, one row per page (url, raw_hash),
--              JSON-LD read into columns.
-- Rules: no join. Latest extraction of a page only (scraper_version).
--        Columns read from the JSON-LD are null for paragraphs pages.
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('jobup', 'raw_job_detail') }}

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(['url', 'raw_hash']) }}
            as job_detail_id,

        ---------- strings
        raw_hash,
        url as job_url,
        payload_format,
        payload ->> '$.title' as job_title,
        payload ->> '$.hiringOrganization.name' as company_name,

        ---------- dates
        try_cast(left(payload ->> '$.datePosted', 10) as date) as posted_date,

        ---------- timestamps
        fetched_at

    from source
    {# A page re-extracted later: the latest extraction only #}
    qualify row_number() over (
        partition by url, raw_hash
        order by fetched_at desc, scraper_version desc
    ) = 1

)

select * from renamed
```

### Intermédiaires et marts

- CTE d'import, CTE de travail, puis une CTE `final` qui pose les groupes de colonnes, puis
  `select * from final`.

```sql
-- ---------------------------------------------------------------------------
-- Model Name: jobs__job_offers.sql
-- Description: one row per job offer, with its latest detail page.
-- Rules: offers never downloaded kept (left join), has_detail = false.
-- ---------------------------------------------------------------------------

with

stg_jobup__job_infos as (

    select
        job_url,
        category,
        seen_at
    from {{ ref('stg_jobup__job_infos') }}

),

stg_jobup__job_details as (

    select
        job_url,
        job_title,
        fetched_at
    from {{ ref('stg_jobup__job_details') }}

),

{# One row per offer before the join: its first sighting #}
job_infos_aggregated_to_offers as (

    select
        job_url,
        min(seen_at) as first_seen_at
    from stg_jobup__job_infos
    group by 1

),

offers_joined_to_details as (

    select
        job_infos_aggregated_to_offers.job_url,
        job_infos_aggregated_to_offers.first_seen_at,
        stg_jobup__job_details.job_title,
        stg_jobup__job_details.fetched_at
    from job_infos_aggregated_to_offers
    left join stg_jobup__job_details
        on
            job_infos_aggregated_to_offers.job_url
            = stg_jobup__job_details.job_url

),

final as (

    select

        ---------- ids
        job_url as job_offer_id,

        ---------- strings
        job_title,

        ---------- booleans
        fetched_at is not null as has_detail,

        ---------- timestamps
        first_seen_at,
        fetched_at

    from offers_joined_to_details

)

select * from final
```

---

## 4. Macros de sélection et de clé

### `dbt_utils.star` : seulement pour exclure des colonnes

`star` liste toutes les colonnes d'une relation sauf celles de `except`. On ne l'utilise **que s'il y a
des colonnes à exclure** ; sinon, `select *` est plus simple.

```sql
source as (

    select
        {{ dbt_utils.star(
            from=source('jobup', 'raw_job_detail'),
            except=['schema_version', 'content_type']
        ) }}
    from {{ source('jobup', 'raw_job_detail') }}

),
```

À ne pas faire :

```sql
-- star without except: write select * instead
select {{ dbt_utils.star(from=source('jobup', 'raw_job_detail')) }}
from {{ source('jobup', 'raw_job_detail') }}
```

### Clé de synthèse

```sql
---------- ids
{{ dbt_utils.generate_surrogate_key(['url', 'raw_hash']) }}
    as job_detail_id,
```

À n'utiliser que si aucune colonne existante n'est unique à la granularité du modèle.

---

## 5. Tests

### Règles

- Chaque modèle a sa clé primaire testée `unique` et `not_null`.
- Clé YAML `data_tests:` (pas l'ancienne clé `tests:`).
- Les tests génériques à paramètres passent leurs paramètres sous `arguments:` (syntaxe dbt actuelle,
  imposée par le flag `require_generic_test_arguments_property`).

```yaml
columns:
  - name: payload_format
    data_type: varchar
    description: "Format of the raw block: json_ld or paragraphs."
    data_tests:
      - not_null
      - accepted_values:
          arguments:
            values: ["json_ld", "paragraphs"]
```

### Test `is_not_empty` : garde-fou contre un modèle vide

Fichier `macros/test_is_not_empty.sql` : le test échoue si le modèle ne renvoie aucune ligne.

```sql
{% test is_not_empty(model) %}

select 1
from {{ model }}
having count(*) = 0

{% endtest %}
```

Il se pose au niveau du modèle, pas d'une colonne. Typiquement sur un modèle dont un résultat vide aurait
des effets en aval (clusters calculés sur rien, tableau de bord vide sans alerte) :

```yaml
models:
  - name: skills__clusters
    description: "One row per skill cluster and period."
    data_tests:
      - is_not_empty  # empty result = run stopped, nothing published downstream
    columns:
      - name: cluster_id
        ...
```

### Test `null_threshold`

Fichier `macros/test_null_threshold.sql` : échoue si la valeur d'une colonne (un pourcentage de nulls,
par exemple) dépasse un seuil.

```sql
{%- test null_threshold(model, column_name, min_null_threshold) %}
    -- Empty result = test passes, any row = test fails
    select {{ column_name }} as null_percentage
    from {{ model }}
    where {{ column_name }} > {{ min_null_threshold }}

{% endtest %}
```

```yaml
- name: title_null_percentage
  data_type: double
  description: "Share of job details without title, in percent."
  data_tests:
    - null_threshold:
        arguments:
          min_null_threshold: 5
```

---

## 6. Documentation (`.yml`)

- **Chaque modèle et chaque colonne** a une `description` non vide et un `data_type` (types DuckDB :
  `varchar`, `bigint`, `double`, `boolean`, `date`, `timestamp with time zone`, `varchar[]`…).
- Une colonne n'est déclarée qu'une fois par modèle (sans tenir compte de la casse) : sinon dbt garde
  silencieusement la dernière.
- Les colonnes du `.yml` correspondent exactement au `.sql` ; chaque `.sql` a son entrée dans un `.yml`,
  et inversement.
- La description dit ce que contient le modèle, sa granularité (« one row per… ») et les règles
  appliquées.

```yaml
models:
  - name: stg_jobup__job_details
    description: >-
      jobup job detail pages, one row per page (url, raw_hash), latest
      extraction only.
    columns:
      - name: job_detail_id
        data_type: varchar
        description: "Surrogate key of the page: url and raw_hash."
        data_tests:
          - unique
          - not_null
      - name: fetched_at
        data_type: timestamp with time zone
        description: "When the page was downloaded, in UTC."
```

### Sources (`src_<source>.yml`)

Les tables sources sont les Parquet bruts, lus par DuckDB. Le chemin est **relatif à la racine du
dépôt** (partie 7) : `data/test/…` pour le target `test`, `data/…` pour le target `real`.

```yaml
version: 2

sources:
  - name: jobup
    description: "Raw tables of jobup.ch, as written by the extraction."
    meta:
      external_location: >-
        read_parquet(
        '{{ "data/test" if target.name == "test" else "data" }}/{name}/source=jobup/*/*.parquet',
        union_by_name = true, hive_partitioning = false)
    tables:
      - name: raw_job_info
        description: "One row per job seen on a result page, per run."
      - name: raw_job_detail
        description: "One row per detail page downloaded, with its raw block."
```

`union_by_name` lit ensemble des fichiers de versions de contrat différentes ; le partitionnement hive
est désactivé (la colonne `source` existe déjà, le jour d'écriture n'est pas utile).

### Ordre de travail pour un nouveau staging

Dossier, puis `src_<source>.yml`, puis les `.sql`, puis build, puis `stg_<source>.yml` (types lus avec
`describe` sur les vues construites), puis relecture des descriptions.

---

## 7. Configuration

### Lancer dbt : toujours depuis la racine du dépôt

Le projet est un monolithe : **tous les chemins sont relatifs à la racine du dépôt**, et tout se lance
depuis la racine (extraction, dbt, normalisation, notebooks). Une vue DuckDB garde le chemin relatif de
ses Parquet et le résout au moment où on la lit : lue depuis un autre dossier, elle casse.

```bash
uv run --package jobcompass-transformation dbt deps \
    --project-dir transformation --profiles-dir transformation
uv run --package jobcompass-transformation dbt build \
    --project-dir transformation --profiles-dir transformation --target test
```

- `--package jobcompass-transformation` est obligatoire : depuis la racine, `uv run` seul n'installe que
  le package racine, sans dbt, et lance un autre `dbt` trouvé dans le `PATH` (dbt Fusion, par exemple).

- `profiles.yml` est versionné dans `transformation/` (rien dans `~/.dbt/`). Deux targets :
  - `test` : base `data/test/jobcompass.duckdb`, lit `data/test/` (zone de test) ;
  - `real` : base `data/jobcompass.duckdb`, lit `data/`.
- Les bases `.duckdb` ne sont pas versionnées ; supprimer `data/test/` efface aussi la base de test.

### Où mettre la configuration

- Ce qui concerne tout un dossier va dans `dbt_project.yml` ; ce qui est propre à un modèle va dans le
  modèle, ou dans `dbt_project.yml` sous le nom du modèle pour garder toutes les matérialisations au même
  endroit.
- Le bloc `config(...)` d'un modèle s'écrit sur plusieurs lignes, un paramètre par ligne.
- Matérialisations par défaut : staging et intermédiaires en **vue** (on ne change que si besoin), marts
  en **table**.
- Marts : `+tags` au niveau du dossier de domaine. Un job qui sélectionne `+tag:<tag>` prend aussi tous
  les parents (staging, intermédiaires, snapshots) : le tag ne se pose **que sur les marts**.
- Incrémental qu'on ne doit jamais reconstruire (historique) : `+full_refresh: false`.

### `dbt_project.yml` (squelette)

```yaml
name: "jobcompass"
version: "1.0.0"

profile: "jobcompass"

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]
clean-targets:
  - "target"
  - "dbt_packages"

models:
  jobcompass:
    staging:
      +materialized: view

    intermediate:
      +materialized: view

    marts:
      +materialized: table

      skills:
        +tags: ["skills"]

        # Append-only history, never rebuilt
        skills__clusters_history:
          +materialized: incremental
          +incremental_strategy: append
          +full_refresh: false
          +on_schema_change: append_new_columns

flags:
  require_generic_test_arguments_property: true
  validate_macro_args: true
  send_anonymous_usage_stats: false
```

### `packages.yml`

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.4.1
```

### Snapshots

- `strategy='check'` quand la source n'a pas de date de mise à jour fiable, `strategy='timestamp'`
  sinon.
- `check_cols` sur les **colonnes réelles** à surveiller, pas sur une colonne de hash calculée exprès.
- Syntaxe actuelle : `hard_deletes='invalidate'` (remplace `invalidate_hard_deletes=True`) et `schema=`
  (remplace `target_schema=`).

```sql
{% snapshot jobs__snap_job_offers %}

-- ---------------------------------------------------------------------------
-- Snapshot Name: jobs__snap_job_offers.sql
-- Description: history of the job offers.
-- Rules: new version when the title or the company changes.
--        An offer missing from the source closes the current version.
-- ---------------------------------------------------------------------------

{{
    config(
        schema='jobs',
        unique_key='job_offer_id',
        strategy='check',
        check_cols=['job_title', 'company_name'],
        hard_deletes='invalidate'
    )
}}

with

jobs__job_offers as (

    select
        job_offer_id,
        job_title,
        company_name
    from {{ ref('jobs__job_offers') }}

)

select * from jobs__job_offers

{% endsnapshot %}
```

---

## 8. YAML et Jinja

- YAML : indentation de 2 espaces, éléments de liste indentés sous leur clé, lignes de 80 caractères au
  plus (sauf une chaîne qu'on ne peut pas couper), une ligne vide entre deux éléments de liste qui sont
  des dictionnaires quand ça aide la lecture.
- Arguments de liste en liste explicite (`['other_user']`), même avec un seul élément.
- Jinja : espaces à l'intérieur des délimiteurs (`{{ this }}`, pas `{{this}}`) ; lignes vides pour
  séparer les blocs ; 4 espaces d'indentation à l'intérieur d'un bloc ; lisibilité avant le contrôle des
  espaces du SQL compilé.

---

## 9. Outillage local : SQLFluff, pre-commit, dbt-checkpoint, pytest

Les contrôles tournent avant chaque commit (pre-commit). Les fichiers de configuration sont **dans le
dépôt** ; ce document dit ce qu'ils vérifient, il ne les recopie pas.

| Fichier | Rôle |
|---|---|
| `.pre-commit-config.yaml` (racine) | lance les contrôles ci-dessous, plus ruff pour le Python |
| `transformation/.sqlfluff` | style SQL de dbt Labs, dialecte `duckdb`, templater Jinja |
| `transformation/.sqlfluffignore` | exclut `target/`, `dbt_packages/`, `logs/`, `macros/`, `snapshots/` |
| `transformation/sqlfluff_libs/` | stubs Python des macros `dbt_utils` et `dbt` pour le templater Jinja |
| `.dbt-checkpoint.yaml` (racine) | dossier du projet dbt (`transformation`), suivi d'usage désactivé |
| `transformation/tests_conventions/test_dbt_conventions.py` | conventions que SQLFluff et dbt-checkpoint ne voient pas |

Ce qui est vérifié :

- **SQLFluff** : minuscules, 4 espaces, 80 caractères, virgules en fin de ligne, `as` explicite, pas
  d'alias de table court, `inner join` explicite, `group by` par position. Le templater Jinja donne des
  valeurs factices à `ref`, `source`, `config`, `this` : pas besoin de base ni de `dbt compile`.
- **dbt-checkpoint** (lit `target/manifest.json`, rafraîchi par `dbt parse`) : chaque modèle et chaque
  colonne a une description ; chaque modèle a ses tests `unique` et `not_null` ; noms de modèles conformes
  (`stg_<source>__<entite>`, `int_<domaine>__<entite>`, `<domaine>__<entite>`).
- **pytest** : un `src_<source>.yml` et un `stg_<source>.yml` par dossier de staging ; modèles de staging
  nommés d'après leur dossier, sans jointure, au format `source` / `renamed` ; un `.yml` par modèle
  intermédiaire ou mart ; groupes de colonnes connus et dans l'ordre ; `data_type` présent et nom de
  colonne conforme à son type (booléen `is_` / `has_`, timestamp `_at`, date `_date`).

Installation (une fois), puis lancement sur tout le projet :

```bash
uv add --dev sqlfluff pre-commit pytest pyyaml
uv run pre-commit install
uv run pre-commit run --all-files
```

pre-commit ne voit que les fichiers suivis par Git : `git add` les nouveaux fichiers avant.

---

## 10. Check-list avant chaque commit

- [ ] Noms en `stg_<source>__<entite>`, `int_<domaine>__<entite>_<action>`, `<domaine>__<entite>`.
- [ ] Clé primaire `<objet>_id` testée `unique` + `not_null` ; pas de clé de synthèse si une colonne
      suffit.
- [ ] En-tête `Model Name / Description / Rules`.
- [ ] Staging : `source` / `renamed`, aucune jointure, `select *` sauf colonnes à exclure (`star`).
- [ ] CTE d'import nommées comme le modèle lu, colonnes utiles seulement.
- [ ] Colonnes groupées par type dans l'ordre ids, strings, numerics, arrays, booleans, dates,
      timestamps.
- [ ] Booléens `is_` / `has_`, dates `_date`, timestamps `_at`.
- [ ] SQL en minuscules, jointures explicites sans alias court, pas de `using`.
- [ ] `.yml` : description et `data_type` sur chaque modèle et chaque colonne, `data_tests:` avec
      `arguments:`.
- [ ] dbt lancé depuis la racine du dépôt ; `dbt build --target test` sans erreur.
- [ ] `uv run pre-commit run --all-files` sans erreur.
