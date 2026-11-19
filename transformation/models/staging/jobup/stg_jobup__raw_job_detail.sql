-- Fiches de jobup : une ligne par page téléchargée (url, raw_hash), extraction la
-- plus récente. Le JSON-LD (json_ld) est lu en colonnes ; à défaut (paragraphs), seuls
-- les paragraphes sont disponibles et les colonnes lues du JSON-LD sont nulles.
-- description = HTML de la source (json_ld) ou paragraphes joints (paragraphs).

with latest as (
    select *
    from {{ source('jobup', 'raw_job_detail') }}
    qualify row_number() over (
        partition by url, raw_hash order by fetched_at desc, scraper_version desc
    ) = 1
)

select
    raw_hash,
    url,
    fetched_at,
    scraper,
    scraper_version,
    payload_format,
    payload::json as payload,
    case when payload_format = 'json_ld' then payload ->> '$.title' end as title,
    case
        when payload_format = 'json_ld' then payload ->> '$.hiringOrganization.name'
    end as company,
    case
        when payload_format = 'json_ld' then payload ->> '$.description'
        else array_to_string(cast(payload::json as varchar[]), chr(10))
    end as description,
    case
        when payload_format = 'json_ld'
            then try_cast(left(payload ->> '$.datePosted', 10) as date)
    end as date_posted,
    schema_version,
    is_test
from latest
