# Spike dlt

*Exploration jetable (branche `spike/dlt`), ouverte le 18 novembre 2026 pour trancher C5 du fil rouge :
adopter dlt pour charger les lignes produites par les scrapers ?*

Le spike ne touche ni au code des briques ni à `data/` : tout est écrit dans `spikes/dlt/output/`
(ignoré par git, effacé à chaque lancement).

```bash
uv add --dev "dlt[parquet,duckdb]"
uv run python spikes/dlt/try_dlt.py
```

## Questions testées

| # | Question | Lien | Statut |
|---|---|---|---|
| 1 | Charger des `ExtractedJob` en Parquet local, contrat Pydantic comme schéma, configuration entièrement dans le code : que produit dlt ? | Principe « peu d'implicite » | fait |
| 2 | `NormalizedJob` : à quoi ressemble la liste `skills` ? | F1 | à faire |
| 3 | Ajouter un champ au contrat puis recharger ; figer le schéma | C3 | à faire |
| 4 | Charger par lots de N : nombre de fichiers, interruption | C2, point d'arrêt | à faire |
| 5 | Relire anciens et nouveaux fichiers ensemble avec DuckDB | C1 | à faire |
| 6 | Disposition des fichiers (site / table) | ADR-001 | vu en 1 |

## Résultats

### Test 1 (dlt 1.32.0)

**Ce qui marche**
- 5 `ExtractedJob` (fixture + HTML de `data/test/`) → un seul fichier Parquet,
  `data/jobup/extracted_job/<load_id>.<file_id>.parquet`, relu sans difficulté par DuckDB.
- Configuration entièrement dans le code : aucun dossier `.dlt/`, ni dans le dépôt ni dans `~`.
  Télémétrie désactivée par une variable d'environnement posée avant l'import.
- Disposition par défaut conforme à celle retenue : un dossier par jeu de données (site), puis par table.

**Ce que dlt ajoute de lui-même (implicite)**
- Deux colonnes dans la table : `_dlt_load_id`, `_dlt_id`.
- Dans le dossier du site : `_dlt_loads/`, `_dlt_version/`, `_dlt_pipeline_state/` (JSONL) et un fichier `init`.
  L'état du pipeline est écrit même sans état incrémental.
- Dossier de travail (`pipelines/jobup/`) : schéma, état, trace (`trace.pickle`) et **une copie de chaque
  fichier chargé** (`load/loaded/.../completed_jobs/`). Doublon des données à nettoyer ou à désactiver.
- **Contrat de schéma posé automatiquement** quand on passe un modèle Pydantic :
  tables `evolve`, colonnes `freeze`, types `freeze`. Un champ ajouté au contrat sera donc refusé
  tant qu'on ne le règle pas (à vérifier au test 3).

**Frottements entre nos contrats et dlt**
- `parsed_at` (`AwareDatetime`) est écrit en **texte**, pas en horodatage. Vérifié à part :
  dlt reconnaît `datetime`, pas `AwareDatetime`. À corriger soit dans le contrat (type `datetime`
  + validateur de fuseau), soit par une indication de type sur la colonne.
- Les listes (`employment_types`, `categories`, `declared_skills`) sont écrites en **texte JSON**,
  pas en tables enfants : c'est le comportement de dlt avec un modèle Pydantic. Format long à revoir
  au test 2.
- `schema_version` est une colonne de texte : la version du contrat est donc aussi portée par
  `_dlt_version`, en double.

### Note : pagination dans dlt
Le client REST de dlt fournit des paginateurs (numéro de page, offset, curseur, lien suivant).
Ils lisent le total ou la page suivante dans une réponse **JSON** ou dans les en-têtes HTTP : ils
servent aux API. Ils ne s'appliquent pas aux pages HTML de jobup (nombre de pages dans `__INIT__`,
page au-delà de la dernière qui renvoie la page 1 au lieu d'une page vide), et `/api/` est interdit
par le `robots.txt` de jobup.
