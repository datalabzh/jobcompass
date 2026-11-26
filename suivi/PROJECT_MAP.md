# JobCompass — carte

## En une phrase
Collecte les offres d'emploi de Suisse romande (jobup.ch pour l'instant, plusieurs sites prévus), en extrait
les compétences et les met à disposition en SQL, pour construire des clusters de compétences indépendants des
intitulés de poste.

## Flux (schéma)
```
<site> ──(run_site.sh <site> : jobcompass-extraction run <site>)──► raw.raw_job_info    + raw.log_raw_job_info
                                                            ├──► raw.raw_job_detail  + raw.log_raw_job_detail
                                                            └──► HTML brut → RustFS (jobcompass-raw, par hash_html_id)
raw.raw_job_detail ──(puis jobcompass-normalization run <site>)──► raw.normalized_job

dbt build (run_dbt.sh) : staging (vues) → intermediate (vues) → marts (tables)
  stg_<site>__job_infos / __job_info_runs / __job_details   (un dossier par site, mêmes colonnes de sortie)
      ─► int_jobs__job_infos_unioned, int_jobs__job_info_runs_unioned, int_jobs__job_details_unioned
      ─► int_jobs__job_infos_aggregated (is_active par site et catégorie) ─┐
  stg_normalization__normalized_jobs + stg_config__normalizers             ├─► marts.jobs__job_offers
      ─► int_skills__normalized_skills_unnested ───────────────────────────┴─► marts.skills__job_skills
  stg_config__sites : registre des sites (test relationships sur site_name)
```
Orchestration : conteneur `pipeline` (supercronic) ; `orchestration/jobcompass.cron` = une ligne par site
(`run_site.sh <site>`, jobup à 4 h) puis une ligne dbt (`run_dbt.sh`, 7 h). Mode : `orchestration/.env`.

## Objets
| Objet | Type | Rôle en 1 ligne | Écrit par |
|---|---|---|---|
| raw.raw_job_info | Table | Une offre vue sur une page de résultats, par run (carte brute en jsonb) | extraction |
| raw.log_raw_job_info | Table | Journal d'un run par catégorie (`completed` / `failed`, totaux) | extraction |
| raw.raw_job_detail | Table | Une page de détail téléchargée : bloc brut `json_ld` ou `paragraphs` | extraction |
| raw.log_raw_job_detail | Table | Un échec de téléchargement d'une page de détail | extraction |
| raw.normalized_job | Table | Compétences d'une page, signées par normaliseur + modèle (versions) | normalisation |
| config.normalizer | Table | Normaliseurs connus ; un seul `is_current` | à la main |
| config.site | Table | Registre des sites connus ; dbt refuse un site absent | à la main |
| RustFS `jobcompass-raw` | Objet S3 | HTML brut immuable, nommé par `hash_html_id` | extraction |
| JobupExtractionUseCase | Classe | Extraction jobup (job infos puis job details), réglée par `site.toml` | — |
| FakeNormalizationUseCase | Classe | Normaliseur factice (déclarées + ~30 mots-clés) ; saute les fiches illisibles | — |
| ExtractionSettings | Classe | Réglages communs de l'extraction, lus dans `extraction/.env` | — |
| marts.jobs__job_offers | Table dbt | Une ligne par offre, tous sites : présence, `is_active`, dernière fiche, `hash_html_id` | dbt |
| marts.skills__job_skills | Table dbt | Une ligne par offre et compétence canonique, jours vus, `hash_html_id` | dbt |
| orchestration/run_site.sh | Script | Extraction puis normalisation d'un site | — |
| orchestration/run_dbt.sh | Script | `dbt build`, une fois, pour tous les sites | — |
| orchestration/common.sh | Script | Mode (test / full), logs, partagés par les deux scripts | — |
| orchestration/jobcompass.cron | Fichier | Heures : une ligne par site, une ligne dbt (heure de Zurich) | à la main |
| Service `pipeline` | Conteneur | Image `orchestration/Dockerfile`, supercronic, `orchestration/` monté en volume | — |

Bases : `jobcompass` (target `real`) et `jobcompass_dev` (target `dev`, zone de test), mêmes schémas.
Ports de Postgres et RustFS publiés sur `127.0.0.1` seulement.

