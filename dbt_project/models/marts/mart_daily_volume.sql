-- Daily total volume and transfer count, broken down by source chain
-- Primary time-series table for Superset line/area charts

with flows as (
    select * from {{ ref('int_burn_flows') }}
)

select
    burn_date,
    source_chain,
    sum(total_volume_usdc)              as daily_volume_usdc,
    sum(num_transfers)                  as daily_transfers,
    sum(unique_depositors)              as daily_unique_depositors,
    avg(avg_transfer_usdc)              as avg_transfer_usdc

from flows
group by burn_date, source_chain
order by burn_date, daily_volume_usdc desc
