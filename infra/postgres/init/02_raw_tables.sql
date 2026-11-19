-- 02_raw_tables.sql
--
-- Description : les tables brutes de l'extraction, une par contrat
--               (common/contracts), nommées comme dans common/catalog.
-- Règles      : colonnes = champs du contrat, un pour un ; rien n'est mis en forme.
--               Les blocs JSON (payload, card, listing_params) sont stockés en
--               jsonb : dbt peut en lire des clés, jamais en analyser le texte.
--               Le HTML d'origine reste dans le stockage objet, adressé par raw_hash.
--               _loaded_at = date d'insertion, ajoutée par la base.
--               raw_test reprend la structure de raw à l'identique.

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
-- raw_hash identifie une version de la page ; (source, url) identifie l'offre.
create table raw.raw_job_detail (
    schema_version  text        not null,
    source          text        not null,
    is_test         boolean     not null,
    url             text        not null,
    raw_hash        text        not null unique check (raw_hash ~ '^[0-9a-f]{64}$'),
    content_type    text        not null,
    fetched_at      timestamptz not null,
    http_status     integer     not null check (http_status between 200 and 299),
    scraper         text        not null,
    scraper_version text        not null,
    payload_format  text        not null check (payload_format in ('json_ld', 'paragraphs')),
    payload         jsonb       not null,
    _loaded_at      timestamptz not null default now()
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

-- Zone de test : même structure (colonnes, valeurs par défaut, contraintes).
create table raw_test.raw_job_info       (like raw.raw_job_info       including all);
create table raw_test.log_raw_job_info   (like raw.log_raw_job_info   including all);
create table raw_test.raw_job_detail     (like raw.raw_job_detail     including all);
create table raw_test.log_raw_job_detail (like raw.log_raw_job_detail including all);
