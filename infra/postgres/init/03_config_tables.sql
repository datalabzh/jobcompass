-- 03_config_tables.sql
--
-- Description : les tables de configuration, modifiables (mise à jour, pas ajout).
-- Règles      : config.normalizer = les normaliseurs connus ; un seul est courant
--               (is_current), garanti par un index unique partiel. dbt ne retient
--               que les lignes de normalized_job produites par le normaliseur
--               courant. Changer de courant = une transaction qui retire l'ancien
--               puis désigne le nouveau.
--               Au démarrage, le normaliseur courant est fake_normalization : il se
--               comporte comme un vrai normaliseur, en attendant celui de l'équipe
--               NLP. Sa version suit normalizer_version de FakeNormalizationUseCase.

create table config.normalizer (
    normalizer          text        not null,
    normalizer_version  text        not null,
    description         text,
    is_current          boolean     not null default false,
    updated_at          timestamptz not null default now(),
    primary key (normalizer, normalizer_version)
);

-- Au plus un normaliseur courant.
create unique index normalizer_one_current
    on config.normalizer (is_current)
    where is_current;

-- Normaliseur courant au démarrage.
insert into config.normalizer (normalizer, normalizer_version, description, is_current)
values (
    'fake_normalization',
    '0.2.0',
    'Fake skills to test the pipeline: the skills declared by the source, plus'
    ' about thirty fixed technology keywords found in the title and description.',
    true
);
