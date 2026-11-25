-- ---------------------------------------------------------------------------
-- Model Name: int_jobs__job_info_runs_unioned.sql
-- Description: extraction runs of the result pages of every site, one row
--              per run of a category.
-- Rules: one CTE per site, reading its staging, same columns in the same
--        order; the sites are put together with union all. Failed runs are
--        kept: downstream models choose the completed ones.
-- ---------------------------------------------------------------------------

with

stg_jobup__job_info_runs as (

    select
        run_id,
        site_name,
        job_category,
        run_status,
        started_at,
        finished_at
    from {{ ref('stg_jobup__job_info_runs') }}

),

unioned as (

    select * from stg_jobup__job_info_runs

)

select * from unioned
