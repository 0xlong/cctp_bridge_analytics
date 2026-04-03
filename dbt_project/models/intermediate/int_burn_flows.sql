-- Aggregate burn events by route (source → destination) and date
-- Used as the backbone for flow and volume marts

with burns as (
    select * from {{ ref('stg_cctp_burns') }}
)

select
    burn_date,
    source_chain,
    dest_chain,

    -- volume
    count(*)                            as num_transfers,
    sum(amount_usdc)                    as total_volume_usdc,
    avg(amount_usdc)                    as avg_transfer_usdc,
    median(amount_usdc)                 as median_transfer_usdc,
    min(amount_usdc)                    as min_transfer_usdc,
    max(amount_usdc)                    as max_transfer_usdc,

    -- users
    count(distinct depositor)           as unique_depositors,
    count(distinct recipient)           as unique_recipients

from burns
group by burn_date, source_chain, dest_chain
order by burn_date, total_volume_usdc desc
