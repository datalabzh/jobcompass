# Ajouter un site

Ce guide ajoute un nouveau portail d'emploi, de la collecte jusqu'aux marts. Exemple : un site nommé
`jobsch`. Le modèle à copier est **jobup** : `extraction/src/extraction/jobup/` et
`dbt/models/staging/jobup/`.

Un site touche cinq endroits, toujours les mêmes :

| # | Où | Quoi |
|---|---|---|
| 1 | `extraction/src/extraction/jobsch/` | la collecte : configuration, classe d'extraction, parseur, tests |
| 2 | `config.site` | la déclaration du site |
| 3 | `dbt/models/staging/jobsch/` | le staging : ses tables brutes mises en colonnes |
| 4 | `dbt/models/intermediate/jobs/*_unioned.sql` | le site ajouté aux trois unions |
| 5 | `orchestration/jobcompass.cron` | sa ligne de planification |

La normalisation n'a rien à faire : elle est commune à tous les sites.

## 0. Avant de coder

- Lire le `robots.txt` et les conditions d'utilisation du portail ([ADR-0001](../adr/0001-perimetre-collecte.md)).
  Une API n'est utilisée que si elle est autorisée.
- Repérer où sont les données : les offres d'une page de résultats (souvent un JSON intégré à la page),
  la pagination, et sur une fiche, un bloc JSON-LD de type `JobPosting`.
- Choisir le nom du site : minuscules, chiffres et `_` (`jobsch`). Ce sera le nom du dossier, la valeur de
  `source` dans les tables et le `site_name` dans dbt.
- Enregistrer une page de résultats et une fiche réelles : elles serviront de fixtures aux tests.

## 1. La collecte

Créer le dossier `extraction/src/extraction/jobsch/` :

```
jobsch/
├── __init__.py                 vide
├── site.toml                   la configuration
├── jobsch_extraction_uc.py     la classe d'extraction
├── jobsch_parser.py            le parseur
└── tests/
    ├── fixtures/               une page de résultats et une fiche réelles
    ├── test_jobsch_parser.py
    └── test_jobsch_extraction_uc.py
```

### `site.toml`

Copier celui de jobup et adapter :

```toml
[db_storage]
class = "storage.postgres_db_storage:PostgresDbStorage"

[file_storage]
class = "storage.s3_file_storage:S3FileStorage"

[extraction]
class = "extraction.jobsch.jobsch_extraction_uc:JobschExtractionUseCase"
min_delay_between_requests = 1.0   # politesse, en secondes
max_pages = 1                      # limite de test : pages de résultats par catégorie
max_jobs = 2                       # limite de test : fiches téléchargées

[extraction.options]               # propre au site, validé par sa classe
categories = ["informatique"]
```

### Le parseur (`jobsch_parser.py`)

Une classe qui hérite de `IParser` (`extraction/interfaces/i_parser.py`) :

- attributs `name` et `version` (obligatoires : sinon la classe est refusée au chargement) ;
- une seule méthode publique, `parse(kind, content)`, qui **lit sans jamais télécharger ni écrire** ;
- `kind` = le type de page, fixé par le site (jobup : `job_info` pour une page de résultats, `job_detail`
  pour une fiche) ;
- contenu illisible : lever `ParsingError`.

Pour une fiche, le parseur rend le **bloc brut** ([ADR-0002](../adr/0002-elt-brut-minimal-dbt.md)) : le JSON-LD
du `JobPosting` tel quel (`PayloadFormat.JSON_LD`), sinon la liste des paragraphes du texte
(`PayloadFormat.PARAGRAPHS`). **Aucun champ choisi ni renommé** : c'est le travail de dbt. Le parseur de jobup
fait exactement cela et peut être repris presque tel quel.

### La classe d'extraction (`jobsch_extraction_uc.py`)

Une classe `JobschExtractionUseCase` qui hérite de `ISiteExtractionUseCase`
(`extraction/interfaces/i_site_extraction_uc.py`). Elle reçoit tout à sa création (stockages, `get_page`,
`is_test`, limites, `now`, options du `site.toml`) et n'a qu'une méthode publique, `execute()`, qui rend un
`ExtractionReport`.

Les noms sont vérifiés dès le chargement : la classe doit finir par `UseCase` et le fichier par `_uc.py`.

Ce qu'elle doit faire, comme jobup :

1. **Valider ses options** (un modèle Pydantic, comme `JobupOptions`) avant toute requête.
2. **Pour chaque catégorie** : un `run_id` (UUID), les pages de résultats de la première à la dernière (au
   plus `max_pages`), une ligne `RawJobInfo` par offre vue (avec sa carte JSON brute et
   `listing_params={"category": ...}`), puis **toujours** un `LogRawJobInfo` à la fin : `completed`, ou
   `failed` avec l'erreur. Une catégorie en échec n'arrête pas les autres.
3. **Pour les fiches** : offres vues − déjà téléchargées − mises de côté (`max_failures`), au plus
   `max_jobs`, **une par une**, chacune écrite aussitôt :
    - succès : le HTML dans le stockage de fichiers, sous `raw_job_detail_html/<hash_html_id>.html`
      (`compute_hash_html_id`), puis un `RawJobDetail` avec le bloc du parseur ;
    - échec : un `LogRawJobDetail`.
4. Écrire dans les tables du catalogue (`Table.RAW_JOB_INFO`…), avec les contrats communs, et passer
   `is_test` partout.
