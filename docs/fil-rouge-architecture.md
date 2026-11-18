# JobCompass — Fil rouge de la refonte d'architecture

*Toutes les remarques de la revue du 17 novembre 2026, sous forme de questions à trancher.*
*Détail et argumentation : `claude/revue-architecture.md`. État du code : `claude/cadre-projet.md`.*

Règle : chaque question se clôt par une décision courte (ADR : contexte, décision, alternatives écartées,
conséquences). Statut : ☐ à traiter · ◐ en cours · ☑ décidé (avec lien vers l'ADR).
Les décisions de processus (commits, organisation du travail) sont consignées ici, sans ADR.
**Les ADR vivent dans le dépôt** : `docs/adr/NNNN-titre.md`, documentation publiée avec Zensical
(`zensical.toml` à la racine, `uv run zensical serve`).

**Principes directeurs (posés par David le 18/11, critères de chaque décision)** :
1. **Simple et explicite** : peu d'implicite (pas de configuration ou d'état « magiques »), pas de milliers de
   fichiers éparpillés.
2. **Architecture en briques** permettant de travailler en collaboration, en parallèle, sur différents crawlers
   et différentes transformations.
3. **ELT : on dépose le brut, dbt transforme** (posé par David le 18/11, après-midi). On ne réinvente pas la roue :
   collecte avec un outil (Crawlee pressenti), chargement avec dlt, transformations avec dbt
   (bronze → silver → gold, **un staging par type de table brute** : chaque site est un cas particulier).
   Python ne met **jamais** les données en forme pour des tables futures : pas de sélection, de renommage ni
   d'aplatissement de champs avant dbt. Seule exception : la normalisation (NLP/LLM), qui lit une table dbt
   et dépose son résultat comme une nouvelle table brute.

