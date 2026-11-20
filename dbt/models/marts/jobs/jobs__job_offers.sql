-- ---------------------------------------------------------------------------
-- Model Name: jobs__job_offers.sql
-- Description: jobup job offers, one row per offer, with its presence and its
--              latest detail page.
-- Rules: title, company and posted date from the JSON-LD of the detail page
--        when there is one, else from the latest listing card.
--        Offers never downloaded kept (left join), has_detail = false.
-- ---------------------------------------------------------------------------

with

int_jobs__job_infos_aggregated as (

    select
        hash_job_id,
        job_url,
        site_name,
        job_title,
        company_name,
        job_place,
        runs_seen,
        is_active,
        initial_published_at,
        first_seen_at,
        last_seen_at
    from {{ ref('int_jobs__job_infos_aggregated') }}

),

stg_jobup__job_details as (

    select
        hash_job_id,
        hash_job_detail_id,
        payload_format,
        job_title,
        company_name,
        job_description,
        posted_date,
        fetched_at
    from {{ ref('stg_jobup__job_details') }}

),

offers_joined_to_details as (

    select
        int_jobs__job_infos_aggregated.hash_job_id,
        stg_jobup__job_details.hash_job_detail_id,
        int_jobs__job_infos_aggregated.job_url,
        int_jobs__job_infos_aggregated.site_name,
        coalesce(
            stg_jobup__job_details.job_title,
            int_jobs__job_infos_aggregated.job_title
        ) as job_title,
        coalesce(
            stg_jobup__job_details.company_name,
            int_jobs__job_infos_aggregated.company_name
        ) as company_name,
        int_jobs__job_infos_aggregated.job_place,
        stg_jobup__job_details.payload_format,
        stg_jobup__job_details.job_description,
        int_jobs__job_infos_aggregated.runs_seen,
        int_jobs__job_infos_aggregated.is_active,
        coalesce(
            stg_jobup__job_details.posted_date,
            int_jobs__job_infos_aggregated.initial_published_at::date
        ) as posted_date,
        int_jobs__job_infos_aggregated.first_seen_at,
        int_jobs__job_infos_aggregated.last_seen_at,
        stg_jobup__job_details.fetched_at
    from int_jobs__job_infos_aggregated
    left join stg_jobup__job_details
        on
            int_jobs__job_infos_aggregated.hash_job_id
            = stg_jobup__job_details.hash_job_id

),

final as (

    select

        ---------- ids
        hash_job_id,
        hash_job_detail_id,

        ---------- strings
        job_url,
        site_name,
        job_title,
        company_name,
        job_place,
        payload_format,
        job_description,

        ---------- numerics
        runs_seen,

        ---------- booleans
        is_active,
        hash_job_detail_id is not null as has_detail,

        ---------- dates
        posted_date,

        ---------- timestamps
        first_seen_at,
        last_seen_at,
        fetched_at

    from offers_joined_to_details

)

select * from final
