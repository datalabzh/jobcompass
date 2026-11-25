# JobCompass

JobCompass analyse le marché de l'emploi en Suisse romande à partir des offres publiées sur plusieurs portails
(jobup.ch pour l'instant). Un intitulé de poste ne dit plus grand-chose : le projet remplace la taxonomie figée
des métiers par des **clusters de compétences** issus des offres réelles, et suit leur évolution dans le temps.

## Comment ça marche

Les offres sont collectées sur des portails d'emploi (aujourd'hui jobup.ch), lus comme le ferait un visiteur :
par leurs pages web. Quand un portail propose une API autorisée, on peut la lire à la place ; ce n'est le cas
d'aucun portail pour l'instant.

**Étape 1 : lire les pages de résultats (extraction).** Pour chaque catégorie suivie (ex.
« informatique-télécommunications »), on parcourt toutes les pages de résultats, de la première à la dernière.
Une page de résultats liste une vingtaine d'offres ; chaque offre y apparaît sous forme de **carte** (titre,
entreprise, lieu, dates), lue dans le JSON que le portail intègre à la page. On enregistre chaque offre vue avec
sa carte, sans la modifier. Ce parcours complet d'une catégorie s'appelle un **passage** ; on le refait à chaque
fois, pour savoir quelles offres sont encore en ligne et lesquelles ont disparu. À la fin de chaque catégorie, un
journal note si le passage a réussi ou échoué, et combien d'offres il a vues.

**Étape 2 : télécharger les fiches (extraction).** Pour chaque offre vue qui n'a pas encore été téléchargée, on
ouvre sa **fiche** (sa page de détail), une seule fois. On conserve :

- le **HTML d'origine** de la fiche, tel quel, dans le stockage objet (RustFS) : c'est la preuve de ce qu'on a
  lu, et il permet de refaire une extraction plus tard si l'on apprend à mieux lire les pages ;
- le **bloc de données** (`payload`) : la partie utile de la fiche, recopiée sans interprétation. C'est le
  JSON-LD de la page (des données structurées que le site y intègre : titre, description, entreprise…) quand il
  existe, sinon la liste des paragraphes du texte.

Un téléchargement qui échoue est noté dans un journal ; après trois échecs, l'offre est mise de côté.

**Étape 3 : extraire les compétences (normalisation).** Un **normaliseur** lit le bloc de données de chaque fiche
(titre et description, ou paragraphes) et en tire la liste des compétences demandées, sous leur forme brute
(« Postgres ») et canonique (« postgresql »). Chaque résultat est signé du nom et de la version du normaliseur,
pour pouvoir comparer plusieurs normaliseurs sur les mêmes fiches.

**Étape 4 : construire les tables d'analyse (dbt).** dbt assemble le tout en SQL : les offres, leur présence dans
le temps et leurs compétences. Le résultat, ce sont les **marts**, prêts à être interrogés.

Principe : les étapes 1 et 2 rangent les données **sans les interpréter** (ELT). Seule l'étape 3 lit du texte, en
Python ; dbt ne fait que du SQL.

## Ce qui est stocké

