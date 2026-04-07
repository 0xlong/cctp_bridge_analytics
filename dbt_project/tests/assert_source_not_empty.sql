-- Fail if staging table has zero rows.
-- Guards against silent ETL failures producing empty Parquet files.

select 1
from {{ ref('stg_cctp_burns') }}
having count(*) = 0
