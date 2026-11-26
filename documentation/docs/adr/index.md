# Décisions d'architecture (ADR)

Un ADR (*Architecture Decision Record*) consigne une décision structurante : son contexte, la décision,
les alternatives écartées et ses conséquences. Il explique **pourquoi** le projet est ainsi, pour l'équipe
qui le reprendra.

## Règles

- Un fichier par décision : `NNNN-titre-court.md`, numéroté dans l'ordre.
- Court : une page au plus.
- Statuts : **Proposé** → **Accepté** ; une décision remplacée passe en **Remplacé par ADR-NNNN**,
  jamais supprimée ni réécrite.
- Changer d'avis = un nouvel ADR qui remplace l'ancien.
- Les décisions de processus (commits, organisation du travail) ne font pas l'objet d'un ADR.

## Liste

| N° | Titre | Statut | Date |
|---|---|---|---|
| [0001](0001-perimetre-collecte.md) | Périmètre de collecte | Proposé | 2026-11-17 |
| [0002](0002-elt-brut-minimal-dbt.md) | ELT : brut minimal, transformations dans dbt, peu d'outils | Accepté, en partie remplacé (0003, 0007) | 2026-11-18 |
| [0003](0003-postgres-et-rustfs.md) | Stockage : Postgres et RustFS en conteneurs | Accepté | 2026-11-19 |
| [0004](0004-identifiants.md) | Identifiants : un seul hash calculé en Python | Accepté | 2026-11-19 |
| [0005](0005-test-et-production.md) | Test et production : deux bases, test par défaut | Accepté | 2026-11-20 |
| [0006](0006-normaliseur-courant.md) | Normalisations versionnées, normaliseur courant en table | Accepté | 2026-11-19 |
| [0007](0007-planification.md) | Planification : supercronic dans un conteneur, un passage par site | Accepté | 2026-11-25 |
| [0008](0008-plusieurs-sites.md) | Plusieurs sites : un staging par site, réunis dans intermediate | Accepté | 2026-11-26 |

## Écrire un ADR

Copier un ADR existant (par exemple [0007](0007-planification.md)) : en-tête (statut, date, décideur, ce
qu'il remplace), puis **Contexte**, **Décision**, **Alternatives écartées**, **Conséquences**. Ajouter sa
ligne au tableau ci-dessus et à `nav` dans `documentation/zensical.toml`.