**Contrats (enveloppes) qui en découlent** :
- **job info** : l'URL et ses métadonnées (date…), rien d'autre ; pas de scraping des pages de résultats au-delà.
- **job détail** : métadonnées (url, `raw_hash`, date de collecte, version de l'extracteur) + **bloc brut** :
  le JSON-LD tel quel pour jobup. Site sans JSON : un JSON construit par un scrap basique, ou le texte issu du
  HTML, dont la normalisation se chargera.
- `ExtractedJob` (champs choisis et renommés en Python) n'a plus de raison d'être : son rôle passe au staging dbt
  (à confirmer au moment de l'ADR).
- Validation Pydantic limitée à l'enveloppe ; la qualité du contenu est vérifiée par des tests dbt.

Ordre de traitement retenu le 18/11 : C5 (dlt) → D1 (Dagster natif) → B1 (outil de collecte).

## Point de reprise (18/11, fin de session)

- Principe 3 (ELT) posé : il tranche F1, F2, A5 et réoriente C1, C3, B3, B4, C5, C6. **ADR à rédiger** (principe ELT
  + enveloppes job info / job détail), puis ADR C5 (+ F4).
- Branche `spike/dlt` ; spike dans `spikes/dlt/` (`try_dlt.py`, `README.md` avec questions, statuts et résultats).
- Test 1 du spike fait (chargement d'`ExtractedJob` en Parquet local). **Prochaine étape : test 2 redéfini** :
  dlt dépose le JSON-LD brut dans **une seule colonne JSON**, sans l'aplatir en tables enfants (comportement par
  défaut de dlt avec des dict, refusé). Tests 3 à 5 abandonnés (évolution de schéma, reste à faire et relecture
  relèvent de dbt/SQL ; les petits fichiers se règlent avec les lots de dlt).
- Moteur dbt nécessaire dès maintenant (C6) : dbt-duckdb sur les Parquet proposé, à trancher.
- `docs/adr/index.md` indique ADR-0001 « Proposé » alors qu'il est accepté : à corriger au prochain commit.
- `cadre-projet.md` est en retard sur le code : `interfaces/` découpé en `infrastructure/` et `use_cases/`,
  `site_config.py` et `normalization_config.py` fusionnés dans `entrypoints/config.py`, un dossier par
  normaliseur (`normalization/fake/normalizer.toml`, option `--normalizer`). À mettre à jour à la fin de la refonte.
- Fichiers écrits par Claude dans le dépôt le 18/11, non commités : `spikes/dlt/`, `zensical.toml`, `docs/`,
  `.gitignore` (`spikes/**/output/`, `site/`).

---

## A. Priorités (avant toute refonte)

| # | Statut | Remarque | Question à trancher |
|---|---|---|---|
| A1 | ☑ | Beaucoup de changements non commités depuis le 17/11. | Commits par thème (Conventional Commits) : lesquels, dans quel ordre ? → **Décidé le 17/11** : un seul commit `feat: parsing, normalization brick and Log* contracts` (état intermédiaire sur lequel on ne reviendra pas). Désormais : un commit par décision, au moment où on la prend. Pas d'ADR (processus). |
| A2 | ☑ | Les offres disparaissent : chaque jour sans passage complet réel est un historique perdu à jamais, alors que l'objectif n° 1 (évolution des clusters dans le temps) en dépend. | Comment lancer dès maintenant un passage complet quotidien, avec l'architecture actuelle (cron, Dagster minimal) ? Où stocker les vraies données ? → **Décidé le 18/11** : aucune extraction réelle tant que le projet est en développement ; l'historique antérieur au premier passage réel est accepté comme perdu. Options écartées : passage quotidien avec le code actuel, sitemap seul. Pas d'ADR (priorité de projet). |
| A3 | ☑ | Une catégorie, ~800 offres : probablement trop peu pour des clusters stables par période. | Quel périmètre de collecte : toutes les catégories jobup ? d'autres portails ? dans quel ordre ? → **ADR-0001 (Accepté le 18/11)** : `docs/adr/0001-perimetre-collecte.md`. Le `robots.txt` et les CGU de jobs.ch seront lus avant d'en développer le scraper. |
| A4 | ☐ | `ExtractedJob` a été défini sans ses consommateurs. Bonne pratique : contrats pilotés par le consommateur. | Les data scientists existent-ils déjà ? Leur poser : description complète ou sections séparées (missions, profil) ? langue ? HTML brut ? quel historique ? quelle granularité de période ? quelle fraîcheur ? (18/11 : avec le principe 3, leurs réponses façonnent les modèles silver/gold de dbt, plus la collecte.) |
| A5 | ☑ | Sans consommateur identifié, investir dans le parsing est risqué. | En attendant leurs réponses : garder le brut complet (déjà fait) et limiter l'investissement dans le parsing ? → **Décidé le 18/11 (principe 3)** : le parsing se limite à sortir le bloc brut (JSON-LD) ; tout le reste dans dbt. |

## B. Collecte

| # | Statut | Remarque | Question à trancher |
|---|---|---|---|
| B1 | ◐ | On reconstruit Scrapy à la main (spider par site, Items, callbacks, pipelines). Scrapy fournit déjà AutoThrottle, `robots.txt`, tentatives répétées, cache HTTP des réponses brutes, pause/reprise, concurrence. | Moteur maison, Scrapy utilisé comme bibliothèque (lancé depuis un script), ou `httpx` + bibliothèques (cache HTTP, retries) ? Critères : nombre de sites dans un an, pages JavaScript à rendre, transmission à l'équipe. (18/11 : alternatives recensées — Crawlee for Python, Scrapy + scrapy-playwright ; Scrapling écarté (contournement anti-bot) ; duel Crawlee / Scrapy à trancher après examen du 3e site. Les paginateurs de dlt ne servent qu'aux API JSON.) (18/11 après-midi : orientation de David vers un outil existant, Crawlee pressenti ; moteur maison écarté par le principe 3.) |
| B2 | ☐ | Objection : « Scrapy est une usine à gaz ». Vrai en partie (Twisted, réglages, projet imposé) pour un seul site. | Le mode bibliothèque lève-t-il l'objection ? Sinon, l'option `httpx` + bibliothèques suffit-elle ? |
| B3 | ☐ | Seules les fiches nouvellement téléchargées sont parsées ; le HTML déjà stocké n'est jamais reparsé. | Quand et comment reparser le brut existant (nouveau parseur, nouvelle librairie) ? (18/11 : avec le principe 3, le reparsing devient rare : on modifie un modèle dbt, pas l'extraction.) |
| B4 | ☐ | Pas de parseur de secours quand le JSON-LD est absent. | Nécessaire maintenant, ou on journalise l'échec et on attend le besoin ? (18/11 : orientation : à défaut de JSON, un JSON issu d'un scrap basique ou le texte issu du HTML, laissé à la normalisation.) |

## C. Stockage et chargement

