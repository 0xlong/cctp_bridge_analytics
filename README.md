# CCTP Bridge Analytics

End-to-end analytics pipeline for Circle's Cross-Chain Transfer Protocol (CCTP V2). Extracts, decodes, and models USDC bridge activity across 8 EVM chains to surface insights on token flows, user behavior, volume trends, and ecosystem health — entirely from open-source indexers, with no paid data providers.

## Architecture

```
┌──────────────┐    ┌───────────────┐    ┌────────────┐    ┌───────────────┐
│  Subsquid    │───>│  Python ETL   │───>│  dbt +     │───>│  Apache       │
│  (Indexer)   │    │  Extract &    │    │  DuckDB    │    │  Superset     │
│              │    │  Decode       │    │  (Modeling) │    │  (Dashboards) │
└──────────────┘    └───────────────┘    └────────────┘    └───────────────┘
    Raw Logs         Parquet Files        Analytical DB      Visualization
```

**Data Flow:** On-chain `DepositForBurn` events → raw log extraction → ABI decoding → dbt staging/modeling → materialized analytics tables → interactive dashboards.

## Chains Covered

| Chain | CCTP Domain ID | Indexer |
|-------|---------------|---------|
| Ethereum | 0 | Subsquid |
| Avalanche | 1 | Subsquid |
| Optimism | 2 | Subsquid |
| Arbitrum | 3 | Subsquid |
| Base | 6 | Subsquid |
| Polygon | 7 | Subsquid |
| Monad | 15 | Subsquid |
| HyperEVM | 19 | Subsquid |

The pipeline resolves all 31 CCTP V2 destination domains, including Solana, Linea, Sonic, Unichain, and others.

## Key Analytical Models

The dbt layer transforms raw burn events into analytical marts:

| Model | Purpose |
|-------|---------|
| `mart_daily_volume` | Time-series of daily USDC bridging volume and transfer counts by source chain |
| `mart_chain_flows` | Cross-chain flow matrix (source → dest) with volume share, log-scaled scores for graph rendering, and percentage of total volume |
| `mart_top_users` | Depositor segmentation — whale leaderboard ranked by total volume, unique routes, chain diversity, and activity window |
| `mart_hourly_heatmap` | Activity distribution by hour-of-day and day-of-week for temporal pattern analysis |
| `int_burn_flows` | Intermediate route-level daily aggregations with statistical summaries (mean, median, min, max) |

All models are tested with schema-level constraints (`not_null`, `unique`, `accepted_values`) defined in dbt YAML, plus singular data quality tests in `dbt_project/tests/`.

## Data Quality Tests

Two layers of testing:

**Schema tests** (defined in `models/**/schema.yml`) — column-level contracts enforced on every `dbt run`:
- `not_null` on all critical fields (tx_hash, timestamp, depositor, amounts, chains)
- `unique` on `tx_hash` and `depositor` (warn severity)
- `accepted_values` on `source_chain`

**Singular tests** (`tests/`) — custom SQL assertions for logic-level guarantees:

| Test | Layer | What it catches |
|------|-------|----------------|
| `assert_no_negative_volumes` | staging | Decoding errors / uint overflow |
| `assert_no_self_transfers` | staging | source_chain = dest_chain (domain mapping bug) |
| `assert_burn_timestamps_in_range` | staging | Block-range miscalibration in ETL |
| `assert_volume_reconciliation` | mart | Row loss or duplication during aggregation |
| `assert_valid_depositor_addresses` | staging | ABI decoding producing malformed EVM addresses |
| `assert_source_not_empty` | staging | Silent ETL failure producing empty Parquet |

```bash
# Run all tests
cd dbt_project && dbt test

# Singular tests only
dbt test --select test_type:singular

# Single test
dbt test --select assert_no_negative_volumes
```

## Technical Details

### ETL Pipeline (Python)

- **Extract** (`src/ETL/extract/extract_logs.py`): Queries the Subsquid streaming API for `DepositForBurn` events emitted by the `TokenMessengerV2` contract (`0x28b5a0e9c621a5badaa536219b3a228c8168cf5d`). Uses Moralis for date-to-block resolution with hardcoded overrides for chains outside Moralis coverage (HyperEVM). Handles Subsquid's chunked streaming pagination automatically.

- **Transform** (`src/ETL/transform/transform_logs.py`): Decodes ABI-encoded log payloads — extracts `burnToken`, `depositor`, and `minFinalityThreshold` from indexed topics; parses `amount`, `mintRecipient`, `destDomain`, and other fields from the unindexed data section. Handles `bytes32`-padded addresses (cross-chain compatible format) by detecting and stripping left-padding for EVM recipients.

