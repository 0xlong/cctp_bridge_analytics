-- Top depositors ranked by total USDC bridged
-- Whale leaderboard table for Superset

with burns as (
    select * from {{ ref('stg_cctp_burns') }}
)

select
    depositor,
    count(*)                                        as num_burns,
    round(sum(amount_usdc), 2)                      as total_volume_usdc,
    round(avg(amount_usdc), 2)                      as avg_transfer_usdc,
    max(amount_usdc)                                as largest_transfer_usdc,
    count(distinct source_chain)                    as source_chains_used,
    count(distinct dest_chain)                      as dest_chains_used,
    count(distinct source_chain || '->' || dest_chain) as unique_routes,
    min(burn_timestamp)                             as first_burn_at,
    max(burn_timestamp)                             as last_burn_at,

    -- rank by volume
    row_number() over (order by sum(amount_usdc) desc) as volume_rank

from burns
group by depositor
order by total_volume_usdc desc
