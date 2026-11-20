-- ---------------------------------------------------------------------------
-- Model Name: int_skills__normalized_skills_unnested.sql
-- Description: skills of the normalized job detail pages, one row per page
--              extraction and canonical skill, current normalizer only.
-- Rules: only the normalizations of the current normalizer (name and version
--        in config.normalizer). Several models of that normalizer on the same
--        page: the latest normalization only.
-- ---------------------------------------------------------------------------

with

stg_normalization__normalized_jobs as (

    select
        hash_normalized_job_id,
        hash_job_detail_id,
        normalizer_name,
        normalizer_version,
        model_name,
        model_version,
        skills,
        normalized_at
    from {{ ref('stg_normalization__normalized_jobs') }}

),

stg_config__normalizers as (

    select
        normalizer_name,
        normalizer_version
    from {{ ref('stg_config__normalizers') }}
    where is_current

),

{# The normalizations of the current normalizer only #}
current_normalizations as (

    select
        stg_normalization__normalized_jobs.hash_normalized_job_id,
        stg_normalization__normalized_jobs.hash_job_detail_id,
        stg_normalization__normalized_jobs.normalizer_name,
        stg_normalization__normalized_jobs.normalizer_version,
        stg_normalization__normalized_jobs.model_name,
        stg_normalization__normalized_jobs.model_version,
        stg_normalization__normalized_jobs.skills,
        stg_normalization__normalized_jobs.normalized_at
    from stg_normalization__normalized_jobs
    inner join stg_config__normalizers
        on
            stg_normalization__normalized_jobs.normalizer_name
            = stg_config__normalizers.normalizer_name
            and stg_normalization__normalized_jobs.normalizer_version
            = stg_config__normalizers.normalizer_version

),

{# One normalization per page: the latest one #}
latest_normalizations as (

    select distinct on (hash_job_detail_id) *
    from current_normalizations
    order by hash_job_detail_id asc, normalized_at desc  -- noqa: AM06

),

skills_unnested as (

    select
        latest_normalizations.hash_normalized_job_id,
        latest_normalizations.hash_job_detail_id,
        latest_normalizations.normalizer_name,
        latest_normalizations.normalizer_version,
        latest_normalizations.model_name,
        latest_normalizations.model_version,
        skill_element.value ->> 'canonical' as canonical_skill,
        skill_element.value ->> 'raw' as raw_skill,
        skill_element.value ->> 'origin' as skill_origin
    from latest_normalizations
    cross join
        lateral jsonb_array_elements(latest_normalizations.skills)
            as skill_element

),

final as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(
            ['hash_normalized_job_id', 'canonical_skill']
        ) }} as hash_normalized_skill_id,
        hash_normalized_job_id,
        hash_job_detail_id,

        ---------- strings
        canonical_skill,
        raw_skill,
        skill_origin,
        normalizer_name,
        normalizer_version,
        model_name,
        model_version

    from skills_unnested

)

select * from final
