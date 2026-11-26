# JobCompass

JobCompass analyse le marché de l'emploi en Suisse romande à partir des offres publiées sur les portails
d'emploi (jobup.ch pour l'instant). Un intitulé de poste ne dit plus grand-chose : le projet remplace la
taxonomie figée des métiers par des **clusters de compétences** issus des offres réelles, et suit leur
évolution dans le temps.

```
portails ──► extraction ──► normalisation ──► dbt ──► analyses
            (pages, HTML)   (compétences)    (tables SQL)
```

## Documentation

Toute la documentation est dans `documentation/` : installation, guides (ajouter un site, un normaliseur,
un modèle dbt), architecture, conventions et décisions d'architecture. Pour la lire, depuis la racine du
dépôt :

```bash
uv run zensical serve -f documentation/zensical.toml   # http://localhost:8000
```

Elle se lit aussi directement en Markdown : commencer par
[`documentation/docs/index.md`](documentation/docs/index.md).

## Démarrage rapide

Prérequis : Docker (Compose 2.24 ou plus récent) et [uv](https://docs.astral.sh/uv/). Tout se lance
**depuis la racine du dépôt**.

```bash
cp infra/.env.example infra/.env          # puis changer les mots de passe
docker compose -f infra/docker-compose.yml up -d --build --wait
uv sync --all-packages

# Un passage complet, en mode test (base jobcompass_dev, quelques pages seulement)
bash orchestration/run_site.sh jobup      # extraction + normalisation
bash orchestration/run_dbt.sh             # tables d'analyse
```

**Par défaut, tout va en test** : rien n'écrit en production sans `--full` (ou `PIPELINE_MODE=full`).
Détails : [Installation](documentation/docs/prise-en-main/installation.md),
[Lancer la chaîne](documentation/docs/prise-en-main/lancer-la-chaine.md),
[Planification](documentation/docs/prise-en-main/planification.md).

## Organisation du dépôt

| Dossier | Rôle |
|---|---|
| `extraction/` | collecte des portails, un dossier par site (`jobup/`, avec son `site.toml`) |
| `normalization/` | extraction des compétences, un dossier par normaliseur (`fake/`) |
| `dbt/` | transformation en SQL : staging → intermediate → marts |
| `entrypoints/` | lignes de commande de l'extraction et de la normalisation |
| `storage/` | écriture dans Postgres et RustFS |
| `common/` | contrats de données (Pydantic), catalogue des tables, interfaces communes |
| `infra/` | Postgres, RustFS et le conteneur `pipeline` (docker compose) |
| `orchestration/` | planification : scripts d'un site et de dbt, heures (cron), image du conteneur `pipeline` |
| `pre-commit/` | outillage des contrôles avant commit |
| `documentation/` | la documentation |
| `suivi/` | suivi du projet : carte, journal de bord |

## Tests

```bash
for p in common/contracts common/catalog common/interfaces storage extraction normalization entrypoints; do
  (cd $p && uv run pytest -q) || break
done
uv run pre-commit run --all-files
```

Les tests utilisent les vrais conteneurs et vident la base de test avant chaque test. Voir
[Conventions des tests](documentation/docs/conventions/tests.md).
