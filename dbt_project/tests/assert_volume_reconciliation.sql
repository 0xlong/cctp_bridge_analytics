-- Fail if mart_daily_volume total diverges from staging total.
-- Ensures no rows are silently dropped or duplicated during aggregation.

with staging_total as (
    select round(sum(amount_usdc), 2) as total
    from {{ ref('stg_cctp_burns') }}
),

mart_total as (
    select round(sum(daily_volume_usdc), 2) as total
    from {{ ref('mart_daily_volume') }}
)

select *
from staging_total
cross join mart_total
where abs(staging_total.total - mart_total.total) > 0.01
