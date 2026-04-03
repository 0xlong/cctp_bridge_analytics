# ── CCTP V2 Bridge Analytics Configuration ──

# ── Time range (UTC) ──
START_DATE = "2026-03-21"
END_DATE   = "2026-03-31"

# ── Subsquid ──
SQD_BASE_URL = "https://portal.sqd.dev/datasets"

# ── Hardcoded block ranges for chains not supported by Moralis ──
OVERRIDE_BLOCKS = {
    "HyperEVM": (28538392, 31258697),
}

# ── Chains: name → (sqd_dataset, cctp_domain_id) ──
CHAINS = {
    "Ethereum":  ("ethereum-mainnet",  0),
    "Avalanche": ("avalanche-mainnet", 1),
    "Optimism":  ("optimism-mainnet",  2),
    "Arbitrum":  ("arbitrum-one",      3),
    "Base":      ("base-mainnet",      6),
    "Polygon":   ("polygon-mainnet",   7),
    "HyperEVM":  ("hyperliquid-mainnet", 19), #not present on Moralis API, have to hardcode block numbers
    "Monad":     ("monad-mainnet",     15),
}

# ── CCTP V2 contracts ──
TOKEN_MESSENGER_V2 = "0x28b5a0e9c621a5badaa536219b3a228c8168cf5d"

# ── USDC addresses per chain (native USDC only, not bridged variants) ──
USDC_ADDRESSES = {
    "Ethereum": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "Avalanche": "0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e",
    "Optimism":  "0x0b2c639c533813f4aa9d7837caf62653d097ff85",
    "Arbitrum":  "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
    "Base":      "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "Polygon":   "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",
}

# ── Event signatures ──
DEPOSIT_FOR_BURN_TOPIC = "0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5"

# ── All CCTP V2 domain IDs (verified April 2026) ──
DOMAIN_NAMES = {
    0:  "Ethereum",
    1:  "Avalanche",
    2:  "Optimism",
    3:  "Arbitrum",
    5:  "Solana",
    6:  "Base",
    7:  "Polygon",
    10: "Unichain",
    11: "Linea",
    12: "Codex",
    13: "Sonic",
    14: "World Chain",
    15: "Monad",
    16: "Sei",
    18: "XDC",
    19: "HyperEVM",
    21: "Ink",
    22: "Plume",
    25: "Starknet",
    28: "EDGE",
    30: "Morph",
}

# ── Output ──
RAW_OUTPUT_FILE = "data/raw/cctp_raw_logs.parquet"
TRANSFORMED_OUTPUT_FILE = "data/transformed/cctp_transformed_raw_logs.parquet"
