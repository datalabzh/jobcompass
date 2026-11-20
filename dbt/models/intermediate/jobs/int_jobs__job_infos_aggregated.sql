-- ---------------------------------------------------------------------------
-- Model Name: int_jobs__job_infos_aggregated.sql
-- Description: jobup job offers seen on result pages, one row per offer, with
--              its presence and its latest listing card.
-- Rules: first_seen_at / last_seen_at = first and last sighting.
--        is_active = seen in the latest completed run of at least one
--        category: a failed run never makes offers disappear.
--        Card values (title, company, place, dates) from the latest sighting.
-- ---------------------------------------------------------------------------

with

stg_jobup__job_infos as (

    select
        hash_job_id,
        run_id,
        job_url,
        site_name,
        job_title,
        company_name,
        job_place,
        initial_published_at,
        published_at,
        seen_at
    from {{ ref('stg_jobup__job_infos') }}

),

stg_jobup__job_info_runs as (

    select
        run_id,
        job_category,
        started_at
    from {{ ref('stg_jobup__job_info_runs') }}
    where run_status = 'completed'

),

{# The latest completed run of each category #}
latest_completed_runs as (

    select distinct on (job_category) run_id
    from stg_jobup__job_info_runs
    order by job_category asc, started_at desc  -- noqa: AM06

),

{# Offers seen in a latest completed run are still published #}
active_offers as (

    select distinct stg_jobup__job_infos.hash_job_id
    from stg_jobup__job_infos
    inner join latest_completed_runs
        on stg_jobup__job_infos.run_id = latest_completed_runs.run_id

),

{# The latest sighting of each offer: its most recent listing card #}
latest_sightings as (

    select distinct on (hash_job_id)
        hash_job_id,
        job_url,
        site_name,
        job_title,
        company_name,
        job_place,
        initial_published_at,
        published_at
    from stg_jobup__job_infos
    order by hash_job_id asc, seen_at desc  -- noqa: AM06

),

sightings_aggregated_to_offers as (

    select
        hash_job_id,
        count(distinct run_id) as runs_seen,
        min(seen_at) as first_seen_at,
        max(seen_at) as last_seen_at
    from stg_jobup__job_infos
    group by 1

),

final as (

    select

        ---------- ids
        latest_sightings.hash_job_id,

        ---------- strings
        latest_sightings.job_url,
        latest_sightings.site_name,
        latest_sightings.job_title,
        latest_sightings.company_name,
        latest_sightings.job_place,

        ---------- numerics
        sightings_aggregated_to_offers.runs_seen,

        ---------- booleans
        active_offers.hash_job_id is not null as is_active,

        ---------- timestamps
        latest_sightings.initial_published_at,
        latest_sightings.published_at,
        sightings_aggregated_to_offers.first_seen_at,
        sightings_aggregated_to_offers.last_seen_at

    from latest_sightings
    inner join sightings_aggregated_to_offers
        on
            latest_sightings.hash_job_id
            = sightings_aggregated_to_offers.hash_job_id
    left join active_offers
        on latest_sightings.hash_job_id = active_offers.hash_job_id

)

select * from final
