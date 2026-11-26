# Extraction

L'extraction lit les portails d'emploi comme le ferait un visiteur, par leurs pages web, et dépose ce
qu'elle lit **sans l'interpréter** ([ADR-0002](../adr/0002-elt-brut-minimal-dbt.md)).

## Un passage, en deux étapes

**Étape 1 : les pages de résultats.** Pour chaque catégorie suivie (ex. « informatique-télécommunications »),
l'extraction parcourt les pages de résultats, de la première à la dernière. Chaque offre y apparaît sous
forme de **carte** (titre, entreprise, lieu, dates). Elle écrit une ligne `raw_job_info` par offre vue,
avec sa carte brute en JSON. Le parcours complet d'une catégorie s'appelle un **passage** (*run*), identifié
par un `run_id`. À la fin de chaque catégorie, une ligne `log_raw_job_info` dit si le passage a réussi
(`completed`) ou échoué (`failed`, avec l'erreur). Une catégorie en échec n'arrête ni les autres, ni
l'étape 2.

On refait ce parcours à chaque passage : c'est ce qui permet de savoir quelles offres sont encore en ligne.

**Étape 2 : les fiches.** Pour chaque offre vue qui n'a pas encore été téléchargée, l'extraction ouvre sa
**fiche** (page de détail), **une seule fois**, une par une, et écrit chaque résultat aussitôt : un
plantage ne fait rien refaire de ce qui est déjà écrit.

- **Succès** : le HTML d'origine part dans RustFS, nommé par son empreinte
  (`raw_job_detail_html/<hash_html_id>.html`), puis une ligne `raw_job_detail` est écrite avec le **bloc de
  données** de la page (`payload`) : son JSON-LD tel quel (`payload_format = json_ld`) ; à défaut, la liste
  de ses paragraphes de texte (`paragraphs`).
- **Échec** (pas de réponse, statut HTTP hors 2xx) : une ligne `log_raw_job_detail`. Après
  `max_failures` échecs (3 par défaut), l'offre est **mise de côté** et n'est plus retentée.

Fiches à télécharger = offres vues − déjà téléchargées − mises de côté, dans l'ordre de première
apparition.

## Ce que fait un site, ce que fait le moteur

Chaque site possède **tout son processus** : comment il découpe ses offres, comment il lit ses pages, ce
qu'il journalise. Le code commun impose seulement ce qu'un site reçoit et ce qu'il rend :

| Élément | Où | Rôle |
|---|---|---|
| `ISiteExtractionUseCase` | `extraction/interfaces/i_site_extraction_uc.py` | la classe d'un site : reçoit stockages, limites, `get_page`… ; `execute()` rend un `ExtractionReport` |
| `IParser` | `extraction/interfaces/i_parser.py` | lit un contenu déjà téléchargé, sans requête ni écriture |
| `make_get_page` | `extraction/http.py` | télécharge une page : user agent, timeout, délai de politesse entre deux requêtes |
| `site.toml` | `extraction/<site>/site.toml` | la configuration du site : classe, délai, limites de test, catégories |
| `ExtractionSettings` | `extraction/settings.py` | réglages communs à tous les sites, lus dans `extraction/.env` |

C'est le **contrat**, pas le code, qui rend les données des sites comparables : tous les sites écrivent les
mêmes tables avec les mêmes contrats (`RawJobInfo`, `LogRawJobInfo`, `RawJobDetail`, `LogRawJobDetail`).

La commande ne connaît que le nom du site : `jobcompass-extraction run jobup` lit
`extraction/jobup/site.toml`, qui désigne la classe à utiliser. Toute la configuration est validée avant
la première requête.

## La politesse envers les sites

- Un délai minimal entre deux requêtes, réglé par site (`min_delay_between_requests`, 1 s pour jobup).
- Un **user agent** qui identifie JobCompass (`EXTRACTION_USER_AGENT`) : y mettre un contact avant toute
  collecte complète.
- Ni nouvelle tentative immédiate, ni cache : un échec est journalisé et retenté au passage suivant.

Le `robots.txt` et les conditions d'utilisation d'un portail se lisent **avant** d'en écrire l'extraction
([ADR-0001](../adr/0001-perimetre-collecte.md)).

## Les versions

Chaque site déclare un `name` et une `version` (ex. `jobup_extraction` 0.2.0), enregistrés avec chaque
fiche (`scraper`, `scraper_version`). Changer la façon de télécharger ou de lire les pages, parseur
compris, = monter la version. On peut alors relire le HTML stocké avec la nouvelle version : les lignes
s'ajoutent, et dbt garde la plus récente.

## jobup.ch, le premier site

- Pages de résultats : `https://www.jobup.ch/fr/emplois/<catégorie>/?page=<n>` ; les offres sont lues
  dans le JSON `__INIT__` intégré à la page.
- Fiches : le bloc JSON-LD de type `JobPosting`, sinon les paragraphes du texte visible.
- Code : `extraction/src/extraction/jobup/` (`jobup_extraction_uc.py`, `jobup_parser.py`, `site.toml`,
  `tests/` avec deux pages réelles en fixtures).

Pour ajouter un portail : [Ajouter un site](../guides/ajouter-un-site.md).
