# Conventions Python

Les règles d'écriture du code Python du projet. Elles sont en partie vérifiées par ruff (avant chaque
commit) et par le code lui-même (des classes mal nommées sont refusées au chargement).

## KISS d'abord

La solution la plus simple qui marche. Pas d'abstraction, de couche ou de dépendance « pour plus tard » :
on l'ajoute quand un besoin réel apparaît. Un fichier se lit sans devoir en ouvrir cinq autres.

## Les cas d'utilisation : une classe, une méthode `execute`

Toute action métier est une classe qui hérite de `IUseCase` (`common/interfaces/`) :

- elle reçoit **tout ce dont elle a besoin à sa création** (stockages, réglages, horloge `now`…) ;
- elle n'a **qu'une méthode publique, `execute()`**, qui lance l'action et rend son rapport ;
- tout le reste est privé (`_nom`).

Nommage, vérifié dès le chargement de la classe (`TypeError` sinon) : le nom finit par **`UseCase`**
(`JobupExtractionUseCase`) et le fichier par **`_uc.py`** (`jobup_extraction_uc.py`).

Une étape interne peut être elle-même une classe privée du module, avec son `execute`
(ex. `_JobupJobInfosUseCase` dans `jobup_extraction_uc.py`).

## Les interfaces

- Une interface est une classe abstraite préfixée par `I` (`IParser`, `IDbStorage`), dans un fichier
  `i_<nom>.py` du dossier `interfaces/` de sa brique. Les interfaces partagées par plusieurs briques sont
  dans `common/interfaces/` ou `storage/interfaces/`.
- Quand une interface exige des attributs (signature d'un normaliseur, `name` et `version` d'un parseur),
  elle les vérifie dès la définition de la classe concrète.

## Les briques et leurs dépendances

- Une brique **n'importe jamais une autre brique** : l'extraction ne connaît pas la normalisation, et
  inversement. Elles partagent seulement `common/` et `storage/`. Les lignes de commande (`entrypoints/`)
  importent la brique qu'elles lancent.
- Chaque brique a son `pyproject.toml` et ses dépendances. Ajouter une dépendance :
  `uv add --package <package> <bibliothèque>`.
- On importe chaque classe par son chemin complet
  (`from contracts.jobs.raw_job_info import RawJobInfo`) : les `__init__.py` restent vides.

## La configuration

- Ce qui est propre à un site ou à un normaliseur : un fichier TOML dans son dossier (`site.toml`,
  `normalizer.toml`), **validé par un modèle Pydantic** au chargement, avant toute requête ou écriture.
- Ce qui est propre à une machine (mots de passe, mode, user agent) : un `.env` dans le dossier de la
  brique concernée, jamais versionné, avec son modèle `.env.example`. Le chemin du `.env` se calcule depuis
  l'emplacement du fichier Python, pas depuis le dossier courant.
- Une variable d'environnement l'emporte toujours sur le fichier.

## L'écriture

- **En-tête de chaque fichier**, en français : le nom du fichier, puis `Description` (ce que fait le
  fichier) et `Règles` (ce qu'il faut savoir pour le modifier sans casser). C'est la documentation au plus
  près du code : la tenir à jour.
- **Docstrings et commentaires dans le code**, en anglais, d'une ligne ; obligatoires sur chaque module,
  classe et fonction (règle ruff `D1`).
- **Tout est typé** : arguments et retours (règle ruff `ANN`), et par habitude du projet les variables
  locales aussi.
- Lignes de 88 caractères, imports triés (ruff).
- Les dates sont toujours avec fuseau (`AwareDatetime`), en UTC.
- Les données passent entre briques par les **contrats** (`common/contracts/`), jamais par des
  dictionnaires libres.

## Les contrôles

```bash
uv run ruff check .          # lint
uv run ruff format .         # mise en forme
uv run pre-commit run --all-files
```
