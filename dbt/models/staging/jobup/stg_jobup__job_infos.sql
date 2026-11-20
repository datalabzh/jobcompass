-- ---------------------------------------------------------------------------
-- Model Name: stg_jobup__job_infos.sql
-- Description: jobs seen on jobup result pages, one row per job and per run.
-- Rules: no join. Every run kept: the lifetime of a job offer is read from
--        its runs. listing_card = raw JSON card of the result page.
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('jobup', 'raw_job_info') }}

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(['run_id', 'url']) }}
            as job_info_id,
        run_id,

        ---------- strings
        url as job_url,
        source as site_name,
        schema_version,
        listing_params['category'] as job_category,
        card as listing_card,

        ---------- booleans
        is_test,

        ---------- timestamps
        seen_at

    from source

)

select * from renamed
