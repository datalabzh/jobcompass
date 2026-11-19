# JobCompass : consignes pour Claude

JobCompass analyse le marché de l'emploi en Suisse romande à partir des offres de plusieurs portails. Il
remplace la taxonomie figée des métiers par des **clusters de compétences** issus des données réelles.
Projet d'équipe, en cours de refonte d'architecture (branche `refactor/architecture`).

## Façon de travailler

- **Toujours en français** : réponses, documentation, en-têtes des fichiers Python.
- **Ne jamais écrire ni modifier de code sans l'accord explicite de David.** Décrire d'abord ce qu'on veut
  faire, attendre son accord, puis le faire.
- **Par étapes** : une étape à la fois, vérifiée, avant la suivante.
- Réponses simples et efficaces : répondre à la question posée, sans partir dans tous les sens.
- **Challenger David** : ne pas aller dans son sens par défaut, s'appuyer sur les bonnes pratiques et les
  projets de référence. Le projet sert aussi à se former en architecture.
- Pas de tests ou d'explorations (spikes) inutiles : trancher directement sur l'essentiel.
- **KISS** : la solution la plus simple ; pas d'abstraction par anticipation.

## Principes d'architecture

1. **Simple et explicite** : peu d'implicite, pas de configuration ni d'état « magiques », pas de
   milliers de fichiers éparpillés.
2. **Architecture en briques** : travail en parallèle sur différents crawlers et transformations.
3. **ELT** (ADR-0002) : Python collecte et dépose la donnée **brute** ; toute mise en forme se fait dans
   **dbt** (DuckDB). Python ne met jamais les données en forme pour des tables futures. Seule exception :
   la normalisation (NLP/LLM), qui lit une table dbt et dépose son résultat comme nouvelle table brute.
4. Outils : Python, DuckDB, dbt. **Tout autre outil demande un besoin concret** (dlt, Scrapy, Crawlee
   écartés).

Décisions et questions ouvertes : `docs/adr/` (une décision par fichier) et
`docs/fil-rouge-architecture.md` (toutes les questions de la refonte, avec leur statut).

## Organisation du dépôt

Monolithe, workspace uv : chaque brique est un package avec ses propres dépendances.

| Dossier | Rôle |
|---|---|
| `common/contracts/` | contrats de données (Pydantic), versionnés |
| `common/catalog/` | catalogue des tables |
| `common/interfaces/` | interfaces communes |
| `extraction/` | un dossier par site (`jobup/`) : téléchargement et extraction du bloc brut |
| `storage/` | écriture des Parquet |
| `normalization/` | normalisation des compétences |
| `entrypoints/` | CLI |
| `transformation/` | projet dbt (staging, intermediate, marts) |
| `orchestration/` | Dagster, plus tard (vide pour l'instant) |
| `docs/` | documentation Zensical : ADR, fil rouge, conventions |
| `data/` | données (non versionnées) ; `data/test/` = zone de test |

## Commandes

**Tout se lance depuis la racine du dépôt** : les chemins de données sont relatifs à la racine.

```bash
# Tests d'une brique (pytest est déclaré dans chaque package)
(cd extraction && uv run pytest -q)

# Vérifier qu'une brique se suffit à elle-même
uv sync --package jobcompass-extraction

# dbt, toujours depuis la racine, avec le dbt de la brique (--package)
uv run --package jobcompass-transformation dbt build --project-dir transformation --profiles-dir transformation --target test

# Documentation
uv run zensical serve
```

## Conventions de code

**Python**

- En-tête de chaque fichier : docstring court en français (nom du fichier, `Description`, `Règles`),
  l'essentiel seulement.
- Docstring sur **chaque** classe, méthode et fonction ; **toutes** les variables typées.
- Une seule responsabilité par fonction ou méthode ; découper ce qui est trop long.
- Cas d'utilisation : une classe avec **une seule méthode publique `execute()`**, dépendances reçues en
  paramètres, tout le reste en méthodes privées.
- Encapsulation, « tell, don't ask » : on ne passe à une classe que ce qu'on peut vouloir changer depuis
  l'appelant (un stockage…) ; sa cuisine interne ne regarde qu'elle.
- Interfaces : ABC plutôt que Protocol. Pas de clean architecture, pas de conteneur d'injection, pas de DTO.
- Noms de fichiers qui disent ce qu'ils contiennent (pas de `base.py` ou `utils.py` fourre-tout).
- Code propre à chaque site derrière une interface minimale, plutôt qu'une classe générique pour tous.
- ruff (règles dans `pyproject.toml`), lignes de 88 caractères.

**dbt** : `docs/conventions/dbt.md`, à appliquer à chaque modèle, `.yml`, macro ou snapshot.
Documentation dbt de référence : https://docs.getdbt.com/llms.txt (index des pages en Markdown) ; pour
DuckDB, le dépôt dbt-duckdb. Vérifier une syntaxe ou une option dbt dans la documentation avant de
l'écrire, plutôt que de se fier à sa mémoire.

## Git

- Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`…), en français ; `!` pour un
  changement incompatible (ex. une nouvelle version majeure de contrat).
- Un commit par décision ou par étape, au moment où on la prend.
- Rien sur `main` pendant la refonte : on travaille sur `refactor/architecture`.
- Commiter seulement quand David le demande ; **ne jamais pousser** (David pousse lui-même).
- Un message de commit qui contient `!` se met entre apostrophes simples (le `!` entre guillemets
  doubles déclenche l'historique de bash).

## Données

- **Aucune extraction réelle à grande échelle tant que le projet est en développement.** Les passages de
  test (limités par le `site.toml`) écrivent dans `data/test/`.
- Le HTML brut de chaque page est conservé tel quel, adressé par son `raw_hash`.
