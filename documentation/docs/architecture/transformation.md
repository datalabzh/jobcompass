# Transformation (dbt)

dbt assemble les tables brutes en tables d'analyse, uniquement en SQL. Il ne parse jamais de texte : il lit
des clés JSON, joint et agrège.

## Les couches

```
sources (raw, config)
   │
   ▼
staging         un dossier par source, une vue par table brute, sans jointure
   │              stg_jobup__job_infos, stg_jobup__job_info_runs, stg_jobup__job_details
   │              stg_normalization__normalized_jobs, stg_config__normalizers, stg_config__sites
   ▼
intermediate    assemblage des sites, puis jointures et regroupements (vues)
   │              int_jobs__job_infos_unioned, int_jobs__job_info_runs_unioned,
   │              int_jobs__job_details_unioned           (tous les sites réunis)
   │              int_jobs__job_infos_aggregated          (une ligne par offre, is_active)
   │              int_skills__normalized_skills_unnested  (une ligne par compétence)
   ▼
marts           produits finaux (tables)
                  jobs__job_offers, skills__job_skills
```

Règles d'écriture : [Conventions dbt](../conventions/dbt.md).

### Staging : un dossier par site

Les tables brutes sont communes à tous les sites (colonne `source`), mais chaque site a son propre format
de carte et de JSON-LD. Chaque site a donc son staging (`dbt/models/staging/<site>/`), qui lit ses lignes
(`where source = '<site>'`) et les met en colonnes. **Tous les stagings de sites sortent les mêmes
colonnes** : c'est ce qui permet de les réunir.

### Intermediate : les sites réunis

Les trois modèles `int_jobs__*_unioned` réunissent les sites avec `union all` : un CTE par site. Ensuite,
toute la logique métier (offre active, dernière fiche, compétences) est écrite **une seule fois**, pour
tous les sites.

Chaque `site_name` doit être déclaré dans la table `config.site` : un test `relationships` fait échouer
`dbt build` sinon.

## Les marts

### `marts.jobs__job_offers` : une ligne par offre

Présence de l'offre (`first_seen_at`, `last_seen_at`, `runs_seen`, `is_active`), titre, entreprise, lieu,
date de publication, description, et `hash_html_id` de sa dernière fiche. Titre, entreprise et date viennent
du JSON-LD de la fiche quand il existe, sinon de la carte. Les offres jamais téléchargées sont gardées
(`has_detail = false`).

### `marts.skills__job_skills` : une ligne par offre et par compétence

Les compétences de la dernière fiche de chaque offre, d'après le normaliseur courant, avec la forme
canonique et brute, l'origine, `is_active` et les jours de première et dernière apparition. Pas
d'agrégation : les comptes par jour, semaine ou mois se calculent à partir de cette table.

### Exemples

```sql
-- Les 20 compétences les plus demandées parmi les offres en ligne
select canonical_skill, count(*) as offres
from marts.skills__job_skills
where is_active
group by 1
order by 2 desc
limit 20;

-- Nouvelles offres par semaine
select date_trunc('week', first_seen_at) as semaine, count(*) as offres
from marts.jobs__job_offers
group by 1
order by 1;

-- Retrouver le HTML d'origine d'une offre : son hash_html_id est le nom du fichier
-- dans RustFS (raw_job_detail_html/<hash_html_id>.html)
select job_url, hash_html_id from marts.jobs__job_offers where job_title ilike '%data engineer%';
```

## Le catalogue des colonnes

Chaque modèle et chaque colonne sont décrits dans les fichiers `.yml` à côté des modèles (c'est vérifié
avant chaque commit). Pour les consulter sous forme de site, avec le graphe des dépendances :

```bash
uv run --env-file infra/.env --package jobcompass-dbt dbt docs generate --project-dir dbt --profiles-dir dbt --target dev
uv run --package jobcompass-dbt dbt docs serve --project-dir dbt --profiles-dir dbt --port 8080
```

## Lancer dbt

Toujours depuis la racine du dépôt :

```bash
uv run --env-file infra/.env --package jobcompass-dbt dbt build --project-dir dbt --profiles-dir dbt --target dev
```

`--target dev` (base de test) ou `--target real` (production). `dbt build` construit les modèles et lance
leurs tests ; `--select <modèle>+` limite à un modèle et à ce qui en dépend.

Pour ajouter un modèle : [Ajouter un modèle dbt](../guides/ajouter-un-modele-dbt.md).
