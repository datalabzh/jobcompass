-- 01_schemas.sql
--
-- Description : les schémas de la base JobCompass.
-- Règles      : raw    = données brutes, en ajout seul (jamais modifiées) ;
--               config = tables de configuration, seules tables mises à jour.
--               Les schémas de dbt (staging, intermediate, marts) sont créés
--               par dbt.
--               Appliqué aux deux bases (vraies données et _dev) par
--               00_init_databases.sh, au premier démarrage uniquement.

create schema if not exists raw;
create schema if not exists config;
