-- ---------------------------------------------------------------------------
-- Model Name: stg_config__normalizers.sql
-- Description: known normalizers, one row per normalizer and version.
-- Rules: no join. Exactly one row is current (is_current), guaranteed by a
--        unique index in Postgres.
-- ---------------------------------------------------------------------------

with

source as (

    select * from {{ source('config', 'normalizer') }}

),

renamed as (

    select

        ---------- ids
        {{ dbt_utils.generate_surrogate_key(
            ['normalizer', 'normalizer_version']
        ) }} as hash_normalizer_id,

        ---------- strings
        normalizer as normalizer_name,
        normalizer_version,
        description as normalizer_description,

        ---------- booleans
        is_current,

        ---------- timestamps
        updated_at

    from source

)

select * from renamed
