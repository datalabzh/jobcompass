# JobCompass — carte

## En une phrase
Collecte les offres d'emploi de Suisse romande (jobup.ch pour l'instant), en extrait les compétences et les
met à disposition en SQL, pour construire des clusters de compétences indépendants des intitulés de poste.

## Flux (schéma)
```
jobup.ch ──(jobcompass-extraction run jobup)──► raw.raw_job_info      + raw.log_raw_job_info
                                           ├──► raw.raw_job_detail    + raw.log_raw_job_detail
                                           └──► HTML brut → RustFS (bucket jobcompass-raw, par hash_html_id)

raw.raw_job_detail ──(jobcompass-normalization run jobup)──► raw.normalized_job
config.normalizer (désigne le normaliseur courant)

dbt build : staging (vues) → intermediate (vues) → marts (tables)
  stg_jobup__job_infos, stg_jobup__job_info_runs ─► int_jobs__job_infos_aggregated ─┐
  stg_jobup__job_details ───────────────────────────────────────────────────────────┼─► marts.jobs__job_offers
  stg_normalization__normalized_jobs + stg_config__normalizers                      │
      ─► int_skills__normalized_skills_unnested ────────────────────────────────────┴─► marts.skills__job_skills
```
Orchestration : lancement manuel ; un cron qui enchaîne les 3 commandes quand la collecte réelle démarrera
(Dagster seulement si un besoin réel apparaît ; `orchestration/` vide).

## Objets
| Objet | Type | Rôle en 1 ligne | Écrit par |
|---|---|---|---|
| raw.raw_job_info | Table | Une offre vue sur une page de résultats, par run (carte brute en jsonb) | extraction |
| raw.log_raw_job_info | Table | Journal d'un run par catégorie (`completed` / `failed`, totaux) | extraction |
| raw.raw_job_detail | Table | Une page de détail téléchargée : bloc brut `json_ld` ou `paragraphs` | extraction |
| raw.log_raw_job_detail | Table | Un échec de téléchargement d'une page de détail | extraction |
| raw.normalized_job | Table | Compétences d'une page, signées par normaliseur + modèle (versions) | normalisation |
| config.normalizer | Table | Normaliseurs connus ; un seul `is_current` (seule table mise à jour) | à la main |
| RustFS `jobcompass-raw` | Objet S3 | HTML brut immuable, nommé par `hash_html_id` | extraction |
| JobupExtractionUseCase | Classe | Extraction jobup (job infos puis job details), réglée par `site.toml` | — |
| FakeNormalizationUseCase | Classe | Normaliseur factice (déclarées + ~30 mots-clés), courant par défaut | — |
| marts.jobs__job_offers | Table dbt | Une ligne par offre : présence, `is_active`, dernière fiche, `hash_html_id` | dbt |
| marts.skills__job_skills | Table dbt | Une ligne par offre et compétence canonique, jours vus, `hash_html_id` | dbt |

Bases : `jobcompass` (target `real`) et `jobcompass_dev` (target `dev`, zone de test), mêmes schémas.

## Décisions clés (le « pourquoi »)
- 2026-11-18 : ELT — Python dépose le brut, dbt transforme (ADR-0002) ; pas d'outil sans besoin concret.
- 2026-11-19 : Postgres en conteneur à la place de Parquet/DuckDB — plus simple à transmettre à l'équipe.
- 2026-11-19 : RustFS à la place de MinIO — l'édition communautaire de MinIO n'est plus distribuée.
- 2026-11-19 : le SQL ne parse jamais de texte ; la normalisation Python lit job detail et écrit normalized_job.
- 2026-11-19 : un seul hash en Python (`hash_html_id`), les autres `hash_<objet>_id` calculés en staging dbt.
- 2026-11-19 : normaliseur courant désigné dans `config.normalizer`, pas dans une variable dbt.
- 2026-11-20 : zone de test = base séparée `jobcompass_dev` ; titre/entreprise/date pris du JSON-LD, sinon de la carte.
- 2026-11-25 : cron plutôt que Dagster — 3 commandes à la suite, état dans les tables ; l'équipe n'attend pas Dagster.
- 2026-11-25 : `hash_html_id` dans les marts — remonter d'une ligne d'analyse au HTML d'origine (traçabilité).

## Où on en est
- ✅ Fait : infra Docker (Postgres 17 + RustFS), extraction jobup et normalisation factice vers Postgres,
  modèles dbt staging → marts, deux bases test / production (étape 5), `hash_html_id` dans les marts, README.
  Chaîne validée de bout en bout sur la base de test.
- 🔧 En cours : documentation `docs/` (ADR-0002 à mettre à jour, ADR 0003 à 0007 à rédiger, fil rouge).
- ⏭️ Prochaine étape : livraison (jeudi 26/11) ; plus tard, script + cron pour la collecte réelle.

Note : `CLAUDE.md` ne fait plus que renvoyer ici — le travail se fait dans Claude Chat ;
référence = ce fichier + le cadre du projet Claude + le README.

## Questions fréquentes des équipes
- Comment savoir si une offre est encore active ? → `is_active` = vue dans le dernier run **terminé** d'une de ses
  catégories ; un run en échec ne fait jamais disparaître d'offres.
- Que se passe-t-il si un run échoue ? → `log_raw_job_info.status = 'failed'`, les autres catégories continuent ;
  on relance, les lignes déjà écrites sont ignorées (`on conflict do nothing`).
- Où regarder en cas d'erreur ? → `raw.log_raw_job_info` (runs), `raw.log_raw_job_detail` (téléchargements),
  rapport JSON en fin de commande.
- Comment changer de normaliseur ? → nouveau dossier dans `normalization/`, puis désigner le courant dans
  `config.normalizer` (une transaction) ; dbt ne lit que le courant.
- Comment lancer un vrai passage ? → `--full` (base de production `jobcompass`) ; sans option, c'est un test
  dans `jobcompass_dev` (1 page, 2 fiches pour jobup).
- Comment retrouver le HTML d'une offre ? → `hash_html_id` dans les marts = nom du fichier dans RustFS.