| # | Statut | Remarque | Question à trancher |
|---|---|---|---|
| C1 | ☐ | `storage.read()` charge toute une table en mémoire Python, fichier par fichier, pour calculer le reste à faire. Contredit « Python garde peu en mémoire » et « le T est en SQL ». | Calculer les restes à faire avec DuckDB (anti-jointure sur les Parquet) ? Ou l'état incrémental de dlt ? (18/11 : orientation SQL, cohérente avec le principe 3 et « état dans les données ».) |
| C2 | ☐ | Un fichier Parquet par job : des milliers de petits fichiers en quelques semaines. | Compaction périodique ? Écriture par lots + reprise exacte autrement ? Laisser le data warehouse absorber ? |
| C3 | ☐ | Pas de stratégie d'évolution des schémas : l'ajout de `normalizer_description` a obligé à supprimer des données de test. | Comment lire côte à côte des fichiers d'anciennes et de nouvelles versions (union par nom, dlt, migrations) ? (18/11 : enveloppe minimale + bloc brut : le schéma du brut bouge peu ; l'évolution du contenu est absorbée par le staging dbt.) |
| C4 | ☐ | `IStorage` + `LocalParquetStorage` recouvrent `fsspec` / `pyarrow.dataset` (local ↔ S3/MinIO/GCS par simple URL). | Garder l'abstraction maison ou s'appuyer sur ces bibliothèques ? |
| C5 | ◐ | dlt couvre une bonne partie de `storage/` et du reste à faire : schéma déduit et évolutif, état incrémental, destinations Parquet / stockage objet, intégration Dagster. | Adopter dlt pour le chargement ? Où s'arrête-t-il, où commence notre code ? → Spike en cours (`spikes/dlt/`, branche `spike/dlt`). Orientations retenues le 18/11 : dlt charge les lignes produites par les scrapers, par lots réglables ; HTML brut hors dlt (responsabilité du scraper) ; état dans les données, pas d'état incrémental dlt ; configuration explicite dans le code ; **validation par Pydantic seulement** (le contrat de schéma de dlt est laissé en `evolve`, pour ne pas dépendre de dlt) ; **une seule version lue : `schema_version` du contrat** (`_dlt_version` reste interne à dlt) ; le contrat est la seule source de vérité, le schéma dlt en est généré. Nettoyage du dossier de travail dlt (copies des fichiers chargés) : à traiter au passage du spike au cas concret. Disposition des données retenue : `data/<producteur>/<table>/` (un dossier par site, `normalization/`), HTML dans `data/html/<site>/`. (18/11 après-midi : dlt confirmé pour le chargement ; test 2 redéfini (JSON brut dans une colonne, sans tables enfants) ; tests 3 à 5 abandonnés.) |
| C6 | ◐ | Cible : stockage objet → data warehouse → dbt. | Quel warehouse, quel outil de chargement, à quel moment ? (18/11 : chargement = dlt ; un moteur dbt est nécessaire dès maintenant ; dbt-duckdb sur les Parquet proposé, à trancher.) |

## D. Orchestration et configuration

