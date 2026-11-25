# JobCompass — journal de bord

Les entrées les plus récentes en haut. 3 à 5 lignes par session.

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
