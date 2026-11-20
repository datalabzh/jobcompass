-- ---------------------------------------------------------------------------
-- Model Name: stg_jobup__job_info_runs.sql
-- Description: extraction runs of the jobup result pages, one row per run of
--              a category.
-- Rules: no join. Failed runs kept: downstream models choose the completed
--        ones.
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('jobup', 'log_raw_job_info') }}
    where source = 'jobup'

),

renamed as (

    select

        ---------- ids
        run_id,

        ---------- strings
        source as site_name,
        schema_version,
        listing_params ->> 'category' as job_category,
        status as run_status,
        error as run_error,

        ---------- numerics
        announced_total,
        pages_read,
        jobs_seen,
        distinct_urls,

        ---------- booleans
        is_test,

        ---------- timestamps
        started_at,
        finished_at

    from source

)

select * from renamed