| # | Statut | Remarque | Question à trancher |
|---|---|---|---|
| D1 | ◐ | « Dagster appelle des CLI » : une assurance contre un changement d'orchestrateur qu'on n'a pas (KISS : pas d'abstraction par anticipation). | Assets Dagster natifs appelant des fonctions Python, ou CLI en sous-processus ? Le passage à Airflow est-il un risque réel ? (18/11 : modèle d'exécution de Dagster expliqué — code locations (un par brique possible, chacun son environnement), briques sans import de Dagster ; éviter les générateurs `create-dagster` / `dg` / components YAML.) |
| D2 | ☐ | Limites de passage, rapports JSON, config Pydantic maison (`Config`, `run_limits`) recoupent la config, les métadonnées et les *resources* de Dagster. | Qui lance les passages : Dagster seul, ou aussi des humains en CLI ? Qu'est-ce qu'on garde en maison ? |
| D3 | ☐ | Signature des processeurs + hook pre-commit prévus. | Les métadonnées Dagster suffisent-elles ? Que garder de la signature (déjà dans les données : nom, version, description) ? |
| D4 | ☐ | `known_folders` pourrait servir à Dagster pour découvrir les sites et normaliseurs. | Découverte automatique ou liste explicite des assets ? |

## E. Structure du code

| # | Statut | Remarque | Question à trancher |
|---|---|---|---|
| E1 | ☐ | 7 packages dans un workspace uv pour environ 2 000 lignes. | Regrouper en 3 ou 4 packages (contrats, extraction, normalisation, orchestration) ? Qui installe quoi séparément ? |
| E2 | ☐ | `interfaces/` est partagé par toutes les briques : des briques « indépendantes » couplées par un package commun. | Interfaces dans chaque brique, seuls les contrats de données en commun ? (Le découpage `infrastructure/` / `use_cases/` réintroduit des couches de clean architecture, abandonnée le 13/11.) |
| E3 | ☐ | `parse(kind: str, content) -> object` sacrifie le typage à la règle « une seule méthode publique » (d'où des `isinstance`). | Deux méthodes typées, un type générique, ou garder tel quel ? |
| E4 | ☐ | `JobupOptions` importe le parseur avec son propre code, en double avec l'import de classes de `Config`. | Un seul utilitaire d'import (dans `common`) ? |
| E5 | ☐ | Le préfixe `log_` désigne deux choses : un bilan de passage (`log_raw_job_info`) et des échecs (`log_raw_job_detail`, `log_extracted_job`). | Garder, ou distinguer (ex. `failed_…` pour les échecs) ? |

## F. Contrats et données

| # | Statut | Remarque | Question à trancher |
|---|---|---|---|
| F1 | ☑ | Principe « format long », mais `NormalizedJob.skills` est une liste imbriquée. | Aplatir dans le contrat, ou écrire noir sur blanc que l'aplatissement se fait toujours en SQL ? (Spike : avec un modèle Pydantic, dlt écrit les listes en texte JSON, pas en tables enfants.) → **Décidé le 18/11 (principe 3)** : les listes restent telles quelles dans le brut ; l'aplatissement se fait dans dbt (silver). Écartés : aplatissement par dlt (tables enfants, dépendance à dlt), ligne par compétence dans le contrat (forme pensée pour une table future). |
| F2 | ☑ | `ExtractedJob` ne lit pas `addressRegion`, `workHours`, `jobBenefits`, alors que le JSON-LD les fournit. | Les ajouter maintenant ou attendre la demande des consommateurs (lié à A4) ? → **Sans objet depuis le 18/11 (principe 3)** : le JSON-LD est déposé complet ; dbt prend les champs dont il a besoin. |
| F3 | ☐ | Cadre juridique non traité : conditions d'utilisation des portails, données personnelles (nLPD). | Qui vérifie, avant la collecte réelle à grande échelle ? |
| F4 | ☑ | Spike dlt (18/11) : `AwareDatetime` (Pydantic) est écrit en texte par dlt ; un `datetime` + validateur de fuseau est écrit en horodatage. | → **Décidé le 18/11** : type date-heure maison dans `field_types.py` : `datetime` + validateur qui refuse une date naïve et ramène toute date en UTC (remplace `AwareDatetime`). Une date-heure naïve fournie par un portail est rendue explicite par le site lui-même, avec le fuseau du portail. Un job refusé est journalisé, jamais bloquant. Où ranger le fuseau d'un portail (configuration du site ou constante du code du site) : à décider quand un portail en aura besoin. ADR à rédiger avec C5. |
| F5 | ☐ | Les JSON Schema générés (`contracts/schemas/`) servent aux consommateurs non Python et à la lisibilité des revues ; tous les consommateurs connus sont en Python. | Garder la génération des JSON Schema ou la supprimer ? (18/11 : orientation de David : à supprimer à terme s'ils ne sont pas lus à l'extérieur.) |

## G. Principes et objections (à garder en tête à chaque décision)

| # | Statut | Remarque | Question à trancher |
|---|---|---|---|
| G1 | ☐ | Objection : « si on change d'outil, tout le projet est à revoir ». Réponse : la protection, ce sont les contrats ; l'enfermement vient de la logique métier écrite *dans* l'outil. | Adopter la règle « un outil est autorisé dans sa brique, jamais dans les contrats ni la logique métier » ? |
| G2 | ☐ | Objection : « classes natives pour rester agnostique ». Réponse : l'équipe hérite d'un framework maison sans documentation ni communauté ; un outil connu se transmet souvent mieux. | Pour chaque sujet : l'outil retire-t-il plus de complexité qu'il n'en ajoute ? |
| G3 | ◐ | Nomenclature qui a beaucoup changé en trois jours ; le cadrage mélange décisions et description. | Figer la nomenclature ; tenir les ADR à part du cadrage ? → **ADR à part : décidé le 18/11** (`docs/adr/`, Zensical). Nomenclature : à figer. |
| G4 | ☑ | Principes directeurs posés par David le 18/11. | Simple et explicite (peu d'implicite, pas de fichiers éparpillés) ; briques permettant le travail en parallèle sur crawlers et transformations. Voir en tête du document. |
