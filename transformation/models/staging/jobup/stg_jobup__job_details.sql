-- ---------------------------------------------------------------------------
-- Model Name: stg_jobup__job_details.sql
-- Description: jobup job detail pages, one row per page (url, raw_hash),
--              raw data block read into columns.
-- Rules: no join. Latest extraction of a page only.
--        Columns read from the JSON-LD are null for paragraphs pages.
--        job_description: JSON-LD description (HTML) or paragraphs joined.
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('jobup', 'raw_job_detail') }}

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(['url', 'raw_hash']) }}
            as job_detail_id,

        ---------- strings
        raw_hash,
        url as job_url,
        source as site_name,
        scraper as scraper_name,
        scraper_version,
        schema_version,
        payload_format,
        payload,
        payload ->> '$.title' as job_title,
        payload ->> '$.hiringOrganization.name' as company_name,
        case
            when payload_format = 'json_ld' then payload ->> '$.description'
            else array_to_string(cast(payload::json as varchar[]), chr(10))
        end as job_description,

        ---------- booleans
        is_test,

        ---------- dates
        try_cast(left(payload ->> '$.datePosted', 10) as date) as posted_date,

        ---------- timestamps
        fetched_at

    from source
    {# A page re-extracted later: the latest extraction only #}
    qualify row_number() over (
        partition by url, raw_hash
        order by fetched_at desc, scraper_version desc
    ) = 1

)

select * from renamed
