# Règles métier

## Une offre est-elle encore en ligne ?

À chaque passage, on relit toutes les pages de résultats de chaque catégorie. Une offre est **active**
(`is_active`) si elle apparaissait lors du **dernier passage réussi** d'au moins une de ses catégories, sur
son site. Une catégorie est propre à son site : deux sites peuvent avoir une catégorie du même nom sans se
mélanger.

Un passage qui échoue (site en panne, page illisible) n'est pas pris en compte : sinon, toutes ses offres
sembleraient avoir disparu. La catégorie garde l'état de son dernier passage réussi.

`first_seen_at` et `last_seen_at` donnent la première et la dernière fois où l'offre a été vue ;
`runs_seen` le nombre de passages qui l'ont vue.

Attention : une catégorie retirée de la configuration d'un site garde ses offres actives, puisque son
dernier passage réussi reste le même.

## Suit-on les modifications d'une offre ?

Non. Chaque fiche n'est téléchargée qu'une fois ; ensuite, on suit seulement la présence de l'offre dans les
pages de résultats.

## D'où viennent le titre, l'entreprise et la date de publication ?

De la fiche, si elle a été téléchargée et contient un JSON-LD ; sinon, de la carte de l'offre dans les pages
de résultats (la plus récente). `has_detail` indique si la fiche a été téléchargée (en test, seules quelques
fiches le sont).

## Et si une fiche a été extraite plusieurs fois ?

Quand l'extraction d'un site change de version, une fiche peut être relue depuis son HTML d'origine. On
garde la lecture de la version la plus récente (`scraper_version`, comparée nombre par nombre : 0.10.0
après 0.9.0), puis la plus récente dans le temps. Les versions s'écrivent donc toujours `x.y.z`, avec des
nombres seulement (vérifié par un test dbt).

## D'où viennent les compétences ?

D'un **normaliseur**. Plusieurs peuvent coexister, et leurs résultats sont tous gardés ; un seul est
**courant** (`config.normalizer`), et lui seul alimente les marts. Si un même normaliseur a plusieurs
modèles sur une fiche, on garde la normalisation la plus récente.

Une compétence n'apparaît qu'une fois par offre ; `skills__job_skills` a une ligne par offre et par
compétence canonique.

## Quand une fiche est-elle abandonnée ?

Après 3 téléchargements échoués (`EXTRACTION_MAX_FAILURES`), l'offre est mise de côté et n'est plus
retentée. Elle reste dans les marts, sans fiche (`has_detail = false`).

## Les données de test comptent-elles ?

Jamais. Elles sont dans une base à part et marquées `is_test = true` (voir
[Test et production](test-et-production.md)).
