Be terse. No conversational filler. Use surgical edits only. Do not rewrite whole files unless requested.

# Project State Summary: Circle CCTP Bridge Analytics
## 📁 Repository Overview
We are building a data analysis pipeline to extract, decode, match, and analyze Circle CCTP (Cross-Chain Transfer Protocol) bridge data across multiple EVM chains without using paid services (like Dune). The project uses open-source indexers (Subsquid) to fetch log data.
**Active Workspace:** `circle_cctp_bridge_analytics`
**Environment:** Python (with a local `cctp_bridge_analytics_env` virtual environment)
## 🛠️ Current Implementation State
According to the pipeline defined in `project_stepbystep_guideliens.txt`, we are progressing through 4 stages:
1. **Step 1: FETCH** (✅ Mostly Complete)
2. **Step 2: DECODE** (✅ Mostly Complete)
3. **Step 3: MATCH** (🚧 Pending)
4. **Step 4: ANALYZE** (🚧 Pending)
### Existing Codebase
- `extract_logs_from_EVMchain_sqd.py`: The core extraction script. It queries the Subsquid API to fetch `DepositForBurn` logs from the `TokenMessengerV2` contract across various networks (Ethereum, Avalanche, Optimism, Arbitrum, Base, Polygon, HyperEVM, Monad). It includes a 2-step automatic timestamp-to-block calibration mechanism and fully decodes the ABI chunk payloads payload into readable data.
- `config.py`: Contains configurations for the time range (e.g., `2026-03-05` to `2026-03-06`), chain mappings (Subsquid dataset name, CCTP domain IDs, avg block time for calibration), contract addresses, and event topics.
- `block_by_date.py`: A helper script that uses the Moralis API (via `.env` key) to fetch block numbers for specific dates on various chains.
- **Data output files**: The extractor is already functional and has generated CSV datasets: `cctp_extracted_logs.csv` (~427KB) and `cctp_burns.csv`.
## 🎯 Next Steps / Pending Work
As outlined in our project guidelines, we need to implement the following:
- **Match Phase (Step 3)**: Currently, we've extracted the "Burn" (source) side of CCTP transactions. We need to implement logic to monitor the destination chain for a `MessageReceived` event from the `MessageTransmitter` contract, matching it to our burn records using `nonce` and `sourceDomain`.
- **Analyze Phase (Step 4)**: Build analytics and metrics on top of the matched dataset (metrics like volume, latency, top users/routes).
- **Interactive Graph (Ultimate Goal)**: Build an interactive live graph of token flows across chains, similar to a previous project (using GitHub Pages to host).
## 🔑 Key Technical Details
- CCTP routing uses specific internal domain IDs (e.g., Ethereum is `0`, Arbitrum is `3`, Base is `6`), which are mapped in `config.py`.
- Addresses emitted within CCTP payloads are stored in `bytes32` (left-padded with zeros) to maintain cross-chain compatibility. Our extractor successfully decodes these back to standard EVM 20-byte addresses.
- **Contract Architecture**: Uses `TokenMessengerV2` (`0x28b5a...cf5d`) for burns (source) and mints (destination), and `MessageTransmitterV2` (`0x81D4...B64`) across EVM chains to relay messages.
- **The Matching Mechanism**: Matching cross-chain events involves linking:
  - Source Chain: `DepositForBurn` (Main burn event) & `MessageSent`.
  - Dest Chain: `MessageReceived` and `MintAndWithdraw`.
  - The `nonce` in the `MessageReceived` event is actually a `keccak256` hash of the cross-chain message, not a simple auto-incrementing integer.
- **🚨 Known Issues / Blockers 🚨**: The current `block_by_date.py` script is returning `Error 401` from the Moralis API (`https://deep-index.moralis.io/api/v2.2/dateToBlock`). The `MORALIS_API_KEY` in the `.env` file appears to be invalid or expired, so timestamp-to-block resolution via this API currently fails. (Note: The main `extract_logs_from_EVMchain_sqd.py` script bypasses this issue entirely by using an automatic 2-step block calibration via Subsquid!)