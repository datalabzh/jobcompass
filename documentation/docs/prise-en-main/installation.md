# Installation

Objectif : faire tourner JobCompass sur ta machine, en mode test, en une quinzaine de minutes.

## Prérequis

- **Docker** et **Docker Compose** 2.24 ou plus récent (`docker compose version`).
- **[uv](https://docs.astral.sh/uv/)**, qui installe aussi Python 3.12.
- Git.

## 1. Récupérer le dépôt

```bash
git clone <url-du-dépôt> jobcompass
cd jobcompass
```

**Toutes les commandes de cette documentation se lancent depuis la racine du dépôt.**

## 2. Créer les fichiers de réglages

Chaque dossier garde ses propres réglages dans un `.env` non versionné, copié depuis son modèle
`.env.example` :

```bash
cp infra/.env.example infra/.env                   # obligatoire : mots de passe de Postgres et RustFS
cp orchestration/.env.example orchestration/.env   # facultatif : mode test ou production
cp extraction/.env.example extraction/.env         # facultatif : user agent, timeout…
```

Dans `infra/.env`, **change les mots de passe** (`POSTGRES_PASSWORD`, `S3_SECRET_KEY`).

| Fichier | Contenu | Lu par |
|---|---|---|
| `infra/.env` | connexions à Postgres et RustFS | les conteneurs, les stockages Python, dbt |
| `orchestration/.env` | `PIPELINE_MODE` (`test` ou `full`) | les scripts de `orchestration/` |
| `extraction/.env` | `EXTRACTION_*` : user agent, timeout, échecs tolérés, niveau de log | la commande d'extraction |

Sans `orchestration/.env` ni `extraction/.env`, les valeurs par défaut s'appliquent (mode test, user agent
générique).

## 3. Démarrer l'infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d --build --wait
```

Cela démarre quatre conteneurs :

| Conteneur | Rôle |
|---|---|
| `jobcompass-postgres` | Postgres 17 : les deux bases `jobcompass` (production) et `jobcompass_dev` (test) |
| `jobcompass-rustfs` | stockage objet compatible S3 : le HTML brut des offres |
| `jobcompass-rustfs-init` | crée le bucket au premier démarrage, puis s'arrête |
| `jobcompass-pipeline` | la planification (supercronic) : voir [Planification](planification.md) |

Au premier démarrage, Postgres crée les deux bases et leurs tables (scripts de `infra/postgres/init/`).

## 4. Installer les dépendances Python

```bash
uv sync --all-packages
```

## 5. Vérifier

```bash
docker compose -f infra/docker-compose.yml exec postgres psql -U jobcompass -d jobcompass_dev -c "select * from config.site;"
```

Tu dois voir la ligne `jobup`. La console RustFS est sur http://localhost:9001 (identifiants :
`S3_ACCESS_KEY` et `S3_SECRET_KEY` de `infra/.env`).

Prochaine étape : [Lancer la chaîne](lancer-la-chaine.md).

## Pièges connus

**Postgres s'arrête au premier démarrage avec « Permission denied »** sur un script de
`infra/postgres/init/`. Postgres doit pouvoir lire ces fichiers. Rétablir les droits, puis repartir de
volumes vides :

```bash
find infra/postgres -type d -exec chmod 755 {} +
find infra/postgres -type f -exec chmod 644 {} +
chmod 755 infra/postgres/init/00_init_databases.sh
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d --wait
```

**Un script de `infra/postgres/init/` a été modifié, mais rien ne change.** Ces scripts ne tournent qu'au
premier démarrage, sur un volume vide. Deux solutions : appliquer la modification à la main dans les deux
bases (`psql`), ou repartir de zéro avec `docker compose -f infra/docker-compose.yml down -v`, qui
**efface les données des deux bases**.

**Docker : « veth … operation not supported ».** Le noyau a été mis à jour sans redémarrage :
redémarrer la machine.

**Se connecter à la base depuis un autre poste.** Les ports de Postgres et RustFS ne sont publiés que sur
`127.0.0.1`, pour qu'ils ne soient pas joignables depuis le réseau. Depuis un autre poste, passer par un
tunnel SSH : `ssh -L 5432:localhost:5432 <serveur>`.
