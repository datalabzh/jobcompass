# ADR-0007 — Planification : supercronic dans un conteneur, un passage par site

- **Statut** : Accepté
- **Date** : 2026-11-25
- **Décideur** : David
- **Remplace** : la partie « Dagster quand il faudra planifier » d'[ADR-0002](0002-elt-brut-minimal-dbt.md)

## Contexte

La collecte doit tourner seule chaque jour, sur n'importe quelle machine de l'équipe, après un simple
`docker compose up`. La chaîne est courte : extraction, normalisation, dbt. L'heure doit pouvoir changer
facilement, et un portail en panne ne doit pas bloquer les autres.

## Décision

- Un conteneur **`pipeline`** dans le docker compose, qui exécute **supercronic** (planificateur au format
  cron, conçu pour les conteneurs) sur `orchestration/jobcompass.cron`.
- **Une ligne cron par site** (`run_site.sh <site>` : extraction puis normalisation), et **une seule ligne
  dbt** (`run_dbt.sh`), quelques heures plus tard, pour tous les sites.
- Le mode (test ou production) se règle dans `orchestration/.env`, propre à chaque machine.
- Chaque dossier garde ses propres réglages (`infra/.env`, `orchestration/.env`, `extraction/.env`).

## Alternatives écartées

- **Dagster, Prefect, Airflow** : serveur et base de métadonnées pour trois commandes ; à reconsidérer si
  la chaîne devient un vrai graphe de tâches.
- **Cron sur la machine hôte** : dépend de la machine, à installer à la main par chacun.
- **Une librairie Python** (APScheduler) : un processus à maintenir pour ce que cron fait en une ligne.
- **Un seul script qui boucle sur les sites** : un site lent retarde les autres ; la liste des sites
  vivrait à deux endroits.

## Conséquences

- Changer une heure ou ajouter un site = une ligne dans le cron, puis un redémarrage du conteneur.
- dbt tourne à heure fixe sans attendre les sites : un site en retard arrive dans les marts le lendemain.
- Si un jour il faut des alertes en cas d'échec, yacron est l'étape suivante naturelle (même principe).
