-- Reads the project-level Parquet directly via DuckDB's read_parquet().
-- Path is relative to the dbt_project/ working directory (one level up = project root).

with source as (
    select *
    from read_parquet('../data/transformed/cctp_transformed_raw_logs.parquet')
),

renamed as (
    select
        tx_hash,
        cast(block_number as bigint)                          as block_number,
        cast(log_index as integer)                            as log_index,
        cast(timestamp as timestamp)                          as burn_timestamp,
        cast(timestamp as date)                               as burn_date,
        extract(hour from cast(timestamp as timestamp))       as burn_hour,
        extract(dow  from cast(timestamp as timestamp))       as burn_dow,
        source_chain,
        dest_chain,
        lower(depositor)                                      as depositor,
        lower(recipient)                                      as recipient,
        lower(burn_token)                                     as burn_token,
        cast(amount as double)                                as amount_usdc
    from source
)

select * from renamed
