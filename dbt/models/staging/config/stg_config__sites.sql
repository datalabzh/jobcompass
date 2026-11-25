-- ---------------------------------------------------------------------------
-- Model Name: stg_config__sites.sql
-- Description: sites known to JobCompass, one row per site.
-- Rules: no join. The register of the sites: every site_name found in the
--        data must be here (relationships tests of the unioned models).
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('config', 'site') }}

),

renamed as (

    select

        ---------- strings
        site_name,
        description as site_description,

        ---------- timestamps
        updated_at

    from source

)

select * from renamed
