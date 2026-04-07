-- Fail if any depositor is not a valid 42-char EVM address (0x + 40 hex).
-- Catches ABI decoding issues at the source boundary.

select *
from {{ ref('stg_cctp_burns') }}
where length(depositor) != 42
   or depositor not like '0x%'
