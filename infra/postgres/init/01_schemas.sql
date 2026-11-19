-- 01_schemas.sql
--
-- Description : les schémas de la base JobCompass.
-- Règles      : raw      = données brutes, en ajout seul (jamais modifiées) ;
--               raw_test = mêmes tables, pour les passages de test (zone à part) ;
--               config   = tables de configuration, seules tables mises à jour.
-- Exécuté par Postgres au premier démarrage (volume vide) uniquement.

create schema if not exists raw;
create schema if not exists raw_test;
create schema if not exists config;
