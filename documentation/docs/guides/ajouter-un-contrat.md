# Ajouter un contrat

Un **contrat** fixe les colonnes d'une table brute : c'est une classe Pydantic, partagée par la brique qui
écrit et par dbt qui lit. Ce guide crée une nouvelle table brute (par exemple pour les clusters, ou un
nouveau journal), ou modifie un contrat existant.

## Créer une table brute

### 1. Le contrat

Dans `common/contracts/src/contracts/jobs/<nom>.py`, une classe qui hérite de `ContractModel` (immuable,
champs inconnus refusés). S'inspirer de `raw_job_info.py` :

```python
class SkillCluster(ContractModel):
    """One skill of one market cluster of a period."""

    schema_version: Literal["1.0"] = "1.0"
    source: SourceSlug
    is_test: bool = Field(description="True if written by a test run (limited)")
    ...
```

- `schema_version`, `source` et `is_test` sont présents dans tous les contrats.
- Utiliser les types de `contracts/components/field_types.py` (`SourceSlug`, `JobUrl`, `Sha256Hash`, dates
  `AwareDatetime`), et y ajouter une énumération si un champ a une liste fermée de valeurs.
- Un bloc JSON se garde tel quel (texte JSON ou liste) : l'aplatissement se fait dans dbt.
- En-tête du fichier : `Description` et `Règles`, en français (voir [Conventions Python](../conventions/python.md)).

### 2. Le catalogue

Dans `common/catalog/src/catalog/tables.py`, une ligne pour nommer la table, avec en commentaire le contrat
qu'elle contient. Un journal se nomme `log_` + le nom de la table qu'il accompagne.

### 3. La table Postgres

Dans `infra/postgres/init/schema/02_raw_tables.sql`, la table avec **une colonne par champ du contrat**,
les mêmes noms, une contrainte `unique` qui rend l'écriture idempotente (relancer un passage ne crée pas
de doublon), et `_loaded_at timestamptz not null default now()`.

Ce script ne tourne que sur un volume vide : pour les bases existantes, lancer le `create table` dans les
deux bases (voir [Installation, pièges connus](../prise-en-main/installation.md#pieges-connus)).

### 4. La source dbt

Déclarer la table dans le `src_<source>.yml` de la brique qui l'écrit, puis son staging
([Ajouter un modèle dbt](ajouter-un-modele-dbt.md)).

### 5. Les tests

Dans `common/contracts/tests/test_contracts.py` : un enregistrement valide est accepté, un champ manquant ou
invalide est refusé.

## Modifier un contrat existant

- **Monter `schema_version`** à chaque changement de forme : les lignes anciennes et nouvelles restent
  distinguables.
- **Ajouter un champ** : avec une valeur par défaut si possible, puis `alter table … add column …` dans les
  deux bases et dans `02_raw_tables.sql`.
- **Supprimer ou renommer un champ** : à éviter ; les tables sont en ajout seul, et l'historique garde
  l'ancienne forme. En discuter avant, et l'écrire dans un ADR si c'est structurant.
