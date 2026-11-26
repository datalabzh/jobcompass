# Données

## Bases et schémas

Postgres 17 (conteneur `jobcompass-postgres`) contient **deux bases**, avec exactement les mêmes schémas et
les mêmes tables :

| Base | Contenu |
|---|---|
| `jobcompass` | la production : les vraies données |
| `jobcompass_dev` | le test : passages limités et tests automatiques |

| Schéma | Contenu | Écrit par |
|---|---|---|
| `raw` | les tables brutes, en **ajout seul** | extraction, normalisation |
| `config` | les tables de configuration, seules tables modifiées à la main | l'équipe |
| `staging`, `intermediate`, `marts` | les couches dbt | dbt |

Les tables `raw` et `config` sont créées au premier démarrage par `infra/postgres/init/` ; les schémas dbt
par dbt.

## Tables brutes

| Table | Une ligne par… | Contrat | Écrite par |
|---|---|---|---|
| `raw.raw_job_info` | offre vue sur une page de résultats, par passage (avec sa carte JSON) | `RawJobInfo` | extraction, étape 1 |
| `raw.log_raw_job_info` | passage d'une catégorie (`completed` ou `failed`, compteurs) | `LogRawJobInfo` | extraction, étape 1 |
| `raw.raw_job_detail` | fiche téléchargée, par version de l'extraction (avec son bloc de données) | `RawJobDetail` | extraction, étape 2 |
| `raw.log_raw_job_detail` | téléchargement de fiche échoué | `LogRawJobDetail` | extraction, étape 2 |
| `raw.normalized_job` | normalisation d'une fiche (compétences, signature du normaliseur) | `NormalizedJob` | normalisation |

- **Ajout seul** : on n'y modifie ni n'y supprime rien. Relancer une étape ne crée pas de doublon : chaque
  table a une contrainte d'unicité, et une ligne déjà présente est ignorée (`on conflict do nothing`).
- **Colonnes = champs du contrat**, un pour un. Les contrats sont dans `common/contracts/` ; chacun porte
  un `schema_version`, monté à chaque changement de forme.
- Les blocs JSON (carte, bloc de données, compétences) sont en `jsonb` : dbt en lit des clés.
- `_loaded_at` : date d'insertion, ajoutée par la base.

## Tables de configuration

| Table | Une ligne par… | Rôle |
|---|---|---|
| `config.site` | site connu | le registre des sites : dbt refuse un site absent |
| `config.normalizer` | normaliseur et version | `is_current` désigne celui qui alimente les marts (un seul) |

Chaque base a sa copie : on peut tester un autre normaliseur courant dans la base de test.

## Le stockage objet (RustFS)

Le HTML d'origine de chaque fiche est conservé tel quel dans RustFS (compatible S3), bucket
`jobcompass-raw` :

- clé = `raw_job_detail_html/<hash_html_id>.html` ;
- en test, précédé de `dev/` : supprimer `dev/` efface toutes les données de test ;
- une page identique n'est écrite qu'une fois.

C'est la preuve de ce qui a été lu, et la possibilité de relire les pages si l'on apprend à mieux les lire.

## Les identifiants

- **`hash_html_id`** : SHA-256 du HTML d'une fiche, en hexadécimal. C'est le **seul** identifiant calculé en
  Python (`compute_hash_html_id`, dans `common/contracts/`) ; c'est aussi le nom du fichier dans RustFS.
- Tous les autres identifiants sont calculés **dans le staging dbt**, nommés `hash_<objet>_id`
  (ex. `hash_job_id` = empreinte de la source et de l'URL, qui identifie une offre).

Une offre est identifiée par `(source, url)` ; une fiche par `(hash_html_id, scraper, scraper_version)`.

## La traçabilité

```
marts.skills__job_skills ──hash_job_id──► marts.jobs__job_offers ──hash_html_id──► RustFS
```

Depuis n'importe quelle ligne d'analyse, on retrouve l'offre, puis le fichier HTML d'origine.
