# Ajouter un normaliseur

Ce guide branche un nouveau normaliseur (un vrai modèle NLP, par exemple) à côté du normaliseur factice, le
compare, puis en fait le normaliseur courant. Exemple : un normaliseur nommé `spacy`. Le modèle à copier
est `normalization/src/normalization/fake/`.

À lire d'abord : [Normalisation](../architecture/normalisation.md).

## 1. Le dossier du normaliseur

```
normalization/src/normalization/spacy/
├── __init__.py                     vide
├── normalizer.toml                 la configuration
├── spacy_normalization_uc.py       la classe
└── tests/
    └── test_spacy_normalization_uc.py
```

Le nom du dossier est le nom du normaliseur pour la commande (`--normalizer spacy`).

### `normalizer.toml`

```toml
class = "normalization.spacy.spacy_normalization_uc:SpacyNormalizationUseCase"
max_jobs = 10   # limite de test : fiches normalisées par passage
```

### La classe

Une classe `SpacyNormalizationUseCase` qui hérite de `INormalizationUseCase`
(`normalization/interfaces/i_normalization_uc.py`). Elle doit finir par `UseCase`, vivre dans un fichier
`…_uc.py`, et déclarer sa **signature** (sinon elle est refusée au chargement) :

```python
class SpacyNormalizationUseCase(INormalizationUseCase):
    """Skills found by a spaCy model."""

    normalizer: str = "spacy_normalization"
    normalizer_version: str = "0.1.0"
    model: str = "fr_core_news_md"
    model_version: str = "3.8.0"
    description: str = "Skills found by a spaCy NER model in the title and description."

    def execute(self) -> NormalizationReport:
        ...
```

Elle reçoit à sa création `source`, `db_storage`, `is_test`, `max_jobs` (`None` = sans limite) et `now`.
`execute()` doit, comme `FakeNormalizationUseCase` :

1. **Lire les fiches en attente** : `db_storage.read(Table.RAW_JOB_DETAIL, source, columns=[...])`, moins
   celles déjà présentes dans `normalized_job` avec **la même signature**, de la plus ancienne à la plus
   récente, au plus `max_jobs`.
2. **Lire le bloc de données** selon `payload_format` : `json_ld` → un objet JSON-LD (`title`,
   `description` en HTML, parfois `skills`) ; `paragraphs` → une liste de textes.
3. **Écrire un `NormalizedJob` par fiche, une par une**, avec la clé recopiée telle quelle (`hash_html_id`,
   `scraper`, `scraper_version`), la signature, `normalized_at=self.now()` et `skills`, une liste de
   `NormalizedSkill(raw=..., canonical=..., origin=...)`. Une compétence au plus une fois par fiche.
4. **Sauter une fiche illisible** : la journaliser, la compter, continuer. Elle ne doit jamais arrêter le
   passage.
5. Rendre un `NormalizationReport` : `normalized`, `remaining`, `failed`.

Le plus simple est de copier `fake_normalization_uc.py` et de remplacer `_skills`.

### Les dépendances

Les bibliothèques NLP vont dans `normalization/pyproject.toml` (`dependencies`), puis :

```bash
uv lock && uv sync --all-packages
```

Elles ne sont installées qu'avec la normalisation : l'extraction reste légère.

## 2. Tester

```bash
(cd normalization && uv run pytest -q)
uv run --package jobcompass-entrypoints jobcompass-normalization run jobup --normalizer spacy
```

Le passage de test normalise 10 fiches de `jobcompass_dev`. Voir [Conventions des tests](../conventions/tests.md).

## 3. Comparer avec le normaliseur actuel

Les deux normaliseurs écrivent dans la même table, chacun avec sa signature : on compare en SQL.

```sql
select normalizer, normalizer_version,
       count(*) as fiches,
       avg(jsonb_array_length(skills)) as competences_par_fiche
from raw.normalized_job
group by 1, 2;
```

Plus tard, le **golden set** (un jeu d'offres annotées à la main) servira de référence commune pour mesurer
la qualité de chaque normaliseur.

## 4. En faire le normaliseur courant

Deux réglages, à changer ensemble (voir [Normalisation](../architecture/normalisation.md)) :

**a. Les marts lisent le nouveau normaliseur** (`config.normalizer`). Une transaction, d'abord dans la
base de test :

```sql
begin;
insert into config.normalizer (normalizer, normalizer_version, description)
values ('spacy_normalization', '0.1.0', 'Skills found by a spaCy NER model in the title and description.');
update config.normalizer set is_current = false, updated_at = now() where is_current;
update config.normalizer set is_current = true, updated_at = now()
where normalizer = 'spacy_normalization' and normalizer_version = '0.1.0';
commit;
```

Puis `dbt build --target dev`, vérification des marts, et la même transaction dans la base de production.
Ajouter aussi la ligne dans `infra/postgres/init/schema/03_config_tables.sql` pour les nouvelles installations.

**b. La planification lance le nouveau normaliseur** : dans
`normalization/src/normalization/normalization.toml`, `default = "spacy"`. C'est une décision d'équipe.

Avant le premier passage complet, toutes les fiches existantes sont en attente pour le nouveau normaliseur :
lancer une fois `jobcompass-normalization run <site> --full` par site, ou laisser la planification les
traiter.

## 5. Les versions ensuite

| Changement | Monter | Puis |
|---|---|---|
| le modèle, sa liste de mots, ses réglages | `model_version` | rien : les marts prennent la normalisation la plus récente du normaliseur courant |
| ce que le normaliseur lit ou écrit | `normalizer_version` | nouvelle ligne courante dans `config.normalizer` (étape 4a) |

Dans les deux cas, toutes les fiches sont normalisées à nouveau ; les anciennes lignes restent pour comparer.
