# Vue d'ensemble

## Le flux

```
portails d'emploi
      │
      ▼
┌──────────────┐   HTML brut ──────────────►  RustFS (bucket jobcompass-raw)
│  extraction  │
└──────────────┘   raw_job_info, log_raw_job_info,
      │            raw_job_detail, log_raw_job_detail ──►  Postgres, schéma raw
      ▼
┌──────────────┐
│normalisation │   normalized_job ─────────────────────►  Postgres, schéma raw
└──────────────┘
      │
      ▼
┌──────────────┐   staging → intermediate → marts ─────►  Postgres, schémas dbt
│     dbt      │   (lit aussi config.site et config.normalizer)
└──────────────┘
      │
      ▼
analyse en SQL, clusters de compétences, visualisations
```

La planification (`orchestration/`) enchaîne ces étapes chaque jour : un passage par site
(extraction puis normalisation), puis dbt pour tous les sites.

## Trois briques indépendantes

| Brique | Dossier | Rôle | Écrit |
|---|---|---|---|
| Extraction | `extraction/` | collecte les pages des portails, un dossier par site | HTML brut, tables `raw_job_*` |
| Normalisation | `normalization/` | tire les compétences des fiches, un dossier par normaliseur | `normalized_job` |
| Transformation | `dbt/` | assemble et met en forme, en SQL | schémas `staging`, `intermediate`, `marts` |

Les briques **ne s'appellent jamais entre elles** : chacune lit ce que la précédente a déposé en base. Elles
partagent seulement :

- les **contrats de données** (`common/contracts/`) : une classe Pydantic par table brute, qui fixe ses
  colonnes ;
- le **catalogue** des tables (`common/catalog/`) : le nom de chaque table, défini une seule fois ;
- le **stockage** (`storage/`) : l'écriture dans Postgres et dans RustFS.

Chaque équipe peut donc travailler en parallèle : l'équipe NLP sur un normaliseur, une autre sur un
nouveau site, une autre sur les analyses, tant que les contrats sont respectés.

## Organisation du dépôt

| Dossier | Contenu |
|---|---|
| `extraction/` | moteur commun et un dossier par site (`jobup/`, avec son `site.toml`) |
| `normalization/` | un dossier par normaliseur (`fake/`, avec son `normalizer.toml`) |
| `dbt/` | le projet dbt |
| `entrypoints/` | les lignes de commande de l'extraction et de la normalisation |
| `storage/` | écriture et lecture dans Postgres et RustFS |
| `common/` | contrats, catalogue des tables, interface commune des cas d'utilisation |
| `infra/` | Postgres, RustFS et le conteneur `pipeline` (docker compose), scripts SQL d'initialisation |
| `orchestration/` | scripts de passage, planification (cron), image du conteneur `pipeline` |
| `pre-commit/` | outillage des contrôles avant commit (SQLFluff) |
| `documentation/` | cette documentation |
| `suivi/` | suivi du projet : carte, journal de bord |

Le dépôt est un **workspace [uv](https://docs.astral.sh/uv/)** : chaque brique est un package avec ses
propres dépendances. Installer la commande d'extraction n'installe pas les bibliothèques NLP de la
normalisation, et inversement.

## Les principes

- **KISS** : la solution la plus simple. Un outil, une couche ou une abstraction ne s'ajoute que pour un
  besoin réel, jamais par anticipation.
- **ELT** ([ADR-0002](../adr/0002-elt-brut-minimal-dbt.md)) : Python extrait et dépose la donnée telle
  quelle ; toute mise en forme se fait en SQL, dans dbt. Le SQL, lui, n'analyse jamais de texte : c'est le
  rôle de la normalisation.
- **Brut immuable** : le HTML de chaque fiche est conservé tel quel, adressé par son empreinte
  (`hash_html_id`), car les offres disparaissent des portails. Les tables brutes sont en ajout seul.
- **Traçabilité** : depuis n'importe quelle ligne d'analyse, on remonte à l'offre, puis au HTML d'origine.
- **Versions qui coexistent** : chaque extraction et chaque normalisation sont signées de leur version ;
  une nouvelle version ajoute des lignes, sans effacer les anciennes, pour pouvoir comparer.
- **Test par défaut** : sans option explicite, rien n'écrit en production
  ([Test et production](test-et-production.md)).

## Pour aller plus loin

- [Extraction](extraction.md), [Normalisation](normalisation.md), [Transformation](transformation.md) :
  chaque brique en détail.
- [Données](donnees.md) : bases, schémas, tables, stockage objet.
- [Règles métier](regles-metier.md) : offre active, versions, normaliseur courant.
