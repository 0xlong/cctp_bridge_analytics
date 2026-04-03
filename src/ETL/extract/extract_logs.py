import os
import sys
import requests
import json
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root (3 levels up from this file) and add src/ to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    SQD_BASE_URL, CHAINS, TOKEN_MESSENGER_V2,
    DEPOSIT_FOR_BURN_TOPIC, RAW_OUTPUT_FILE,
    START_DATE, END_DATE, OVERRIDE_BLOCKS,
)

OUTPUT_PATH = PROJECT_ROOT / RAW_OUTPUT_FILE

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("MORALIS_API_KEY")
MORALIS_URL = "https://deep-index.moralis.io/api/v2.2/dateToBlock"

MORALIS_CHAIN_MAP = {
    "Ethereum": "eth",
    "Avalanche": "avalanche",
    "Optimism": "optimism",
    "Arbitrum": "arbitrum",
    "Base": "base",
    "Polygon": "polygon",
    "HyperEVM": "hyperliquid",
    "Monad": "monad",
}

# ── Date helpers ──

def format_date_for_moralis(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to 'YYYY-MM-DDT00:00:00+00:00' for Moralis."""
    return f"{date_str}T00:00:00+00:00"

def date_to_timestamp(date_str: str) -> int:
    """Convert 'YYYY-MM-DD' to unix timestamp (UTC)."""
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


# ── Block Fetching (Moralis) ──

def get_block_for_date(chain_name: str, date_str: str) -> int:
    """Fetch exact block number for a given date using Moralis."""
    moralis_chain = MORALIS_CHAIN_MAP.get(chain_name)
    if not moralis_chain:
        raise ValueError(f"Unknown chain mapping for Moralis: {chain_name}")
    
    formatted_date = format_date_for_moralis(date_str)
    res = requests.get(
        MORALIS_URL, 
        headers={"X-API-Key": API_KEY}, 
        params={"chain": moralis_chain, "date": formatted_date}
    )
    if res.status_code == 200:
        #BLOCK NUMBER PRINT
        print(f"{chain_name}: {res.json().get('block')}")
        return res.json().get('block')
    else:
        raise RuntimeError(f"Moralis API Error {res.status_code} for {chain_name}: {res.text}")


# ── Subsquid query ──

def build_payload(from_block: int, to_block: int) -> dict:
    return {
        "type": "evm",
        "fromBlock": from_block,
        "toBlock": to_block,
        "fields": {
            "block": {"number": True, "timestamp": True},
            "log": {
                "address": True,
                "topics": True,
                "data": True,
                "transactionHash": True,
                "logIndex": True,
            },
        },
        "logs": [{
            "address": [TOKEN_MESSENGER_V2],
            "topic0": [DEPOSIT_FOR_BURN_TOPIC],
        }],
    }


# ── Fetcher (raw logs only) ──

def fetch_raw_logs(chain_name: str, chain_config: tuple) -> list[dict]:
    dataset = chain_config[0]

    if chain_name in OVERRIDE_BLOCKS:
        from_block, to_block = OVERRIDE_BLOCKS[chain_name]
    else:
        try:
            from_block = get_block_for_date(chain_name, START_DATE)
            to_block = get_block_for_date(chain_name, END_DATE)
        except Exception as e:
            print(f"  {chain_name}: Error fetching blocks: {e}")
            return []

    print(f"  {chain_name}: querying blocks {from_block:}–{to_block:}...")

    url = f"{SQD_BASE_URL}/{dataset}/stream"
    start_ts = date_to_timestamp(START_DATE)
    end_ts = date_to_timestamp(END_DATE)

    records = []
    current_from_block = from_block

    while current_from_block <= to_block:
        payload = build_payload(current_from_block, to_block)
        
        # We explicitly request gzip to avoid zstd bugs in python's requests library
        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"
        }
        
        # Subsquid streams can be large; stream the response
        with requests.post(url, headers=headers, json=payload, stream=True) as response:
            try:
                response.raise_for_status()
            except Exception as e:
                print(f"  {chain_name}: Request failed at block {current_from_block}: {e}")
                break

            last_block_in_batch = current_from_block
            lines_parsed = 0
            
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    block = json.loads(line)
                except json.JSONDecodeError:
                    continue
                    
                lines_parsed += 1
                header = block["header"]
                last_block_in_batch = header["number"]
                
                if header["timestamp"] < start_ts or header["timestamp"] >= end_ts:
                    continue
                    
                for log in block.get("logs", []):
                    if (log.get("address", "").lower() != TOKEN_MESSENGER_V2.lower()
                            or log.get("topics", [None])[0] != DEPOSIT_FOR_BURN_TOPIC):
                        continue
                    records.append({
                        "source_chain": chain_name,
                        "block_number": header["number"],
                        "block_timestamp": header["timestamp"],
                        "tx_hash": log["transactionHash"],
                        "log_index": log["logIndex"],
                        "address": log["address"],
                        "topics": json.dumps(log["topics"]),
                        "data": log["data"],
                    })
            
            # Subsquid API chunks streams. If it stopped early, continue from next block.
            if lines_parsed == 0 or last_block_in_batch >= to_block:
                break
                
            current_from_block = last_block_in_batch + 1

    print(f"  {chain_name}: {len(records)} raw logs")
    return records


# ── Main ──

def main():
    print(f"CCTP V2 Raw Log Extraction: {START_DATE} → {END_DATE}\n")

    all_records = []
    for chain_name, chain_config in CHAINS.items():
        logs = fetch_raw_logs(chain_name, chain_config)
        all_records.extend(logs)

    all_records.sort(key=lambda r: r["block_timestamp"])

    if all_records:
        import pandas as pd
        df = pd.DataFrame(all_records)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUTPUT_PATH, index=False)
        print(f"\nWrote {len(all_records)} raw logs to {OUTPUT_PATH}")
    else:
        print("\nNo logs found.")

if __name__ == "__main__":
    main()