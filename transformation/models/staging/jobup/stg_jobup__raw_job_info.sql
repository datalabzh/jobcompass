-- Offres vues sur les pages de résultats de jobup : une ligne par offre et par passage
-- (la durée de vie d'une offre se déduit de ses passages). card = carte JSON brute.

select
    run_id,
    url,
    seen_at,
    listing_params['category'] as category,
    card::json as card,
    schema_version,
    is_test
from {{ source('jobup', 'raw_job_info') }}
