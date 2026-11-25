-- ---------------------------------------------------------------------------
-- Model Name: jobs__job_offers.sql
-- Description: job offers of every site, one row per offer, with its presence
--              and its latest detail page.
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

int_jobs__job_details_unioned as (

    select
        hash_job_id,
        hash_job_detail_id,
        hash_html_id,
        payload_format,
        job_title,
        company_name,
        job_description,
        posted_date,
        fetched_at
    from {{ ref('int_jobs__job_details_unioned') }}

),

offers_joined_to_details as (

    select
        int_jobs__job_infos_aggregated.hash_job_id,
        int_jobs__job_details_unioned.hash_job_detail_id,
        int_jobs__job_details_unioned.hash_html_id,
        int_jobs__job_infos_aggregated.job_url,
        int_jobs__job_infos_aggregated.site_name,
        coalesce(
            int_jobs__job_details_unioned.job_title,
            int_jobs__job_infos_aggregated.job_title
        ) as job_title,
        coalesce(
            int_jobs__job_details_unioned.company_name,
            int_jobs__job_infos_aggregated.company_name
        ) as company_name,
        int_jobs__job_infos_aggregated.job_place,
        int_jobs__job_details_unioned.payload_format,
        int_jobs__job_details_unioned.job_description,
        int_jobs__job_infos_aggregated.runs_seen,
        int_jobs__job_infos_aggregated.is_active,
        coalesce(
            int_jobs__job_details_unioned.posted_date,
            int_jobs__job_infos_aggregated.initial_published_at::date
        ) as posted_date,
        int_jobs__job_infos_aggregated.first_seen_at,
        int_jobs__job_infos_aggregated.last_seen_at,
        int_jobs__job_details_unioned.fetched_at
    from int_jobs__job_infos_aggregated
    left join int_jobs__job_details_unioned
        on
            int_jobs__job_infos_aggregated.hash_job_id
            = int_jobs__job_details_unioned.hash_job_id

),

final as (

    select

        ---------- ids
        hash_job_id,
        hash_job_detail_id,
        hash_html_id,

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