5. Télécharger uniquement avec `get_page` : il applique le user agent et le délai de politesse.
6. Déclarer `name` et `version` (ex. `jobsch_extraction`, `0.1.0`), écrits dans `scraper` et
   `scraper_version`. Format `x.y.z`, chiffres seulement.

Le plus simple est de copier `jobup_extraction_uc.py` et de changer ce qui est propre au site : l'URL des
pages de résultats, la pagination, la lecture des offres.

### Les tests

Les tests vivent à côté du code (`jobsch/tests/`) et utilisent les outils de `extraction/conftest.py` :
`FakeGetPage` simule le réseau avec tes fixtures, la fixture `storages` donne les vrais stockages de test.
S'inspirer de `jobup/tests/`. Voir [Conventions des tests](../conventions/tests.md).

```bash
(cd extraction && uv run pytest -q)
```

### Premier passage, en test

```bash
uv run --package jobcompass-entrypoints jobcompass-extraction run jobsch
```

Vérifier dans `jobcompass_dev` : `raw.raw_job_info`, `raw.log_raw_job_info` (`status = 'completed'`) et
`raw.raw_job_detail` ont des lignes avec `source = 'jobsch'`.

## 2. Déclarer le site

Ajouter la ligne dans les **deux bases** :

```bash
for db in jobcompass jobcompass_dev; do
docker compose -f infra/docker-compose.yml exec -T postgres psql -U jobcompass -d $db -c \
  "insert into config.site (site_name, description) values ('jobsch', 'jobs.ch, job portal of Switzerland.');"
done
```

Et l'ajouter au script d'initialisation `infra/postgres/init/schema/03_config_tables.sql` (dans
l'`insert into config.site`), pour les nouvelles installations.

## 3. Le staging dbt

Créer `dbt/models/staging/jobsch/`, en copiant `staging/jobup/` :

| Fichier | Contenu |
|---|---|
| `src_jobsch.yml` | la source `jobsch` : les mêmes tables brutes, schéma `raw` |
| `stg_jobsch__job_infos.sql` | les offres vues : `where source = 'jobsch'`, la carte lue en colonnes |
| `stg_jobsch__job_info_runs.sql` | les passages |
| `stg_jobsch__job_details.sql` | les fiches, dernière extraction seulement, le JSON-LD lu en colonnes |
| `stg_jobsch.yml` | descriptions et tests de chaque colonne |

Ce qui change d'un site à l'autre, ce sont les **clés JSON** lues (la carte de jobup a `title`,
`company.name`, `place`…). Ce qui ne change pas, ce sont **les colonnes de sortie**, que les unions
attendent, dans cet ordre :

| Modèle | Colonnes attendues par l'union |
|---|---|
| `stg_<site>__job_infos` | `hash_job_info_id`, `hash_job_id`, `run_id`, `job_url`, `site_name`, `job_category`, `job_title`, `company_name`, `job_place`, `initial_published_at`, `published_at`, `seen_at` |
| `stg_<site>__job_info_runs` | `run_id`, `site_name`, `job_category`, `run_status`, `started_at`, `finished_at` |
| `stg_<site>__job_details` | `hash_job_detail_id`, `hash_job_id`, `hash_html_id`, `job_url`, `site_name`, `payload_format`, `job_title`, `company_name`, `job_description`, `posted_date`, `fetched_at` |

Une clé absente du site donne une colonne `null` (ex. `null::text as job_place`). Les identifiants se
calculent comme pour jobup (`dbt_utils.generate_surrogate_key`), pour rester uniques entre sites.

## 4. Les unions

Dans chacun des trois modèles `dbt/models/intermediate/jobs/int_jobs__*_unioned.sql`, ajouter un CTE pour le
site et une ligne `union all` :

```sql
stg_jobsch__job_infos as (

    select
        hash_job_info_id,
        ...                    -- mêmes colonnes, même ordre que jobup
    from {{ ref('stg_jobsch__job_infos') }}

),

unioned as (

    select * from stg_jobup__job_infos
    union all
    select * from stg_jobsch__job_infos

)
```

Rien d'autre ne change : `is_active`, les marts et les compétences s'appliquent au nouveau site.

```bash
uv run --env-file infra/.env --package jobcompass-dbt dbt build --project-dir dbt --profiles-dir dbt --target dev
```

Le test `relationships` sur `site_name` échoue si l'étape 2 a été oubliée.

## 5. La planification

Ajouter une ligne dans `orchestration/jobcompass.cron`, à une heure où dbt n'a pas encore tourné :

```
30 4 * * * bash /app/orchestration/run_site.sh jobsch
```

Puis reconstruire l'image (nouveau code) : `docker compose -f infra/docker-compose.yml up -d --build pipeline`.

## Check-list

- [ ] `robots.txt` et conditions d'utilisation lus
- [ ] `extraction/src/extraction/<site>/` : `site.toml`, classe `…UseCase` dans un fichier `…_uc.py`, parseur, tests
- [ ] tests de l'extraction verts
- [ ] passage de test : lignes dans les quatre tables brutes, `completed` dans `log_raw_job_info`
- [ ] ligne dans `config.site` (deux bases) et dans `03_config_tables.sql`
- [ ] staging : trois modèles aux colonnes attendues, `.yml` complet
- [ ] le site ajouté aux trois modèles `*_unioned`
- [ ] `dbt build` vert, `pre-commit run --all-files` vert
- [ ] ligne dans `orchestration/jobcompass.cron`
