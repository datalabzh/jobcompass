# JobCompass

JobCompass analyse le marché de l'emploi en Suisse romande à partir des offres publiées sur les portails
d'emploi (jobup.ch pour l'instant). Constat de départ : un intitulé de poste ne dit plus grand-chose —
des titres différents recouvrent les mêmes compétences, un même titre recouvre des réalités différentes.
JobCompass remplace donc la taxonomie figée des métiers par des **clusters de compétences** calculés à
partir des offres réelles, et suit leur évolution dans le temps.

Le projet est développé par une association : cette documentation est la référence commune, et chacun
peut la corriger ou la compléter.

## Par où commencer

| Tu veux… | Lis |
|---|---|
| découvrir le projet et le faire tourner chez toi | [Installation](prise-en-main/installation.md), puis [Lancer la chaîne](prise-en-main/lancer-la-chaine.md) |
| comprendre comment c'est construit | [Vue d'ensemble](architecture/vue-d-ensemble.md) |
| collecter un nouveau portail | [Ajouter un site](guides/ajouter-un-site.md) |
| brancher un vrai modèle NLP | [Ajouter un normaliseur](guides/ajouter-un-normaliseur.md) |
| analyser les données en SQL | [Transformation (dbt)](architecture/transformation.md) |
| faire tourner la collecte chaque jour | [Planification](prise-en-main/planification.md) |
| savoir pourquoi le projet est ainsi | [Décisions d'architecture (ADR)](adr/index.md) |

## Organisation de la documentation

- **Prise en main** : installer, lancer, planifier. À lire dans l'ordre la première fois.
- **Guides** : « comment faire… », une tâche par page, étapes numérotées.
- **Architecture** : comment c'est construit et pourquoi, brique par brique.
- **Conventions** : les règles d'écriture du code (Python, dbt, tests).
- **ADR** : les décisions structurantes, datées, avec leurs alternatives écartées.

Le suivi du projet au jour le jour (carte, journal de bord) est à part, dans le dossier `suivi/` du dépôt.

## Modifier cette documentation

Les pages sont des fichiers Markdown dans `documentation/docs/`. Pour voir le résultat pendant que tu
écris, depuis la racine du dépôt :

```bash
uv run zensical serve -f documentation/zensical.toml   # http://localhost:8000, rechargé à chaque modification
```

Une nouvelle page s'ajoute aussi au menu, dans `nav` de `documentation/zensical.toml`.
