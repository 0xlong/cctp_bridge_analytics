-- Hourly activity heatmap data: transfers and volume per hour-of-day × day-of-week
-- Used for hourly heatmap charts in Superset

with burns as (
    select * from {{ ref('stg_cctp_burns') }}
)

select
    burn_hour,
    burn_dow,
    case burn_dow
        when 0 then 'Sun'
        when 1 then 'Mon'
        when 2 then 'Tue'
        when 3 then 'Wed'
        when 4 then 'Thu'
        when 5 then 'Fri'
        when 6 then 'Sat'
    end                                             as day_name,
    count(*)                                        as num_transfers,
    round(sum(amount_usdc), 2)                      as total_volume_usdc,
    round(avg(amount_usdc), 2)                      as avg_transfer_usdc

from burns
group by burn_hour, burn_dow
order by burn_dow, burn_hour
