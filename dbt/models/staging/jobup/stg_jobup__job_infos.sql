-- ---------------------------------------------------------------------------
-- Model Name: stg_jobup__job_infos.sql
-- Description: jobs seen on jobup result pages, one row per job and per run,
--              listing card read into columns.
-- Rules: no join. Every run kept: the lifetime of a job offer is read from
--        its runs. Card values are null when the key is missing; dates that
--        cannot be read are null.
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('jobup', 'raw_job_info') }}
    where source = 'jobup'

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(['run_id', 'source', 'url']) }}
            as hash_job_info_id,
        {{ dbt_utils.generate_surrogate_key(['source', 'url']) }}
            as hash_job_id,
        run_id,

        ---------- strings
        url as job_url,
        source as site_name,
        schema_version,
        listing_params ->> 'category' as job_category,
        card ->> 'title' as job_title,
        card -> 'company' ->> 'name' as company_name,
        card ->> 'place' as job_place,
        card as listing_card,

        ---------- booleans
        is_test,

        ---------- timestamps
        case
            when
                pg_input_is_valid(
                    card ->> 'initialPublicationDate', 'timestamptz'
                )
                then (card ->> 'initialPublicationDate')::timestamptz
        end as initial_published_at,
        case
            when pg_input_is_valid(card ->> 'publicationDate', 'timestamptz')
                then (card ->> 'publicationDate')::timestamptz
        end as published_at,
        seen_at

    from source

)

select * from renamed
