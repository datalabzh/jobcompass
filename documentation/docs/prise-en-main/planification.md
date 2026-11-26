# Planification

En production, la collecte tourne seule chaque jour, dans le conteneur `pipeline`. Il est démarré par
`docker compose` avec le reste de l'infrastructure : aucune installation sur la machine.

## Comment ça marche

Le conteneur exécute **supercronic**, un planificateur au format cron conçu pour les conteneurs. Il lit
`orchestration/jobcompass.cron` :

```
0 4 * * * bash /app/orchestration/run_site.sh jobup
0 7 * * * bash /app/orchestration/run_dbt.sh
```

- **Une ligne par site** : `run_site.sh <site>` fait l'extraction puis la normalisation du site. Chaque
  site a son heure, et un site qui échoue ne gêne pas les autres.
- **Une seule ligne dbt** : `run_dbt.sh` construit les tables d'analyse pour tous les sites, assez tard
  pour que les sites aient fini. Un site en retard arrive dans les marts au passage suivant. Deux
  `dbt build` en même temps se gêneraient : il n'y en a donc qu'une.

Les heures sont celles de Zurich (le conteneur est réglé sur `Europe/Zurich`). Supercronic ne relance
pas une ligne tant que son passage précédent n'est pas fini.

## Les opérations courantes

| Pour… | Modifier | Puis |
|---|---|---|
| changer une heure | sa ligne dans `orchestration/jobcompass.cron` | `docker compose -f infra/docker-compose.yml restart pipeline` |
| collecter un nouveau site | une ligne `run_site.sh <site>` dans le cron | idem |
| arrêter de collecter un site | supprimer sa ligne | idem |
| passer en production | `PIPELINE_MODE=full` dans `orchestration/.env` | idem |
| prendre en compte une modification du code Python ou dbt | — | `docker compose -f infra/docker-compose.yml up -d --build pipeline` |

Le dossier `orchestration/` est monté dans le conteneur : modifier l'heure ou le mode ne demande qu'un
redémarrage. Le code Python et dbt, eux, sont copiés dans l'image : il faut la reconstruire (`--build`).

Format d'une ligne cron : `minute heure jour-du-mois mois jour-de-la-semaine commande`. Exemples :
`0 4 * * *` tous les jours à 4 h, `0 4 * * 1-5` du lundi au vendredi.

## Suivre les passages

```bash
docker compose -f infra/docker-compose.yml logs -f pipeline
```

Supercronic écrit une ligne au lancement et à la fin de chaque passage, avec son résultat, et les
scripts écrivent leurs étapes (`[run_site] 1/2 extraction`…).

Un passage se lance aussi à la main, dans le conteneur :

```bash
docker compose -f infra/docker-compose.yml exec pipeline bash /app/orchestration/run_site.sh jobup
```

## Le mode test ou production

Le mode se règle dans `orchestration/.env`, propre à chaque machine (non versionné) :

- `PIPELINE_MODE=test` (défaut) : passages limités, base `jobcompass_dev`, dbt `--target dev` ;
- `PIPELINE_MODE=full` : tout, base `jobcompass`, dbt `--target real`.

Une variable donnée à la commande l'emporte : `PIPELINE_MODE=test bash orchestration/run_site.sh jobup`.

## Que se passe-t-il en cas d'échec ?

| Situation | `run_site.sh` |
|---|---|
| une catégorie a échoué (code 1 de l'extraction) | normalise quand même ; finit en code 1 |
| configuration incorrecte (2) ou arrêt imprévu (3) | s'arrête, sans normaliser ; finit avec ce code |

Une catégorie en échec ne fausse pas les données : une offre n'est considérée comme disparue que d'après
le dernier passage **réussi** de sa catégorie (voir [Règles métier](../architecture/regles-metier.md)).

## Tester la planification

Pour vérifier que supercronic déclenche bien les scripts, mettre temporairement une ligne à
`* * * * *` (toutes les minutes), redémarrer le service et suivre les logs. Laisser tourner deux ou trois
passages, pas plus : même en test, chaque passage interroge le portail. Puis remettre l'heure réelle.
