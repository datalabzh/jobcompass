# ADR-0001 — Périmètre de collecte

- **Statut** : Proposé
- **Date** : 2026-11-17
- **Décideur** : David

## Contexte

Les clusters de compétences par période demandent du volume : une seule catégorie d'un seul portail
(environ 800 offres sur jobup) est probablement insuffisante. La collecte est plafonnée par la politesse
envers les sites (environ une requête par seconde et par site), pas par le code : même jobup en entier
(environ 31 000 offres) tient en moins d'une heure par jour. La difficulté de passage à l'échelle tient donc
au nombre et à l'hétérogénéité des sources, pas au volume. Le projet sera repris par une équipe qui pourra
élargir le périmètre.

## Décision

- Au plus **trois portails** à douze mois : jobup.ch, jobs.ch (même groupe, structure proche), et un
  troisième à choisir.
- **Catégorie informatique** uniquement pour commencer.
- Ajouter une catégorie = ajouter une ligne dans la configuration du site, sans développement.
- Données lues dans le HTML et le JSON intégré aux pages. Une API interne n'est utilisée que si le
  `robots.txt` et les conditions d'utilisation du portail l'autorisent. Rendu JavaScript en dernier recours.
- Toute l'offre de la catégorie est collectée ; région et langue se filtrent en SQL.

## Alternatives écartées

- **Toutes les catégories dès maintenant** : volume et temps de développement sans besoin exprimé.
- **LinkedIn, Indeed** : le scraping est interdit par leurs conditions d'utilisation.
- **API internes interdites par `robots.txt`** (ex. `/api/` sur jobup) : contournement d'une règle explicite
  du site, risque juridique pour un projet d'équipe.

## Conséquences

- Une même offre peut être publiée sur jobup et jobs.ch : dédoublonnage entre portails à prévoir en
  transformation (dbt), sinon les cooccurrences de compétences sont faussées.
- jobs.ch couvre toute la Suisse (beaucoup d'offres en allemand) : filtre région et langue en SQL ; le brut
  reste complet et le filtre réversible.
- Volume total à confirmer avec les data scientists (consommateurs des données).
- Rien n'est construit « pour d'autres catégories » au-delà de la liste dans la configuration du site.

## Points à lever avant acceptation

- Validation par David.
- Lecture du `robots.txt` de jobs.ch.
