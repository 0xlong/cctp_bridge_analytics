-- Hourly activity heatmap data: transfers and volume per hour-of-day × day-of-week
-- Used for hourly heatmap charts in Superset

with burns as (
    select * from {{ ref('stg_cctp_burns') }}
)

select
    burn_hour,
    burn_dow,
    case burn_dow
        when 0 then '7_Sunday'
        when 1 then '1_Monday'
        when 2 then '2_Tuesday'
        when 3 then '3_Wednesday'
        when 4 then '4_Thursday'
        when 5 then '5_Friday'
        when 6 then '6_Saturday'
    end                                             as day_name,
    count(*)                                        as num_transfers,
    round(sum(amount_usdc), 2)                      as total_volume_usdc,
    round(avg(amount_usdc), 2)                      as avg_transfer_usdc

from burns
group by burn_hour, burn_dow
order by burn_dow, burn_hour