| Où | Contenu | Écrit par |
|---|---|---|
| `raw.raw_job_info` | une ligne par offre vue dans un passage, avec sa carte | étape 1 |
| `raw.log_raw_job_info` | le journal de chaque passage (réussi ou échoué, nombre d'offres) | étape 1 |
| RustFS, bucket `jobcompass-raw` | le HTML d'origine de chaque fiche, nommé par son empreinte `hash_html_id` | étape 2 |
| `raw.raw_job_detail` | une ligne par fiche téléchargée, avec son bloc de données | étape 2 |
| `raw.log_raw_job_detail` | les téléchargements échoués | étape 2 |
| `raw.normalized_job` | les compétences de chaque fiche, signées par le normaliseur | étape 3 |
| `config.normalizer` | le normaliseur dont les résultats sont utilisés (seule table modifiée à la main) | à la main |
| `marts.jobs__job_offers` | une ligne par offre : présence, statut actif, titre, description | étape 4 |
| `marts.skills__job_skills` | une ligne par offre et compétence | étape 4 |

Les tables du schéma `raw` sont en **ajout seul** : on n'y modifie ni n'y supprime rien, et relancer une étape
n'y crée pas de doublons. Chaque table existe dans deux bases (voir « Test ou production »).

## Organisation du code

Monorepo en workspace [uv](https://docs.astral.sh/uv/) : chaque brique est un package avec ses propres
dépendances. Les briques ne s'appellent pas entre elles : chacune lit ce que la précédente a déposé en base.

| Dossier | Rôle |
|---|---|
| `extraction/` | Étapes 1 et 2, un dossier par site (`jobup/`, avec son `site.toml`) |
| `normalization/` | Étape 3, un dossier par normaliseur (`fake/`, avec son `normalizer.toml`) |
| `dbt/` | Étape 4 : staging → intermediate → marts |
| `entrypoints/` | Les lignes de commande des étapes 1 à 3 |
| `storage/` | Écriture dans Postgres et dans RustFS |
| `common/` | Contrats de données (Pydantic), noms des tables, interfaces communes |
| `infra/` | Postgres et RustFS en conteneurs Docker |
| `orchestration/` | Planification : script de la chaîne, heure (cron), image du conteneur `pipeline` |
| `documentation/` | Documentation : décisions d'architecture, conventions (sources dans `docs/`) |
| `suivi/` | Suivi du projet : carte du projet, journal de bord |

## Prérequis

- Docker et Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.12 ou plus)

## Démarrage

Tout se lance **depuis la racine du dépôt**.

```bash
# 1. Variables de l'infrastructure (fichier non versionné)
cp infra/.env.example infra/.env        # puis changer les mots de passe

# 2. Postgres 17 + RustFS
docker compose -f infra/docker-compose.yml up -d --wait

# 3. Dépendances de toutes les briques
uv sync --all-packages
```

Console RustFS : http://localhost:9001.

## Lancer la chaîne

```bash
# Étapes 1 et 2 : extraction de jobup.ch
uv run --package jobcompass-entrypoints jobcompass-extraction run jobup

# Étape 3 : normalisation des fiches téléchargées
uv run --package jobcompass-entrypoints jobcompass-normalization run jobup

# Étape 4 : tables d'analyse
uv run --env-file infra/.env --package jobcompass-dbt dbt build --project-dir dbt --profiles-dir dbt --target dev
```

Les options ne s'affichent qu'avec `run --help` (ex. `jobcompass-extraction run --help`). Pour la normalisation,
`--normalizer <dossier>` choisit un autre normaliseur que celui par défaut (`normalization.toml`).

## Planification

La chaîne peut tourner seule, chaque jour, dans le conteneur `pipeline` : supercronic y lance
`orchestration/run_pipeline.sh` (extraction, normalisation, puis dbt) à l'heure fixée dans
`orchestration/jobcompass.cron`. Le conteneur démarre avec les autres :

```bash
docker compose -f infra/docker-compose.yml up -d --build --wait
docker compose -f infra/docker-compose.yml logs -f pipeline     # suivre les passages
```

| Pour… | Modifier | Puis |
|---|---|---|
| changer l'heure | la ligne de `orchestration/jobcompass.cron` (heure de Zurich) | `docker compose -f infra/docker-compose.yml restart pipeline` |
| passer en production | `PIPELINE_MODE=full` dans `orchestration/.env` (modèle : `.env.example`) | idem |
| prendre en compte une modification du code Python ou dbt | — | `docker compose -f infra/docker-compose.yml up -d --build pipeline` |

Par défaut (`PIPELINE_MODE=test`), un passage planifié va en test, comme les commandes à la main.
Le script se lance aussi à la main : `./orchestration/run_pipeline.sh` (ou
`PIPELINE_MODE=full ./orchestration/run_pipeline.sh`). Si une catégorie échoue à l'extraction, la
normalisation et dbt tournent quand même, et le passage finit en échec (code 1).

## Test ou production

Postgres contient **deux bases**, avec exactement les mêmes tables :

- `jobcompass_dev` : la **base de test** ;
- `jobcompass` : la **base de production**, les vraies données.

**Par défaut, tout va en test : c'est une sécurité.** Sans l'option `--full`, une commande ne peut ni écrire en
production ni charger tout un site :

| Commande | Où vont les données | Ce qui est téléchargé ou traité |
|---|---|---|
| `run jobup` (sans option) | base de test `jobcompass_dev` (+ préfixe `dev/` dans RustFS) | limité par la configuration : pour jobup, **1 page** de résultats et **2 fiches** (`site.toml`) ; 10 fiches pour la normalisation (`normalizer.toml`) |
| `run jobup --max-pages N --max-jobs N` | base de test `jobcompass_dev` | les limites données ; c'est toujours un test |
| `run jobup --full` | **base de production `jobcompass`** | tout, sans limite |

`--full` ne se combine pas avec `--max-pages` ou `--max-jobs`. Les données de test sont aussi marquées
`is_test = true`.

dbt suit la même règle : `--target dev` (la valeur par défaut) lit et écrit dans la base de test ;
`--target real` dans la base de production.

## Règles métier

**Comment sait-on qu'une offre est encore en ligne ?**
À chaque passage, on relit toutes les pages de résultats d'une catégorie. Une offre est **active** (`is_active`)
si elle apparaissait lors du dernier passage réussi de sa catégorie. Un passage qui échoue (site en panne, page
illisible) n'est pas pris en compte : sinon, toutes ses offres sembleraient avoir disparu. `first_seen_at` et
`last_seen_at` donnent la première et la dernière fois où l'offre a été vue.

**Est-ce qu'on suit les modifications d'une offre ?**
Non : chaque fiche n'est téléchargée qu'une fois. Ensuite, on suit seulement sa présence dans les pages de
résultats.

**D'où viennent le titre, l'entreprise et la date de publication ?**
De la fiche, si elle a été téléchargée et contient un JSON-LD ; sinon, de la carte de l'offre dans les pages de
résultats. `has_detail` indique si la fiche a été téléchargée (en test, seules quelques fiches le sont).

**Et si une fiche a été extraite plusieurs fois ?**
Quand le programme d'extraction change de version, une fiche peut être relue depuis son HTML d'origine. On garde
la lecture faite par la version la plus récente (`scraper_version`), puis la plus récente dans le temps.

**D'où viennent les compétences ?**
D'un **normaliseur**. Plusieurs normaliseurs peuvent coexister, et leurs résultats sont tous gardés ; un seul est
**courant**, choisi dans la table `config.normalizer`, et lui seul alimente les marts. Aujourd'hui, c'est un
normaliseur provisoire (`fake_normalization`) : il reprend les compétences déclarées par le site et repère une
trentaine de mots-clés techniques, en attendant un vrai normaliseur.

**À quel niveau de détail sont les compétences ?**
`skills__job_skills` contient une ligne par offre et par compétence, avec les jours où l'offre a été vue. Les
comptes par jour, semaine ou mois se calculent à partir de cette table.

**Comment relier une offre à son HTML d'origine ?**
Chaque fiche est identifiée par l'empreinte de son HTML (`hash_html_id`), qui est aussi le nom du fichier dans
RustFS. Les deux marts contiennent cette colonne : depuis n'importe quelle ligne, on retrouve directement le
fichier. Les autres identifiants (`hash_<objet>_id`) sont calculés par dbt.

## Tests automatiques

```bash
# Tests Python, brique par brique (les conteneurs doivent tourner ; ils écrivent dans la base de test)
for p in common/contracts common/catalog common/interfaces storage extraction normalization entrypoints; do
  (cd $p && uv run pytest -q) || break
done
```

Les tests dbt sont lancés par `dbt build` (voir « Lancer la chaîne »).

## Pièges connus

- **Modifier un script SQL de `infra/postgres/init/`** : il n'est exécuté qu'au premier démarrage. Repartir de
  volumes vides (ce qui efface les données des deux bases) :
  ```bash
  docker compose -f infra/docker-compose.yml down -v
  docker compose -f infra/docker-compose.yml up -d --wait
  ```
- **Fichiers illisibles par Postgres** (« Permission denied » à l'initialisation) : les scripts doivent être en
  `644` et leurs dossiers en `755`.
  ```bash
  find infra/postgres -type d -exec chmod 755 {} +
  find infra/postgres -type f -exec chmod 644 {} +
  chmod 755 infra/postgres/init/00_init_databases.sh
  ```
- **Docker : « veth … operation not supported »** : le noyau a été mis à jour sans redémarrage ; redémarrer la
  machine.

## Documentation

La documentation (décisions d'architecture, conventions dbt) est dans `documentation/` : les pages dans
`documentation/docs/`, la configuration dans `documentation/zensical.toml`. Elle est publiée avec
[Zensical](https://zensical.org), installé par `uv sync --all-packages` (groupe de dépendances `dev`).
Pour la consulter, depuis la racine du dépôt :

```bash
uv run zensical serve -f documentation/zensical.toml   # aperçu sur http://localhost:8000
```

Pour générer le site statique dans `documentation/site/` (non versionné) :
`uv run zensical build -f documentation/zensical.toml`.

Le suivi du projet est dans `suivi/` : `suivi/PROJECT_MAP.md` (carte du projet) et `suivi/DEVLOG.md` (journal de
bord).
