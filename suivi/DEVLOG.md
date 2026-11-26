# JobCompass — journal de bord

Les entrées les plus récentes en haut. 3 à 5 lignes par session.

## 2026-11-26 (nuit)
- Fait : relecture du code ; ports Postgres/RustFS en local ; normaliseur qui saute les fiches illisibles ;
  code 3 pour un arrêt imprévu ; `ExtractionSettings` dans `extraction/.env` ; dbt multi-sites (unions,
  `config.site`, `is_active` par site) ; `run_site.sh` + `run_dbt.sh` (un passage cron par site) ;
  documentation complète dans `documentation/` (prise en main, guides, architecture, conventions, ADR 0003-0008) ;
  README allégé ; ancien fil rouge abandonné (antérieur à la méthode de suivi actuelle).
- Pourquoi : que l'association puisse reprendre le projet, ajouter des sites et des normaliseurs seule.
- Décision : union des sites dans intermediate (pas de chaîne par site) ; registre des sites en table ;
  un passage cron par site, dbt 3 h après ; plus aucune mention de Claude dans les commits.
- Reste à faire : trancher le statut d'ADR-0001 ; ADR des dates UTC ; contact dans le user agent et cadre
  juridique avant la collecte complète.

## 2026-11-25 (nuit)
- Fait : planification de la chaîne — `orchestration/run_pipeline.sh`, `jobcompass.cron`, `Dockerfile` (+ son
  `.dockerignore`), `.env.example`, service `pipeline` dans le docker-compose ; testé à la main puis toutes les minutes.
- Pourquoi : que le projet tourne seul après un `docker compose up`, sur n'importe quelle machine de l'équipe.
- Décision : supercronic (plutôt que Dagster, une librairie Python ou un cron sur la machine) ; chaque dossier
  garde ses variables ; si une catégorie échoue, on continue (is_active ignore les passages en échec).
- Reste à faire : variables d'extraction dans `extraction/` (fait le 26/11).

## 2026-11-25 (soir)
- Fait : étape 5 validée et commitée (deux bases, scripts `infra/postgres/` enfin versionnés) ; `data/` supprimé ;
  `hash_html_id` ajouté aux marts `jobs__job_offers` et `skills__job_skills` ; README écrit (processus, stockage,
  test ou production, règles métier, documentation).
- Pourquoi : livraison du jeudi 26/11 ; README lisible par quelqu'un qui découvre le projet.
- Décision : cron plutôt que Dagster pour l'orchestration (l'équipe n'attend pas Dagster).
- Reste à faire : documentation `docs/` (ADR-0002, ADR 0003 à 0007, fil rouge) — dans un nouveau chat.

## 2026-11-25
- Fait : adoption de la procédure de suivi (PROJECT_MAP.md + DEVLOG.md, rituels de début et de fin de session) ;
  cadre du projet mis à jour (Postgres en Docker, plus de DuckDB/Parquet/Neo4j, plus de démo RNCP).
- Pourquoi : garder une vue d'ensemble du projet et pouvoir répondre aux questions de l'équipe.
- Décision : travail dans Claude Chat, plus dans Claude Code ; CLAUDE.md n'est plus tenu à jour.
- Reste à faire : relire et valider PROJECT_MAP.md ; compléter « En cours » et « Prochaine étape ».

## 2026-11-19 / 20 (reconstitué)
- Fait : passage de Parquet/DuckDB à Postgres 17 + RustFS en conteneurs (`infra/`), tables brutes et
  table `config.normalizer`, base de test `jobcompass_dev`, modèles dbt staging → intermediate → marts.
- Pourquoi : stockage simple à transmettre à l'équipe, compatible dbt.
- Reste à faire : livrer la chaîne extraction → normalisation → dbt (jeudi 26/11).
