# JobCompass

JobCompass analyse le marché de l'emploi en Suisse romande à partir des offres publiées sur plusieurs portails
(jobup.ch pour l'instant). Un intitulé de poste ne dit plus grand-chose : le projet remplace la taxonomie figée
des métiers par des **clusters de compétences** issus des offres réelles, et suit leur évolution dans le temps.

## Architecture

Trois briques indépendantes, qui ne s'appellent pas : chacune lit ce que la précédente a déposé en base.

| Brique | Dossier | Rôle |
|---|---|---|
| Extraction | `extraction/` | Télécharge les listes et les fiches d'offres (un dossier par site), dépose le brut |
| Normalisation | `normalization/` | Lit les fiches brutes, en extrait les compétences, dépose un job normalisé |
| Transformation | `dbt/` | Met en forme le brut : staging → intermediate → marts |

Briques communes : `common/contracts/` (contrats de données Pydantic), `common/catalog/` (noms des tables),
`common/interfaces/`, `storage/` (Postgres et S3), `entrypoints/` (lignes de commande).

```
jobup.ch ──(jobcompass-extraction run jobup)──► raw.raw_job_info      + raw.log_raw_job_info
                                           ├──► raw.raw_job_detail    + raw.log_raw_job_detail
                                           └──► HTML brut → RustFS (bucket jobcompass-raw, nommé par hash_html_id)

raw.raw_job_detail ──(jobcompass-normalization run jobup)──► raw.normalized_job

dbt build ──► staging (vues) → intermediate (vues) → marts.jobs__job_offers, marts.skills__job_skills (tables)
```

Principe **ELT** : Python extrait et charge le brut sans le mettre en forme ; dbt transforme. Le SQL ne fait
jamais d'analyse de texte : c'est le rôle de la normalisation.

## Prérequis

- Docker et Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.12 ou plus)

## Démarrage

Tout se lance **depuis la racine du dépôt**.

```bash
# 1. Variables de l'infrastructure (fichier non versionné)
cp infra/.env.example infra/.env        # puis changer les mots de passe

# 2. Postgres 17 + RustFS
docker compose -f infra/docker-compose.yml up -d --wait

# 3. Dépendances de toutes les briques
uv sync --all-packages
```

Au premier démarrage, Postgres crée deux bases avec les mêmes schémas (`raw`, `config`, puis ceux de dbt) :

- `jobcompass` : les vraies données ;
- `jobcompass_dev` : la zone de test (passages limités et tests automatiques).

Console RustFS : http://localhost:9001.

## Lancer la chaîne

```bash
# Extraction de jobup.ch
uv run --package jobcompass-entrypoints jobcompass-extraction run jobup

# Normalisation des fiches téléchargées
uv run --package jobcompass-entrypoints jobcompass-normalization run jobup

# Transformations dbt (base de dev)
uv run --env-file infra/.env --package jobcompass-dbt dbt build --project-dir dbt --profiles-dir dbt --target dev
```

**Passage de test ou vrai passage**

- Sans option : **passage de test**, limité par `extraction/src/extraction/jobup/site.toml` (`max_pages`,
  `max_jobs`) et par `normalizer.toml`. Les données sont marquées `is_test` et vont dans `jobcompass_dev`
  (préfixe `dev/` dans RustFS).
- `--max-pages N` / `--max-jobs N` : ajuste une limite (toujours un test).
- `--full` : vrai passage, sans limite, dans la base `jobcompass`. Ne se combine pas avec les `--max-...`.
- dbt : `--target dev` lit et écrit dans `jobcompass_dev`, `--target real` dans `jobcompass`.
- Normalisation : `--normalizer <dossier>` pour choisir un normaliseur (par défaut : `normalization.toml`).

Les options ne s'affichent qu'avec `run --help` (ex. `jobcompass-extraction run --help`).

## Règles métier

- **Offre active** (`is_active`) : vue dans le dernier passage **terminé** (`completed`) d'au moins une de ses
  catégories. Un passage en échec ne fait jamais disparaître d'offres.
- **Présence** : `first_seen_at` / `last_seen_at` = première et dernière apparition dans les listes.
- **Une offre est téléchargée une seule fois** : on suit sa présence dans les listes, pas ses modifications.
- **Titre, entreprise, date de publication** : pris dans le JSON-LD de la fiche s'il existe, sinon dans la carte
  du listing (dernière apparition).
- **`has_detail`** : la fiche de l'offre a été téléchargée (en test, seulement `max_jobs` fiches).
- **Dernière extraction d'une page** : la plus haute `scraper_version`, comparée nombre par nombre
  (`0.10.0` après `0.9.0`), puis le `fetched_at` le plus récent.
- **Normaliseur courant** : désigné dans `config.normalizer` (un seul `is_current`) ; dbt ne lit que ses
  résultats. Par défaut, `fake_normalization` (compétences déclarées + une trentaine de mots-clés), en attendant
  un vrai normaliseur.
- **Compétences** : `skills__job_skills` est au grain le plus fin, une ligne par offre et compétence canonique ;
  les comptes par jour, semaine ou mois se calculent à partir de ce mart.
- **Identifiants** : un seul hash calculé en Python, `hash_html_id` (SHA-256 du HTML, nom du fichier dans RustFS) ;
  les autres `hash_<objet>_id` sont calculés dans le staging dbt.

## Tests

```bash
# Tests Python, brique par brique (les conteneurs doivent tourner)
for p in common/contracts common/catalog common/interfaces storage extraction normalization entrypoints; do
  (cd $p && uv run pytest -q) || break
done

# Tests dbt : compris dans dbt build (voir plus haut)
```

## Pièges connus

- **Modifier un script SQL de `infra/postgres/init/`** : il n'est exécuté qu'au premier démarrage. Repartir de
  volumes vides :
  ```bash
  docker compose -f infra/docker-compose.yml down -v
  docker compose -f infra/docker-compose.yml up -d --wait
  ```
- **Fichiers illisibles par Postgres** (« Permission denied » à l'initialisation) : les scripts doivent être en
  `644` et leurs dossiers en `755`.
  ```bash
  find infra/postgres -type d -exec chmod 755 {} +
  find infra/postgres -type f -exec chmod 644 {} +
  chmod 755 infra/postgres/init/00_init_databases.sh
  ```
- **Docker : « veth … operation not supported »** : le noyau a été mis à jour sans redémarrage ; redémarrer la machine.

## Documentation

La documentation (décisions d'architecture, conventions dbt) est dans `docs/`, publiée avec
[Zensical](https://zensical.org), installé par `uv sync --all-packages` (groupe de dépendances `dev`).
Pour la consulter, depuis la racine du dépôt :

```bash
uv run zensical serve      # aperçu sur http://localhost:8000, rechargé à chaque modification
```

Pour générer le site statique dans `site/` (non versionné) : `uv run zensical build`.

Le suivi du projet (carte du projet, journal de bord) est dans `suivi/` :
`suivi/PROJECT_MAP.md` et `suivi/DEVLOG.md`.
