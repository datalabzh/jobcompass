# ADR-0002 — ELT : brut minimal, transformations dans dbt, peu d'outils

- **Statut** : Accepté
- **Date** : 2026-11-18
- **Décideur** : David

## Contexte

La revue du 17/11 a proposé d'adopter des outils pour la collecte (Scrapy, Crawlee) et le chargement (dlt).
Le spike dlt (test 1) a montré que dlt ajoute beaucoup d'implicite : colonnes `_dlt_*`, tables d'état,
dossier de travail, copie des fichiers chargés, contrat de schéma posé d'office. Par ailleurs, le code
d'extraction choisissait et renommait des champs en Python (`ExtractedJob`), donc mettait les données en forme
pour des tables pas encore définies. Le projet sera repris par une équipe : il doit rester simple et standard.

## Décision

- **ELT** : Python collecte et dépose la donnée **telle quelle** ; toute mise en forme se fait dans **dbt**
  (dbt-duckdb sur les Parquet) : un staging par table brute, puis silver et gold.
- **Collecte** : notre code Python existant (httpx) : délai entre requêtes, `robots.txt` lu avec la bibliothèque
  standard, quelques tentatives répétées.
- **Extraction minimale** : s'il y a du JSON (JSON-LD), on le prend tel quel ; sinon un petit parseur récupère
  les paragraphes du HTML. Aucun renommage, aucune sélection de champs.
- **Tables brutes (enveloppes)** :
  - *job info* : l'URL et ses métadonnées (site, date…), rien d'autre ;
  - *job détail* : métadonnées (url, `raw_hash`, date de collecte, version de l'extracteur) + bloc brut.
  - Le HTML reste conservé tel quel, à part.
- **Écriture** : un fichier Parquet **par passage**, pas par offre (pyarrow ou DuckDB).
- **Normalisation** (NLP/LLM) : seul traitement en Python après la collecte ; elle lit la description en silver
  et écrit son résultat dans une nouvelle table brute, reprise par dbt.
- **Outils** : Python, DuckDB, dbt. Tout autre outil demande un besoin concret.
- **Orchestration** : un script ou une CLI pour l'instant ; Dagster quand il faudra planifier les passages.

## Alternatives écartées

- **dlt** : plus d'implicite qu'il n'en retire pour déposer des lignes « enveloppe + bloc brut » en Parquet ;
  son aplatissement automatique des listes en tables enfants contredit le principe ELT.
- **Scrapy, Crawlee** : cadre et état propres pour un besoin couvert par quelques lignes ; à reconsidérer
  seulement si un site exige d'exécuter du JavaScript.
- **Contrats détaillés produits en Python** (`ExtractedJob`, ligne par compétence) : mise en forme pour des
  tables futures, rôle de dbt.

## Conséquences

- Les listes (compétences, catégories…) restent telles quelles dans le brut ; l'aplatissement se fait en silver.
- Tous les champs du JSON-LD sont disponibles : pas besoin d'anticiper les besoins des consommateurs.
- Changer la lecture d'un champ = modifier un modèle dbt, sans reparser le HTML.
- Validation Pydantic limitée à l'enveloppe ; la qualité du contenu est vérifiée par des tests dbt.
- Chaque nouveau site demande un extracteur minimal **et** un modèle de staging dbt.
- Le reste à faire et la lecture de fichiers de versions différentes se font en SQL (DuckDB).
- `ExtractedJob` et l'abstraction `IStorage` sont probablement superflus : à confirmer lors de la refonte.
- Le spike dlt est clos ; la branche `spike/dlt` peut être abandonnée.
