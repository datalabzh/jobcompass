# Lancer la chaîne

La chaîne a trois étapes. Chacune lit ce que la précédente a déposé en base : on peut les lancer
séparément, dans cet ordre.

```
extraction  ──►  normalisation  ──►  dbt
(pages web)      (compétences)       (tables d'analyse)
```

**Par défaut, tout tourne en mode test** : peu de pages, base `jobcompass_dev`. C'est une sécurité ; voir
[Test et production](../architecture/test-et-production.md).

## Les trois commandes

```bash
# 1. Extraction : pages de résultats puis fiches des offres (ici jobup.ch)
uv run --package jobcompass-entrypoints jobcompass-extraction run jobup

# 2. Normalisation : compétences des fiches téléchargées
uv run --package jobcompass-entrypoints jobcompass-normalization run jobup

# 3. dbt : tables d'analyse
uv run --env-file infra/.env --package jobcompass-dbt dbt build --project-dir dbt --profiles-dir dbt --target dev
```

Ou, plus court, avec les scripts de la planification (mêmes commandes, mode lu dans
`orchestration/.env`) :

```bash
bash orchestration/run_site.sh jobup   # extraction + normalisation de jobup
bash orchestration/run_dbt.sh          # dbt build
```

## Options

| Option | Commande | Effet |
|---|---|---|
| *(aucune)* | extraction, normalisation | test, limité par la configuration (jobup : 1 page, 2 fiches ; normalisation : 10 fiches) |
| `--max-pages N`, `--max-jobs N` | extraction | test, avec ces limites |
| `--max-jobs N` | normalisation | test, avec cette limite |
| `--full` | extraction, normalisation | **production** : tout, sans limite, base `jobcompass` |
| `--normalizer <dossier>` | normalisation | un autre normaliseur que celui par défaut |
| `--target dev` / `--target real` | dbt | base de test / de production |

`--full` ne se combine pas avec une option `--max-…`. Toutes les options : `run --help`, par exemple
`uv run --package jobcompass-entrypoints jobcompass-extraction run --help`.

## Lire le résultat

Chaque commande Python affiche des logs, puis **en dernière ligne un rapport JSON** :

- extraction : pour chaque catégorie, son journal (`status`, `pages_read`, `jobs_seen`…), puis le bilan
  des fiches (`extracted`, `failed`, `set_aside`) ;
- normalisation : `normalized` (fiches traitées), `failed` (illisibles, sautées), `remaining`
  (restantes, limite atteinte).

### Codes de sortie

| Code | Signification |
|---|---|
| 0 | tout s'est bien passé |
| 1 | extraction : au moins une catégorie a échoué ; les autres sont bien collectées |
| 2 | configuration ou options incorrectes : rien n'a été fait |
| 3 | arrêt imprévu (base ou stockage injoignable…) : voir la trace dans les logs |

### Où regarder en cas de problème

| Question | Table |
|---|---|
| Un passage sur une catégorie a-t-il réussi ? | `raw.log_raw_job_info` (`status`, `error`) |
| Pourquoi une fiche n'a-t-elle pas été téléchargée ? | `raw.log_raw_job_detail` |
| Une page a-t-elle été sautée par le normaliseur ? | les logs de la commande (`WARNING … skipped`) |

## Vérifier les données

```bash
docker compose -f infra/docker-compose.yml exec postgres psql -U jobcompass -d jobcompass_dev
```

```sql
select count(*), count(*) filter (where is_active) as actives from marts.jobs__job_offers;
select canonical_skill, count(*) from marts.skills__job_skills group by 1 order by 2 desc limit 10;
```

Le contenu des tables d'analyse est décrit dans [Transformation (dbt)](../architecture/transformation.md).
