-- Fail if any burn has a negative USDC amount.
-- Guards against decoding errors or overflow in the ETL layer.

select *
from {{ ref('stg_cctp_burns') }}
where amount_usdc < 0
