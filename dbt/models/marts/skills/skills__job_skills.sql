-- ---------------------------------------------------------------------------
-- Model Name: skills__job_skills.sql
-- Description: skills of the jobup job offers, one row per offer and
--              canonical skill, with the days the offer was seen.
-- Rules: skills of the latest detail page of each offer, normalized by the
--        current normalizer. No aggregation: counts by day, week or month
--        are computed from this model.
-- ---------------------------------------------------------------------------

with

int_skills__normalized_skills_unnested as (

    select
        hash_job_detail_id,
        canonical_skill,
        raw_skill,
        skill_origin,
        normalizer_name,
        normalizer_version,
        model_name,
        model_version
    from {{ ref('int_skills__normalized_skills_unnested') }}

),

stg_jobup__job_details as (

    select
        hash_job_detail_id,
        hash_job_id
    from {{ ref('stg_jobup__job_details') }}

),

int_jobs__job_infos_aggregated as (

    select
        hash_job_id,
        job_url,
        is_active,
        first_seen_at,
        last_seen_at
    from {{ ref('int_jobs__job_infos_aggregated') }}

),

skills_joined_to_offers as (

    select
        stg_jobup__job_details.hash_job_id,
        int_jobs__job_infos_aggregated.job_url,
        int_skills__normalized_skills_unnested.canonical_skill,
        int_skills__normalized_skills_unnested.raw_skill,
        int_skills__normalized_skills_unnested.skill_origin,
        int_skills__normalized_skills_unnested.normalizer_name,
        int_skills__normalized_skills_unnested.normalizer_version,
        int_skills__normalized_skills_unnested.model_name,
        int_skills__normalized_skills_unnested.model_version,
        int_jobs__job_infos_aggregated.is_active,
        int_jobs__job_infos_aggregated.first_seen_at,
        int_jobs__job_infos_aggregated.last_seen_at
    from int_skills__normalized_skills_unnested
    inner join stg_jobup__job_details
        on
            int_skills__normalized_skills_unnested.hash_job_detail_id
            = stg_jobup__job_details.hash_job_detail_id
    inner join int_jobs__job_infos_aggregated
        on
            stg_jobup__job_details.hash_job_id
            = int_jobs__job_infos_aggregated.hash_job_id

),

final as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(
            ['hash_job_id', 'canonical_skill']
        ) }} as hash_job_skill_id,
        hash_job_id,

        ---------- strings
        job_url,
        canonical_skill,
        raw_skill,
        skill_origin,
        normalizer_name,
        normalizer_version,
        model_name,
        model_version,

        ---------- booleans
        is_active,

        ---------- dates
        first_seen_at::date as first_seen_date,
        last_seen_at::date as last_seen_date

    from skills_joined_to_offers

)

select * from final
