import sys
import json
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

# Resolve project root (3 levels up from this file) and add src/ to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    DOMAIN_NAMES, RAW_OUTPUT_FILE, TRANSFORMED_OUTPUT_FILE,
)

RAW_PATH = PROJECT_ROOT / RAW_OUTPUT_FILE
TRANSFORMED_PATH = PROJECT_ROOT / TRANSFORMED_OUTPUT_FILE


# ── Decoder ──

def decode_deposit_for_burn(row: pd.Series) -> dict | None:
    """
    Decode a single DepositForBurn raw log row.
    Topics: topic1=burnToken, topic2=depositor, topic3=minFinalityThreshold
    Data chunks: [0]amount [1]mintRecipient [2]destDomain [3]destTokenMsgr [4]destCaller [5]maxFee [6+]hookData
    """
    topics = json.loads(row["topics"])
    data = row["data"][2:]  # strip 0x prefix
    chunks = [data[i : i + 64] for i in range(0, len(data), 64)]

    burn_token = "0x" + topics[1][26:]
    depositor = "0x" + topics[2][26:]
    amount_raw = int(chunks[0], 16)
    mint_recipient_raw = chunks[1]
    dest_domain = int(chunks[2], 16)

    is_evm = mint_recipient_raw[:24] == "0" * 24
    mint_recipient = ("0x" + mint_recipient_raw[24:]) if is_evm else mint_recipient_raw

    timestamp = row["block_timestamp"]
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return {
        "timestamp": dt.isoformat(),
        "unix_ts": timestamp,
        "source_chain": row["source_chain"],
        "dest_chain": DOMAIN_NAMES.get(dest_domain, f"unknown({dest_domain})"),
        "dest_domain": dest_domain,
        "burn_token": burn_token.lower(),
        "depositor": depositor.lower(),
        "recipient": mint_recipient.lower() if is_evm else mint_recipient,
        "amount": amount_raw / 1e6,
        "amount_raw": amount_raw,
        "tx_hash": row["tx_hash"],
        "block_number": row["block_number"],
        "log_index": row["log_index"],
    }


# ── Main ──

def main():
    if not RAW_PATH.exists():
        print(f"Raw log file not found: {RAW_PATH}")
        print("Run the extract step first.")
        sys.exit(1)

    print(f"Reading raw logs from {RAW_PATH}...")
    df_raw = pd.read_parquet(RAW_PATH)
    print(f"  {len(df_raw)} raw log rows loaded")

    decoded = []
    for _, row in df_raw.iterrows():
        rec = decode_deposit_for_burn(row)
        if rec:
            decoded.append(rec)

    if decoded:
        df_out = pd.DataFrame(decoded, columns=[
            "timestamp", "source_chain", "dest_chain", "burn_token", "depositor",
            "recipient", "amount", "tx_hash", "block_number", "log_index",
        ])
        TRANSFORMED_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_parquet(TRANSFORMED_PATH, index=False)
        print(f"\nWrote {len(decoded)} decoded burns to {TRANSFORMED_PATH}")
    else:
        print("\nNo burns decoded.")


if __name__ == "__main__":
    main()
