-- ---------------------------------------------------------------------------
-- Model Name: stg_jobup__job_details.sql
-- Description: jobup job detail pages, one row per page (job_url), latest
--              extraction only, JSON-LD keys read into columns.
-- Rules: no join. Latest extraction of a page: highest scraper_version,
--        compared number by number (0.10.0 after 0.9.0), then latest
--        fetched_at. Columns read from the JSON-LD are null for paragraphs
--        pages (the listing card is used downstream). job_description: the
--        JSON-LD description (HTML), or the paragraphs joined by line breaks.
-- ---------------------------------------------------------------------------

with

source as (

    select distinct on (url) *
    from {{ source('jobup', 'raw_job_detail') }}
    where source = 'jobup'
    {# The latest extraction of each page: distinct on needs named columns #}
    order by  -- noqa: AM06
        url asc,
        string_to_array(scraper_version, '.')::int[] desc,
        fetched_at desc

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(
            ['hash_html_id', 'scraper', 'scraper_version']
        ) }} as hash_job_detail_id,
        {{ dbt_utils.generate_surrogate_key(['source', 'url']) }}
            as hash_job_id,
        hash_html_id,

        ---------- strings
        url as job_url,
        source as site_name,
        scraper as scraper_name,
        scraper_version,
        schema_version,
        payload_format,
        payload ->> 'title' as job_title,
        payload -> 'hiringOrganization' ->> 'name' as company_name,
        case
            when payload_format = 'json_ld' then payload ->> 'description'
            else
                array_to_string(
                    array(select jsonb_array_elements_text(payload)), chr(10)
                )
        end as job_description,
        payload,

        ---------- booleans
        is_test,

        ---------- dates
        case
            when pg_input_is_valid(left(payload ->> 'datePosted', 10), 'date')
                then left(payload ->> 'datePosted', 10)::date
        end as posted_date,

        ---------- timestamps
        fetched_at

    from source

)

select * from renamed
