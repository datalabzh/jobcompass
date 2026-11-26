# Normalisation

La normalisation est la seule étape qui **lit du texte** : elle tire de chaque fiche la liste des
compétences demandées. C'est là que l'équipe NLP intervient.

## Entrée et sortie

```
raw.raw_job_detail  ──►  normaliseur  ──►  raw.normalized_job
(bloc de données brut)                     (compétences signées)
```

- **Entrée** : les lignes de `raw_job_detail` d'une source, avec leur `payload` (JSON-LD ou paragraphes).
- **Sortie** : une ligne `normalized_job` par fiche, avec la liste `skills` ; chaque compétence a sa forme
  brute (`raw`, « Postgres »), sa forme canonique (`canonical`, « postgresql ») et son origine (`declared`
  si le site la donne comme telle, `detected` si le normaliseur l'a trouvée dans le texte).
- Chaque ligne recopie telles quelles la clé de la fiche (`hash_html_id`, `scraper`, `scraper_version`) :
  la normalisation ne calcule aucun identifiant ; dbt retrouve l'offre par jointure.

## La signature et les versions

Chaque normaliseur déclare **quatre noms et versions et une phrase** : `normalizer`,
`normalizer_version`, `model`, `model_version`, `description`. Ils sont écrits sur chaque ligne. Une classe
qui en oublie un est refusée dès son chargement.

- Changer le modèle ou sa liste de mots = monter `model_version`.
- Changer ce que le normaliseur lit ou écrit = monter `normalizer_version`.

Une nouvelle version **ajoute** des lignes : elle normalise à nouveau toutes les fiches, et les anciennes
lignes restent. On peut ainsi comparer deux normaliseurs sur les mêmes fiches, en SQL.

## Quelles fiches sont traitées ?

Fiches en attente = lignes de `raw_job_detail` − fiches déjà normalisées par ce normaliseur, ce modèle et
leurs versions. Elles sont traitées de la plus ancienne à la plus récente, une par une, chacune écrite
aussitôt.

Une fiche qui **ne peut pas être normalisée** (bloc de données inattendu) est journalisée, comptée dans
`failed` du rapport et sautée : elle ne bloque pas les suivantes, et elle est retentée au passage suivant.

## Le normaliseur courant

Plusieurs normaliseurs peuvent coexister dans `normalized_job`. Deux réglages disent lequel sert :

| Réglage | Où | Effet |
|---|---|---|
| `default` | `normalization/src/normalization/normalization.toml` | le normaliseur **lancé** sans option `--normalizer` (donc par la planification) |
| `is_current` | table `config.normalizer` | le normaliseur dont les résultats **alimentent les marts** |

On peut donc faire tourner un nouveau normaliseur à côté de l'ancien, comparer, puis basculer les marts
d'une seule transaction SQL. Marche à suivre : [Ajouter un normaliseur](../guides/ajouter-un-normaliseur.md).

## Le normaliseur factice

En attendant le vrai, `fake` (`fake_normalization` 0.2.0, modèle `keyword_list` 0.1.0) fait tourner toute la
chaîne :

- compétences **déclarées** : la clé `skills` du JSON-LD, gardée telle quelle (forme canonique = en
  minuscules) ;
- compétences **détectées** : une trentaine de technos (python, sql, docker, dbt…) cherchées dans le titre
  et la description, en mots entiers, sans tenir compte de la casse.

Il ne sert qu'à vérifier la chaîne : ses résultats ne disent rien du marché.

## La suite

Les objectifs du projet prévoient ensuite, toujours en Python et en batch : les embeddings des compétences,
puis le calcul des clusters (cooccurrence pondérée, détection de communautés). Ils suivront le même
principe : lire une table, écrire une nouvelle table brute, reprise par dbt.