## Décisions clés (le « pourquoi »)
Détail dans `documentation/docs/adr/` (ADR-0001 à 0008).
- 2026-11-18 : ELT — Python dépose le brut, dbt transforme (ADR-0002) ; pas d'outil sans besoin concret.
- 2026-11-19 : Postgres et RustFS en conteneurs à la place de Parquet/DuckDB et MinIO (ADR-0003).
- 2026-11-19 : le SQL ne parse jamais de texte ; la normalisation Python lit job detail et écrit normalized_job.
- 2026-11-19 : un seul hash en Python (`hash_html_id`), les autres `hash_<objet>_id` en staging dbt (ADR-0004).
- 2026-11-19 : normaliseur courant dans `config.normalizer` ; normalisations versionnées (ADR-0006).
- 2026-11-20 : zone de test = base séparée `jobcompass_dev`, test par défaut (ADR-0005).
- 2026-11-25 : planification par supercronic dans un conteneur (ADR-0007) ; chaque dossier garde ses variables.
- 2026-11-25 : `hash_html_id` dans les marts — remonter d'une ligne d'analyse au HTML d'origine.
- 2026-11-26 : plusieurs sites — staging par site, unions dans intermediate, registre `config.site`,
  `is_active` par site ; un passage cron par site, dbt à part (ADR-0007, ADR-0008).
- 2026-11-26 : arrêt imprévu d'une commande = code 3 (code 1 réservé à une catégorie en échec) ; une fiche
  illisible est sautée par le normaliseur, sans bloquer les suivantes.

## Où on en est
- ✅ Fait : infra Docker (Postgres 17 + RustFS, ports en local), extraction jobup, normalisation factice,
  dbt multi-sites (unions, `config.site`), deux bases test / production, planification (un passage par site,
  dbt à part), réglages d'extraction dans `extraction/.env`, documentation complète (`documentation/`,
  guides, architecture, conventions, ADR 0003 à 0008), README allégé. Chaîne validée sur la base de test.
- 🔧 En cours : —
- ⏭️ Prochaine étape : relecture de la documentation par l'équipe ; mettre un contact dans
  `EXTRACTION_USER_AGENT` et traiter le cadre juridique avant la première collecte complète ; puis
  `PIPELINE_MODE=full` sur la machine de production.
- 📌 À trancher : statut d'ADR-0001 (encore « Proposé ») ; dates toujours en UTC, à écrire en ADR et à
  appliquer dans le code si on le confirme.

Note : `CLAUDE.md` ne fait plus que renvoyer ici — le travail se fait dans Claude Chat ;
référence = ce fichier + le cadre du projet Claude + la documentation.

## Questions fréquentes des équipes
Les réponses détaillées sont dans la documentation (`documentation/docs/`).
- Comment savoir si une offre est encore active ? → `is_active` = vue dans le dernier run **terminé** d'une de
  ses catégories, sur son site ; un run en échec ne fait jamais disparaître d'offres.
- Que se passe-t-il si un run échoue ? → `log_raw_job_info.status = 'failed'`, les autres catégories continuent ;
  on relance, les lignes déjà écrites sont ignorées (`on conflict do nothing`).
- Où regarder en cas d'erreur ? → `raw.log_raw_job_info` (runs), `raw.log_raw_job_detail` (téléchargements),
  rapport JSON en fin de commande, codes de sortie 0 / 1 / 2 / 3.
- Comment ajouter un site ? → guide `guides/ajouter-un-site.md` : dossier dans `extraction/`, ligne dans
  `config.site`, staging dbt, une ligne dans chaque union, une ligne cron.
- Comment changer de normaliseur ? → guide `guides/ajouter-un-normaliseur.md` : `default` dans
  `normalization.toml` (ce qui tourne) et `is_current` dans `config.normalizer` (ce que lisent les marts).
- Comment lancer un vrai passage ? → `--full` (base de production `jobcompass`) ; sans option, c'est un test
  dans `jobcompass_dev` (1 page, 2 fiches pour jobup).
- Comment retrouver le HTML d'une offre ? → `hash_html_id` dans les marts = nom du fichier dans RustFS.
- Comment changer une heure de collecte ? → sa ligne dans `orchestration/jobcompass.cron`, puis
  `docker compose -f infra/docker-compose.yml restart pipeline`.
- Un passage planifié va-t-il en production ? → seulement si `orchestration/.env` contient `PIPELINE_MODE=full`.