- **Output format:** Parquet files for columnar efficiency and native DuckDB compatibility.

### Data Modeling (dbt + DuckDB)

- dbt-duckdb adapter reads Parquet directly via `read_parquet()` — no database load step needed.
- Three-layer model structure: `staging` → `intermediate` → `marts`.
- Window functions compute volume share percentages; log-scaled metrics support network graph visualization.
- Materialized as DuckDB tables for fast analytical queries from Superset.

### Visualization (Apache Superset)

- Dockerized Superset connects to the DuckDB analytical database.
- Supports Sankey diagrams (chain flows), time-series charts (daily volume), heatmaps (hourly activity), and table views (top users).
- Database is synced post-dbt-run via `docker cp`.

## Project Structure

```
circle_cctp_bridge_analytics/
├── src/
│   ├── config.py                  # Chain configs, contract addresses, CCTP domain mappings
│   └── ETL/
│       ├── extract/
│       │   └── extract_logs.py    # Subsquid raw log extraction
│       └── transform/
│           └── transform_logs.py  # ABI decoding & normalization
├── dbt_project/
│   ├── models/
│   │   ├── staging/
│   │   │   └── stg_cctp_burns.sql
│   │   ├── intermediate/
│   │   │   └── int_burn_flows.sql
│   │   └── marts/
│   │       ├── mart_daily_volume.sql
│   │       ├── mart_chain_flows.sql
│   │       ├── mart_top_users.sql
│   │       └── mart_hourly_heatmap.sql
│   ├── tests/
│   │   ├── assert_no_negative_volumes.sql
│   │   ├── assert_no_self_transfers.sql
│   │   ├── assert_burn_timestamps_in_range.sql
│   │   ├── assert_volume_reconciliation.sql
│   │   ├── assert_valid_depositor_addresses.sql
│   │   └── assert_source_not_empty.sql
│   ├── profiles.yml
│   └── dbt_project.yml
├── data/
│   ├── raw/                       # Extracted Parquet logs
│   ├── transformed/               # Decoded burn events
│   └── cctp_analytics.duckdb      # Analytical database
└── .env                           # API keys (not committed)
```

## Getting Started

### Prerequisites

- Python 3.11+
- dbt-core with dbt-duckdb adapter
- Docker (for Superset)
- Moralis API key (for block-by-date resolution)

### Setup

```bash
# Create and activate virtual environment
python -m venv cctp_bridge_analytics_env
source cctp_bridge_analytics_env/bin/activate  # or activate.bat on Windows

# Install dependencies
pip install requests pandas pyarrow python-dotenv dbt-duckdb

# Configure API key
echo "MORALIS_API_KEY=your_key_here" > .env
```

### Run the Pipeline

```bash
# 1. Extract raw logs from Subsquid
python src/ETL/extract/extract_logs.py

# 2. Decode and transform burn events
python src/ETL/transform/transform_logs.py

# 3. Build dbt models
cd dbt_project && dbt run

# 4. Sync to Superset (if running)
docker cp ../data/cctp_analytics.duckdb superset_app:/app/cctp_analytics.duckdb
```

### Configuration

Edit `src/config.py` to adjust:
- `START_DATE` / `END_DATE` — analysis time window
- `CHAINS` — which chains to index
- `OVERRIDE_BLOCKS` — manual block ranges for chains without Moralis support

## Analytical Questions This Pipeline Answers

- **Volume dynamics:** How much USDC flows through CCTP daily? Which chains dominate as sources vs. destinations?
- **Route analysis:** What are the highest-volume cross-chain corridors? How concentrated is flow across routes?
- **User segmentation:** Who are the top bridging wallets? How diversified are their routes? What characterizes whale vs. retail behavior?
- **Temporal patterns:** When does bridging activity peak? Are there day-of-week or hour-of-day patterns that correlate with market events?
- **Ecosystem health:** How evenly distributed is volume across chains? Is traffic growing or contracting on newer chains like Monad and HyperEVM?

## Roadmap

- [ ] **Match Phase:** Link source-chain `DepositForBurn` events to destination-chain `MessageReceived` events via nonce matching against the `MessageTransmitterV2` contract — enabling cross-chain latency measurement
- [ ] **Anomaly Detection:** Statistical models to flag unusual volume spikes, dormant whale reactivation, and atypical routing patterns
- [ ] **Interactive Network Graph:** Live visualization of token flows across chains, deployed via GitHub Pages
- [ ] **Expanded Chain Coverage:** Extend indexing to Solana, Linea, Sonic, and other CCTP V2 destinations

## License

This project is for analytical and research purposes.
