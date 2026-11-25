-- ---------------------------------------------------------------------------
-- Model Name: int_jobs__job_details_unioned.sql
-- Description: job detail pages of every site, one row per page, latest
--              extraction only.
-- Rules: one CTE per site, reading its staging, same columns in the same
--        order; the sites are put together with union all. Each staging
--        already keeps the latest extraction of its pages.
-- ---------------------------------------------------------------------------

with

stg_jobup__job_details as (

    select
        hash_job_detail_id,
        hash_job_id,
        hash_html_id,
        job_url,
        site_name,
        payload_format,
        job_title,
        company_name,
        job_description,
        posted_date,
        fetched_at
    from {{ ref('stg_jobup__job_details') }}

),

unioned as (

    select * from stg_jobup__job_details

)

select * from unioned
