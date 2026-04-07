-- Fail if any burn routes back to the same chain.
-- CCTP is cross-chain only; a self-transfer indicates a decode or mapping bug.

select *
from {{ ref('stg_cctp_burns') }}
where source_chain = dest_chain
