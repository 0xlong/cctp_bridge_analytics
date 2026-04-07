-- Fail if any burn falls outside the expected extraction window.
-- Catches block-range miscalibration in the ETL step.

select *
from {{ ref('stg_cctp_burns') }}
where burn_date < '2026-03-21'
   or burn_date > '2026-03-31'
