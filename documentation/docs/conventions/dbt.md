# Conventions dbt : règles à respecter dans ce projet

Ce document fixe les conventions dbt de JobCompass. Elles s'appuient sur les guides de dbt Labs :

- [How we structure our dbt projects](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- [How we style our dbt models](https://docs.getdbt.com/best-practices/how-we-style/1-how-we-style-our-dbt-models)
- [How we style our SQL](https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql)

**Consigne pour Claude** : appliquer toutes ces règles à chaque modèle, `.yml`, macro ou snapshot écrit
dans ce projet.

**Langue** : en-têtes de modèles, commentaires SQL et descriptions des `.yml` en anglais.

Dans ce document, `<source>` désigne une source de données (un site : `jobup`…), `<domaine>` un domaine
métier (`jobs`, `skills`…), `<entite>` l'objet décrit par un modèle (`job_details`, `clusters`…).

Le projet dbt est dans `dbt/` ; la base est **PostgreSQL** ; les sources sont les tables brutes
déposées par l'extraction et la normalisation Python (schéma `raw`), plus
la table de configuration `config.normalizer` (ADR-0002). Les règles métier des modèles existants sont
en partie 11.

---

## 1. Couches, dossiers et nommage des fichiers

### Trois couches

| Couche | Rôle | Préfixe du modèle | Matérialisation par défaut |
|---|---|---|---|
| `staging` | une source, mise à plat et renommée, sans jointure | `stg_` | vue |
| `intermediate` | jointures, calculs, étapes de préparation | `int_` | vue |
| `marts` | produits finaux lus par l'analyse ou les applications | aucun | table |

Bronze = les tables brutes de Postgres (sources) ; silver = staging et intermédiaires ; gold = marts.
Deux bases, avec les mêmes schémas : `jobcompass` (vraies données, target `real`) et `jobcompass_dev`
(zone de test : passages limités et tests automatiques, target `dev`). Dans chacune : `raw` et `config`
(lus), `staging`, `intermediate` et `marts` (écrits par dbt, sans préfixe : macro
`generate_schema_name`).

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
dbt/
  dbt_project.yml
  profiles.yml
  packages.yml
  models/
    staging/
      jobup/                        # une source = un site...
        src_jobup.yml
        stg_jobup.yml
        stg_jobup__job_infos.sql
        stg_jobup__job_info_runs.sql
        stg_jobup__job_details.sql
      normalization/                # ... ou une brique commune à tous les sites
        src_normalization.yml
        stg_normalization.yml
        stg_normalization__normalized_jobs.sql
      config/                       # ... ou les tables de configuration
        src_config.yml
        stg_config.yml
        stg_config__normalizers.sql
    intermediate/
      jobs/
        int_jobs__job_infos_aggregated.sql
        int_jobs__job_infos_aggregated.yml
      skills/
        int_skills__normalized_skills_unnested.sql
        int_skills__normalized_skills_unnested.yml
    marts/
      jobs/
        jobs__job_offers.sql
        jobs__job_offers.yml
      skills/
        skills__job_skills.sql
        skills__job_skills.yml
  snapshots/
  macros/
    generate_schema_name.sql        # schéma = couche, sans préfixe
    generate_schema_name.yml
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
- **Une clé primaire par modèle**, de type texte, testée `unique` et `not_null`.
- **Nommage des clés** : `hash_<objet>_id` quand la clé est un hash, `<objet>_id` sinon (ex. `run_id`).
  Le même nom partout pour le même objet (`hash_job_id` dans tous les modèles, jamais `id`).
- **Un seul hash est calculé en Python** : `hash_html_id`, l'empreinte SHA-256 du HTML d'une page (le
  nom de son fichier dans RustFS). **Tous les autres** `hash_<objet>_id` sont calculés **dans dbt**, avec
  `dbt_utils.generate_surrogate_key` (MD5 de colonnes concaténées) ; jamais de hash calculé à la main ni
  en Python. Les tables brutes n'ont pas de hash : leur unicité porte sur des colonnes.

| Clé | Colonnes hachées | Ce qu'elle identifie |
|---|---|---|
| `hash_html_id` (Python) | contenu HTML (SHA-256) | le HTML d'une page |
| `hash_job_id` | `source`, `url` | une offre |
| `hash_job_info_id` | `run_id`, `source`, `url` | une offre vue lors d'un passage |
| `hash_job_detail_id` | `hash_html_id`, `scraper`, `scraper_version` | une extraction d'une page |
| `hash_normalized_job_id` | les trois précédentes + `normalizer`, `normalizer_version`, `model`, `model_version` | une normalisation d'une extraction |
| `hash_normalizer_id` | `normalizer`, `normalizer_version` | un normaliseur |
| `hash_normalized_skill_id` | `hash_normalized_job_id`, `canonical_skill` | une compétence d'une normalisation |
| `hash_job_skill_id` | `hash_job_id`, `canonical_skill` | une compétence d'une offre |

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

Les hash et le JSON brut (`jsonb`) sont rangés en `strings`. Pas de groupe qui mélange les types (pas de
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

- Une ligne par objet : quand la source en a plusieurs versions, garder la bonne dès la CTE `source`
  (`distinct on` en Postgres, voir partie 11).

```sql
-- ---------------------------------------------------------------------------
-- Model Name: stg_jobup__job_details.sql
-- Description: jobup job detail pages, one row per page (job_url), latest
--              extraction only, JSON-LD keys read into columns.
-- Rules: no join. Latest extraction of a page: highest scraper_version,
--        compared number by number (0.10.0 after 0.9.0), then latest
--        fetched_at. Columns read from the JSON-LD are null for paragraphs
--        pages (the listing card is used downstream).
-- ---------------------------------------------------------------------------

with

source as (

    select distinct on (url) *
    from {{ source('jobup', 'raw_job_detail') }}
    where source = 'jobup'
    {# The latest extraction of each page: distinct on needs named columns #}
    order by  -- noqa: AM06
        url asc,
        string_to_array(scraper_version, '.')::int[] desc,
        fetched_at desc

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(
            ['hash_html_id', 'scraper', 'scraper_version']
        ) }} as hash_job_detail_id,
        {{ dbt_utils.generate_surrogate_key(['source', 'url']) }}
            as hash_job_id,
        hash_html_id,

        ---------- strings
        url as job_url,
        payload_format,
        payload ->> 'title' as job_title,
        payload -> 'hiringOrganization' ->> 'name' as company_name,

        ---------- dates
        case
            when pg_input_is_valid(left(payload ->> 'datePosted', 10), 'date')
                then left(payload ->> 'datePosted', 10)::date
        end as posted_date,

        ---------- timestamps
        fetched_at

    from source

)

select * from renamed
```

- Lecture du JSON en Postgres : `->` (objet), `->>` (texte). Conversion d'un texte qui peut être
  illisible : `case when pg_input_is_valid(<texte>, '<type>') then <texte>::<type> end` (Postgres n'a
  pas de `try_cast`).

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
        {{ dbt_utils.generate_surrogate_key(['job_url']) }} as hash_job_id,

        ---------- strings
        job_url,
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
{{ dbt_utils.generate_surrogate_key(['source', 'url']) }}
    as hash_job_id,
```

Toutes les clés `hash_<objet>_id` se calculent ainsi (partie 2), y compris dans les intermédiaires et
les marts.

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
    data_type: text
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

- **Chaque modèle et chaque colonne** a une `description` non vide et un `data_type` (types Postgres :
  `text`, `integer`, `bigint`, `boolean`, `date`, `timestamp with time zone`, `jsonb`…), lu dans
  `information_schema.columns` sur les vues construites.
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
      jobup job detail pages, one row per page (job_url), latest
      extraction only.
    columns:
      - name: hash_job_detail_id
        data_type: text
        description: >-
          Key of the page extraction: hash of hash_html_id, scraper and
          scraper_version.
        data_tests:
          - unique
          - not_null
      - name: fetched_at
        data_type: timestamp with time zone
        description: "When the page was downloaded, in UTC."
```

### Sources (`src_<source>.yml`)

Les tables sources sont les tables brutes de Postgres, schéma `raw` (la base dépend du target : `dev`
ou `real`). Les tables brutes contiennent tous les sites : un staging de site
garde `source = '<site>'` dès sa CTE `source`. Un test qui porte sur la donnée brute elle-même (format
d'une colonne) se pose sur la source.

```yaml
version: 2

sources:
  - name: jobup
    description: "Raw tables of the extraction, read for jobup.ch."
    schema: raw
    tables:
      - name: raw_job_detail
        description: >-
          One row per extraction of a detail page by a version of the scraper,
          with its raw block (RawJobDetail).
        columns:
          - name: scraper_version
            data_tests:
              - not_null
              - dbt_utils.expression_is_true:
                  arguments:
                    expression: "~ '^[0-9]+\\.[0-9]+\\.[0-9]+$'"
```

### Ordre de travail pour un nouveau staging

Dossier, puis `src_<source>.yml`, puis les `.sql`, puis build, puis `stg_<source>.yml` (types lus avec
`describe` sur les vues construites), puis relecture des descriptions.

---

## 7. Configuration

### Lancer dbt : toujours depuis la racine du dépôt

Le projet est un monolithe : tout se lance depuis la racine du dépôt. La connexion est lue dans les
variables `POSTGRES_*` de `infra/.env`, chargées par `uv run --env-file` ; les conteneurs doivent tourner
(`docker compose -f infra/docker-compose.yml up -d --wait`).

```bash
uv run --package jobcompass-dbt dbt deps \
    --project-dir dbt --profiles-dir dbt
uv run --env-file infra/.env --package jobcompass-dbt dbt build \
    --project-dir dbt --profiles-dir dbt --target dev
```

- `--package jobcompass-dbt` est obligatoire : depuis la racine, `uv run` seul n'installe que
  le package racine, sans dbt, et lance un autre `dbt` trouvé dans le `PATH` (dbt Fusion, par exemple).
- `profiles.yml` est versionné dans `dbt/` (rien dans `~/.dbt/`). Deux targets :
  - `dev` : base `jobcompass_dev` (zone de test) ;
  - `real` : base `jobcompass` (vraies données).
  - Dans les deux : lit `raw` et `config`, écrit dans `staging`, `intermediate`, `marts`.
- Les valeurs par défaut du profil ne servent qu'à `dbt parse` (pre-commit), qui ne se connecte pas.

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
        unique_key='hash_job_id',
        strategy='check',
        check_cols=['job_title', 'company_name'],
        hard_deletes='invalidate'
    )
}}

with

jobs__job_offers as (

    select
        hash_job_id,
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

## 9. Outillage local : SQLFluff, pre-commit, dbt-checkpoint

Les contrôles tournent avant chaque commit (pre-commit). Les fichiers de configuration sont **dans le
dépôt** ; ce document dit ce qu'ils vérifient, il ne les recopie pas.

| Fichier | Rôle |
|---|---|
| `.pre-commit-config.yaml` (racine) | lance les contrôles ci-dessous, plus ruff pour le Python ; versions figées (`rev`) |
| `pre-commit/.sqlfluff` | style SQL de dbt Labs, dialecte `postgres`, templater Jinja ; passé aux hooks par `--config` ; ST06 désactivée (les colonnes sont groupées par type) |
| `pre-commit/sqlfluff_libs/dbt_utils.py` | macros `dbt_utils` simulées pour le templater Jinja |
| `.dbt-checkpoint.yaml` (racine) | dossier du projet dbt (`dbt`), suivi d'usage désactivé |

Ce qui est vérifié :

- **SQLFluff** : minuscules, 4 espaces, 80 caractères, virgules en fin de ligne, `as` explicite, pas
  d'alias de table court, `inner join` explicite, `group by` par position. Le templater Jinja donne des
  valeurs factices à `ref`, `source`, `config`, `this` (`apply_dbt_builtins`) et aux macros `dbt_utils`
  (`sqlfluff_libs/`) : pas besoin de base ni de `dbt compile`. SQLFluff tourne dans l'environnement de
  pre-commit : ce n'est pas une dépendance uv.
- **dbt parse** (hook local) : rafraîchit le manifest avec le dbt du projet
  (`uv run --package jobcompass-dbt`).
- **dbt-checkpoint** (lit `target/manifest.json`, rafraîchi par `dbt parse`) : chaque modèle et chaque
  colonne a une description ; chaque modèle a ses tests `unique` et `not_null` ; noms de modèles conformes
  (`stg_<source>__<entite>`, `int_<domaine>__<entite>`, `<domaine>__<entite>`).
- **Plus tard, si le besoin vient** (plusieurs sites ou développeurs) : un test pytest des conventions
  que ni SQLFluff ni dbt-checkpoint ne voient (fichiers `src_` / `stg_` par dossier, format `source` /
  `renamed`, groupes de colonnes dans l'ordre, nom de colonne conforme à son type).

Installation (une fois), puis lancement sur tout le projet :

```bash
uv add --dev pre-commit
uv run pre-commit install
uv run pre-commit run --all-files
```

Correction automatique du SQL (hook manuel, jamais lancé au commit) :

```bash
uv run pre-commit run sqlfluff-fix --all-files --hook-stage manual
```

pre-commit ne voit que les fichiers suivis par Git : `git add` les nouveaux fichiers avant.

---

## 10. Check-list avant chaque commit

- [ ] Noms en `stg_<source>__<entite>`, `int_<domaine>__<entite>_<action>`, `<domaine>__<entite>`.
- [ ] Clé primaire testée `unique` + `not_null` ; clés hachées en `hash_<objet>_id`, calculées par
      `dbt_utils.generate_surrogate_key`.
- [ ] En-tête `Model Name / Description / Rules`.
- [ ] Staging : `source` / `renamed`, aucune jointure, `select *` sauf colonnes à exclure (`star`).
- [ ] CTE d'import nommées comme le modèle lu, colonnes utiles seulement.
- [ ] Colonnes groupées par type dans l'ordre ids, strings, numerics, arrays, booleans, dates,
      timestamps.
- [ ] Booléens `is_` / `has_`, dates `_date`, timestamps `_at`.
- [ ] SQL en minuscules, jointures explicites sans alias court, pas de `using`.
- [ ] `.yml` : description et `data_type` sur chaque modèle et chaque colonne, `data_tests:` avec
      `arguments:`.
- [ ] dbt lancé depuis la racine du dépôt avec `--env-file infra/.env` ; `dbt build --target dev`
      sans erreur.
- [ ] `uv run pre-commit run --all-files` sans erreur.

---

## 11. Règles métier des modèles

Les règles appliquées par les modèles existants, à garder en tête (et dans le README) :

- **Une offre** = (`source`, `url`), clé `hash_job_id`. Elle n'est téléchargée qu'une fois ; on ne suit
  pas ses modifications.
- **Présence** (`int_jobs__job_infos_aggregated`) : `first_seen_at` / `last_seen_at` = première et
  dernière apparition dans les listes. `is_active` = vue dans le **dernier passage terminé**
  (`completed`) d'au moins une de ses catégories : un passage en échec ne fait jamais disparaître
  d'offres.
- **Dernière extraction d'une page** (`stg_jobup__job_details`) : la plus haute `scraper_version`,
  **comparée nombre par nombre** (`string_to_array(scraper_version, '.')::int[]`, `0.10.0` après
  `0.9.0`), puis le `fetched_at` le plus récent. Les versions s'écrivent toujours `x.y.z`, chiffres
  seulement : vérifié par un test sur la source.
- **Titre, entreprise, date de publication** (`jobs__job_offers`) : du JSON-LD de la page quand il
  existe, sinon de la carte du listing (dernière apparition). Jamais d'analyse du HTML : dbt lit des
  clés, il n'analyse pas de texte.
- **Normaliseur** : seules les normalisations du normaliseur courant (`config.normalizer`, nom et
  version) sont retenues ; plusieurs modèles du même normaliseur sur une page : la plus récente.
- **Compétences** (`skills__job_skills`) : une ligne par offre et par compétence canonique, avec
  `first_seen_date` / `last_seen_date`, **sans regroupement** : les comptes par jour, semaine ou mois
  se calculent à partir de ce modèle.
- **`distinct on`** (choisir une ligne par objet) exige un `order by` sur des colonnes nommées :
  `-- noqa: AM06` sur cette ligne seulement.
