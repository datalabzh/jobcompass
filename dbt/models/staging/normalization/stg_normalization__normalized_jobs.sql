-- ---------------------------------------------------------------------------
-- Model Name: stg_normalization__normalized_jobs.sql
-- Description: normalizations of job detail pages, one row per normalization
--              (page extraction, normalizer, model and their versions).
-- Rules: no join. Every normalizer kept: the current one is chosen
--        downstream. hash_job_detail_id is computed from the copied key, as
--        in the staging of the detail pages, to join them.
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('normalization', 'normalized_job') }}

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key([
            'hash_html_id', 'scraper', 'scraper_version',
            'normalizer', 'normalizer_version', 'model', 'model_version'
        ]) }} as hash_normalized_job_id,
        {{ dbt_utils.generate_surrogate_key(
            ['hash_html_id', 'scraper', 'scraper_version']
        ) }} as hash_job_detail_id,
        hash_html_id,

        ---------- strings
        source as site_name,
        scraper as scraper_name,
        scraper_version,
        normalizer as normalizer_name,
        normalizer_version,
        model as model_name,
        model_version,
        normalizer_description,
        schema_version,
        skills,

        ---------- booleans
        is_test,

        ---------- timestamps
        normalized_at

    from source

)

select * from renamed
