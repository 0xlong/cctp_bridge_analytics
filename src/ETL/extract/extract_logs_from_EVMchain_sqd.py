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
    DEPOSIT_FOR_BURN_TOPIC, DOMAIN_NAMES,
    START_DATE, END_DATE, OUTPUT_FILE, OVERRIDE_BLOCKS,
)

OUTPUT_PATH = PROJECT_ROOT / OUTPUT_FILE

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


# ── Decoder ──

def decode_deposit_for_burn(log: dict, block_header: dict, source_chain: str) -> dict | None:
    """
    Decode DepositForBurn log.
    Topics: topic1=burnToken, topic2=depositor, topic3=minFinalityThreshold
    Data chunks: [0]amount [1]mintRecipient [2]destDomain [3]destTokenMsgr [4]destCaller [5]maxFee [6+]hookData
    """
    topics = log["topics"]
    data = log["data"][2:]
    chunks = [data[i : i + 64] for i in range(0, len(data), 64)]

    burn_token = "0x" + topics[1][26:]
    depositor = "0x" + topics[2][26:]
    amount_raw = int(chunks[0], 16)
    mint_recipient_raw = chunks[1]
    dest_domain = int(chunks[2], 16)

    is_evm = mint_recipient_raw[:24] == "0" * 24
    mint_recipient = ("0x" + mint_recipient_raw[24:]) if is_evm else mint_recipient_raw

    timestamp = block_header["timestamp"]
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return {
        "timestamp": dt.isoformat(),
        "unix_ts": timestamp,
        "source_chain": source_chain,
        "dest_chain": DOMAIN_NAMES.get(dest_domain, f"unknown({dest_domain})"),
        "dest_domain": dest_domain,
        "burn_token": burn_token.lower(),
        "depositor": depositor.lower(),
        "recipient": mint_recipient.lower() if is_evm else mint_recipient,
        "amount": amount_raw / 1e6,
        "amount_raw": amount_raw,
        "tx_hash": log["transactionHash"],
        "block_number": block_header["number"],
        "log_index": log["logIndex"],
    }


# ── Fetcher ──

def fetch_burns(chain_name: str, chain_config: tuple) -> list[dict]:
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
                    rec = decode_deposit_for_burn(log, header, chain_name)
                    if rec:
                        records.append(rec)
            
            # Subsquid API chunks streams. If it stopped early, continue from next block.
            if lines_parsed == 0 or last_block_in_batch >= to_block:
                break
                
            current_from_block = last_block_in_batch + 1

    print(f"  {chain_name}: {len(records)} burns")
    return records


# ── Main ──

def main():
    print(f"CCTP V2 Burns: {START_DATE} → {END_DATE}\n")

    all_records = []
    for chain_name, chain_config in CHAINS.items():
        burns = fetch_burns(chain_name, chain_config)
        all_records.extend(burns)

    all_records.sort(key=lambda r: r["unix_ts"])

    if all_records:
        import pandas as pd
        df = pd.DataFrame(all_records, columns=[
            "timestamp", "source_chain", "dest_chain", "burn_token", "depositor",
            "recipient", "amount", "tx_hash", "block_number", "log_index",
        ])
        df.to_parquet(OUTPUT_PATH, index=False)
        print(f"\nWrote {len(all_records)} records to {OUTPUT_PATH}")
    else:
        print("\nNo burns found.")

if __name__ == "__main__":
    main()