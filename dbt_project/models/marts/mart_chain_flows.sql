-- Cross-chain flow matrix: every source→destination pair with total volume
-- Used for Sankey diagrams and flow heatmaps in Superset

with flows as (
    select * from {{ ref('int_burn_flows') }}
)

select
    source_chain,
    dest_chain,
    sum(total_volume_usdc)                              as total_volume_usdc,
    sum(num_transfers)                                  as total_transfers,
    round(avg(avg_transfer_usdc), 2)                    as avg_transfer_usdc,
    round(avg(median_transfer_usdc), 2)                 as median_transfer_usdc,
    sum(unique_depositors)                              as total_unique_depositors,

    -- percentage of grand total (window function)
    round(
        sum(total_volume_usdc) * 100.0
        / sum(sum(total_volume_usdc)) over (),
    2)                                                  as pct_of_total_volume

from flows
group by source_chain, dest_chain
order by total_volume_usdc desc
