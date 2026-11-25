-- 02_raw_tables.sql
--
-- Description : les tables brutes de l'extraction et de la normalisation, une par
--               contrat (common/contracts), nommées comme dans common/catalog.
-- Règles      : colonnes = champs du contrat, un pour un ; rien n'est mis en forme.
--               Les blocs JSON (payload, card, listing_params) sont stockés en
--               jsonb : dbt peut en lire des clés, jamais en analyser le texte.
--               Le HTML d'origine reste dans le stockage objet, adressé par
--               hash_html_id.
--               Unicité sur les colonnes, sans hash : une ligne réécrite est ignorée
--               (insert ... on conflict do nothing). Les identifiants hash_<objet>_id
--               sont calculés par dbt, dans le staging.
--               _loaded_at = date d'insertion, ajoutée par la base.
--               Appliqué aux deux bases (vraies données et _dev) par
--               00_init_databases.sh : la zone de test est une base à part.

-- Une offre vue sur une page de résultats, une ligne par offre et par run.
create table raw.raw_job_info (
    schema_version  text        not null,
    run_id          text        not null,
    source          text        not null,
    is_test         boolean     not null,
    url             text        not null,
    seen_at         timestamptz not null,
    listing_params  jsonb       not null default '{}'::jsonb,
    card            jsonb,
    _loaded_at      timestamptz not null default now(),
    unique (run_id, source, url)
);

-- Journal d'un run d'extraction des offres d'une catégorie.
create table raw.log_raw_job_info (
    schema_version  text        not null,
    run_id          text        not null,
    source          text        not null,
    is_test         boolean     not null,
    listing_params  jsonb       not null default '{}'::jsonb,
    started_at      timestamptz not null,
    finished_at     timestamptz not null,
    status          text        not null check (status in ('completed', 'failed')),
    error           text,
    announced_total integer     check (announced_total >= 0),
    pages_read      integer     not null check (pages_read >= 0),
    jobs_seen       integer     not null check (jobs_seen >= 0),
    distinct_urls   integer     not null check (distinct_urls >= 0),
    _loaded_at      timestamptz not null default now()
);

-- Une page de détail téléchargée avec succès, avec son bloc de données brut.
-- Une ligne = une extraction d'une page (hash_html_id) par une version du scraper ;
-- (source, url) identifie l'offre.
create table raw.raw_job_detail (
    schema_version  text        not null,
    source          text        not null,
    is_test         boolean     not null,
    url             text        not null,
    hash_html_id    text        not null check (hash_html_id ~ '^[0-9a-f]{64}$'),
    content_type    text        not null,
    fetched_at      timestamptz not null,
    http_status     integer     not null check (http_status between 200 and 299),
    scraper         text        not null,
    scraper_version text        not null,
    payload_format  text        not null check (payload_format in ('json_ld', 'paragraphs')),
    payload         jsonb       not null,
    _loaded_at      timestamptz not null default now(),
    unique (hash_html_id, scraper, scraper_version)
);

-- Un échec de téléchargement d'une page de détail.
create table raw.log_raw_job_detail (
    schema_version  text        not null,
    source          text        not null,
    is_test         boolean     not null,
    url             text        not null,
    attempted_at    timestamptz not null,
    error           text        not null,
    _loaded_at      timestamptz not null default now()
);

-- Une normalisation d'une extraction : les compétences comprises, signées par le
-- normaliseur et son modèle. Rattachée à raw_job_detail par (hash_html_id,
-- scraper, scraper_version), recopiés tels quels.
create table raw.normalized_job (
    schema_version          text        not null,
    source                  text        not null,
    is_test                 boolean     not null,
    hash_html_id            text        not null check (hash_html_id ~ '^[0-9a-f]{64}$'),
    scraper                 text        not null,
    scraper_version         text        not null,
    normalizer              text        not null,
    normalizer_version      text        not null,
    model                   text        not null,
    model_version           text        not null,
    normalizer_description  text        not null,
    normalized_at           timestamptz not null,
    skills                  jsonb       not null default '[]'::jsonb,
    _loaded_at              timestamptz not null default now(),
    unique (
        hash_html_id, scraper, scraper_version,
        normalizer, normalizer_version, model, model_version
    )
);
