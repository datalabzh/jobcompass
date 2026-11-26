# Conventions des tests

## Où sont les tests

- **Python** : un dossier `tests/` par brique (`common/contracts/tests/`, `storage/tests/`…). Le code d'un
  site ou d'un normaliseur a ses tests **à côté de lui** (`extraction/src/extraction/jobup/tests/`,
  `normalization/src/normalization/fake/tests/`), avec ses fixtures (pages HTML réelles).
- **dbt** : les tests sont déclarés dans les `.yml` des modèles et lancés par `dbt build`.
- **Avant chaque commit** : pre-commit (ruff, SQLFluff, `dbt parse`, dbt-checkpoint).

## Lancer les tests

Les conteneurs doivent tourner : les tests utilisent les vrais Postgres et RustFS.

```bash
docker compose -f infra/docker-compose.yml up -d --wait

# Tous les tests Python, brique par brique
for p in common/contracts common/catalog common/interfaces storage extraction normalization entrypoints; do
  (cd $p && uv run pytest -q) || break
done

# Une seule brique
(cd normalization && uv run pytest -q)

# Les tests dbt
uv run --env-file infra/.env --package jobcompass-dbt dbt build --project-dir dbt --profiles-dir dbt --target dev

# Les contrôles avant commit
uv run pre-commit run --all-files
```

## Les règles

- **Vrais stockages, pas de faux** : les tests écrivent dans la zone de test de Postgres et RustFS, **vidée
  avant chaque test**. Seul le réseau est simulé (`FakeGetPage` dans `extraction/conftest.py`, qui rend des
  pages préparées).
- Conséquence : **lancer les tests efface les données de test** de `jobcompass_dev` (et le préfixe `dev/`
  de RustFS). Relancer un passage de test pour les retrouver. La production n'est jamais touchée : vider une
  zone réelle est refusé.
- **Une heure fixe** (`fixed_now`, `NOW`) : un test ne dépend jamais de l'heure réelle.
- Un test = un comportement, décrit par sa docstring (« max_jobs limits a run; the next run only does what
  remains »). L'en-tête du fichier liste ce que le fichier couvre.
- Les **fixtures HTML** sont de vraies pages enregistrées : quand un portail change sa page, on enregistre
  la nouvelle, et les tests montrent ce qui a changé.

## Ce qu'il faut tester

| Pour… | Tester au moins |
|---|---|
| un parseur | chaque type de page sur une fixture réelle ; un contenu illisible lève `ParsingError` |
| une extraction de site | offres écrites par catégorie ; journal `completed` / `failed` ; une catégorie en échec n'arrête pas les autres ; limites `max_pages` / `max_jobs` ; reprise (rien n'est téléchargé deux fois) ; mise de côté après `max_failures` |
| un normaliseur | les compétences sur quelques fiches construites ; la clé recopiée et la signature ; la limite `max_jobs` et la reprise ; une fiche illisible sautée sans bloquer les suivantes |
| un contrat | un enregistrement valide accepté, des champs invalides refusés |
| un modèle dbt | `unique` et `not_null` sur sa clé ; `accepted_values` sur les listes fermées ; `relationships` vers les tables de référence |

## Plus tard : le golden set

Un jeu d'offres annotées à la main (les compétences attendues) servira de référence commune aux
normaliseurs : chacun sera mesuré sur ce même jeu. Il reste à constituer.
