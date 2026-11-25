-- ---------------------------------------------------------------------------
-- Model Name: int_jobs__job_infos_unioned.sql
-- Description: jobs seen on the result pages of every site, one row per job
--              and per run.
-- Rules: one CTE per site, reading its staging, same columns in the same
--        order; the sites are put together with union all. Adding a site =
--        one CTE and one union all here (and in the two other unioned
--        models), plus its row in config.site.
-- ---------------------------------------------------------------------------

with

stg_jobup__job_infos as (

    select
        hash_job_info_id,
        hash_job_id,
        run_id,
        job_url,
        site_name,
        job_category,
        job_title,
        company_name,
        job_place,
        initial_published_at,
        published_at,
        seen_at
    from {{ ref('stg_jobup__job_infos') }}

),

unioned as (

    select * from stg_jobup__job_infos

)

select * from unioned
