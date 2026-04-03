# CCTP V2 Bridge Analytics — Knowledgebase (Verified from Etherscan)

## The Core Idea
USDC is **burned** on source chain → **minted** on destination chain.
Linked by a **nonce** (a bytes32 hash, not a simple counter).

## Chain Domain IDs
| Domain | Chain        |
|--------|--------------|
| 0      | Ethereum     |
| 1      | Avalanche    |
| 2      | OP Mainnet   |
| 3      | Arbitrum One |
| 5      | Solana (non-EVM) |
| 6      | Base         |
| 7      | Polygon PoS  |

---

## Contracts

| Contract              | Address                                      | Role                          |
|-----------------------|----------------------------------------------|-------------------------------|
| TokenMessengerV2      | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | Burns on source, confirms mint on dest |
| MessageTransmitterV2  | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | Sends messages (source) & receives (dest) |
| TokenMinterV2         | `0xfd78EE919681417d192449715b2594ab58f5D002` | Internal: handles actual USDC burn/mint mechanics |

Note: TokenMessengerV2 and MessageTransmitterV2 are the same addresses across EVM chains.
USDC token address is DIFFERENT per chain (e.g. 0xA0b8...EB48 on Ethereum, 0xaf88...5831 on Arbitrum).

---

## Events to Extract (Verified from live Etherscan txs)

### SOURCE CHAIN — 2 events per bridge tx

#### 1. DepositForBurn ← THE MAIN BURN EVENT (what we need most)
- **Contract:** TokenMessengerV2 (`0x28b5...cf5d`)
- **topic0:** `0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5`
- **Topics (indexed):**
  - topic1 = `burnToken` (address) → USDC contract on source chain
  - topic2 = `depositor` (address) → **WHO bridged** ✅
  - topic3 = `minFinalityThreshold` (uint32) → typically 2000
- **Data (non-indexed):**
  - `amount` (uint256) → USDC amount (6 decimals, divide by 10⁶)
  - `mintRecipient` (bytes32) → **WHO receives** on dest chain ✅ (strip leading zeros for EVM)
  - `destinationDomain` (uint32) → which chain (0=ETH, 3=Arb, 6=Base, etc.)
  - `destinationTokenMessenger` (bytes32) → TokenMessengerV2 on dest
  - `destinationCaller` (bytes32) → who can relay (0 = anyone)
  - `maxFee` (uint256) → max fee willing to pay
  - `hookData` (bytes) → usually empty

#### 2. MessageSent ← contains message blob (optional for basic analytics)
- **Contract:** MessageTransmitterV2 (`0x81D4...B64`)
- **topic0:** `0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036`
- **Signature:** `MessageSent(bytes message)`
- **Note:** The nonce is NOT a visible field inside the bytes. The nonce = keccak256 hash of the message (computed by the contract).

### DESTINATION CHAIN — 2 events per bridge tx

#### 3. MintAndWithdraw ← THE MAIN MINT EVENT
- **Contract:** TokenMessengerV2 (`0x28b5...cf5d`) ⚠️ NOT TokenMinterV2!
- **topic0:** `0x50c55e915134d457debfa58eb6f4342956f8b0616d51a89a3659360178e1ab63`
- **Topics (indexed):**
  - topic1 = `mintRecipient` (address) → **WHO received** ✅
  - topic2 = `mintToken` (address) → USDC on destination chain
- **Data (non-indexed):**
  - `amount` (uint256) → USDC amount minted (6 decimals)
  - `feeCollected` (uint256) → fee taken (can be 0)

#### 4. MessageReceived ← the matching link
- **Contract:** MessageTransmitterV2 (`0x81D4...B64`)
- **topic0:** `0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c`
- **Topics (indexed):**
  - topic1 = `caller` (address) → who triggered receive
  - topic2 = `nonce` (bytes32) → hash-based nonce for matching
  - topic3 = `finalityThresholdExecuted` (uint32)
- **Data (non-indexed):**
  - `sourceDomain` (uint32) → which chain the burn happened on
  - `sender` (bytes32) → TokenMessengerV2 on source chain
  - `messageBody` (bytes) → contains amount, recipient, depositor etc.

### NOT a CCTP event (don't confuse):
- **`0xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8`** = USDC token's own `Mint(address,address,uint256)` event. This is emitted by the USDC token contract itself, NOT by CCTP contracts. Skip it.

---

## Complete Example: 21.29 USDC from Ethereum → Arbitrum

### Source chain (Ethereum) — 5 logs, we care about 2:
```
[skip] Log 1462: USDC Transfer    User → TokenMinterV2          (internal)
[skip] Log 1463: USDC Burn        TokenMinterV2 burns            (internal)
[skip] Log 1464: USDC Transfer    TokenMinterV2 → 0x000 (burn)  (internal)
[NEED] Log 1465: MessageSent      message blob for cross-chain
[NEED] Log 1466: DepositForBurn   depositor=0xb444, amount=21.29, dest=Arbitrum(3)
```

### Destination chain (Arbitrum) — 4 logs, we care about 2:
```
[skip] Log 1: USDC Mint           USDC token internal mint       (internal)
[skip] Log 2: USDC Transfer       0x000 → recipient             (internal)
[NEED] Log 3: MintAndWithdraw     recipient=0xFC80, amount=21.29, fee=0
[NEED] Log 4: MessageReceived     nonce=E6C5F2..., sourceDomain=0(ETH)
```

### Collected data:
```
WHO bridged:     0xb444A85121b593fBC81767cd4Cf4CeFAa24bd751 (depositor)
WHO received:    0xfC80B1fFa8327BD173124e4eea7510D124a7c93e (mintRecipient)
Amount burned:   21.29 USDC
Amount minted:   21.29 USDC
Fee collected:   0 USDC
Route:           Ethereum (domain 0) → Arbitrum (domain 3)
Nonce:           E6C5F277B5DFE0106CE41C67B357A391E34D1DC30EB8681368BE377B1366903A
```

---

## Subsquid Query Config (Corrected)

For SOURCE chains (burns):
```python
"address": [
    "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d",  # TokenMessengerV2
],
"topic0": [
    "0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5",  # DepositForBurn
]
```

For DESTINATION chains (mints):
```python
"address": [
    "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d",  # TokenMessengerV2
    "0x81D40F21F12A8F0E3252Bccb954D722d4c464B64",  # MessageTransmitterV2
],
"topic0": [
    "0x50c55e915134d457debfa58eb6f4342956f8b0616d51a89a3659360178e1ab63",  # MintAndWithdraw
    "0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c",  # MessageReceived
]
```

Since every chain can be BOTH source and destination, query ALL events on ALL chains:
```python
"address": [
    "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d",  # TokenMessengerV2
    "0x81D40F21F12A8F0E3252Bccb954D722d4c464B64",  # MessageTransmitterV2
],
"topic0": [
    "0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5",  # DepositForBurn
    "0x50c55e915134d457debfa58eb6f4342956f8b0616d51a89a3659360178e1ab63",  # MintAndWithdraw
    "0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c",  # MessageReceived
]
```

## Matching Strategy
- **Simple (no matching needed):** Just analyze DepositForBurn for burns, MintAndWithdraw for mints independently.
- **Full matching:** Match by (amount + mintRecipient + sourceDomain/destinationDomain + timestamp proximity).
- **Cryptographic matching:** Hash the MessageSent bytes → should equal nonce in MessageReceived.topic2.

## Address Format
- EVM addresses in bytes32: strip leading 24 hex chars of zeros → `"0x" + bytes32[24:]`
- Non-EVM (Solana, domain 5): full bytes32, no stripping


CCTP bridge Mainnet contract addresses
​
TokenMessengerV2
Blockchain,Domain,Address
Ethereum,0,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Avalanche,1,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
OP_Mainnet,2,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Arbitrum,3,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Base,6,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Polygon_PoS,7,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Unichain,10,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Linea,11,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Codex,12,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Sonic,13,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
World Chain,14,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Monad,15,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Sei,16,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
XDC,18,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
HyperEVM,19,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Ink,21,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
Plume,22,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
EDGE,28,0x98706A006bc632Df31CAdFCBD43F38887ce2ca5c
Morph,30,0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
​
MessageTransmitterV2
Blockchain,Domain,Address
Ethereum,0,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Avalanche,1,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
OP_Mainnet,2,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Arbitrum,3,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Base,6,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Polygon_PoS,7,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Unichain,10,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Linea,11,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Codex,12,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Sonic,13,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
World_Chain,14,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Monad,15,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Sei,16,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
XDC,18,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
HyperEVM,19,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Ink,21,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
Plume,22,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
EDGE,28,0x5b61381Fc9e58E70EfC13a4A97516997019198ee
Morph,30,0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
​
TokenMinterV2
Blockchain,Domain,Address
Ethereum,0,0xfd78EE919681417d192449715b2594ab58f5D002
Avalanche,1,0xfd78EE919681417d192449715b2594ab58f5D002
OP_Mainnet,2,0xfd78EE919681417d192449715b2594ab58f5D002
Arbitrum,3,0xfd78EE919681417d192449715b2594ab58f5D002
Base,6,0xfd78EE919681417d192449715b2594ab58f5D002
Polygon_PoS,7,0xfd78EE919681417d192449715b2594ab58f5D002
Unichain,10,0xfd78EE919681417d192449715b2594ab58f5D002
Linea,11,0xfd78EE919681417d192449715b2594ab58f5D002
Codex,12,0xfd78EE919681417d192449715b2594ab58f5D002
Sonic,13,0xfd78EE919681417d192449715b2594ab58f5D002
World Chain,14,0xfd78EE919681417d192449715b2594ab58f5D002
Monad,15,0xfd78EE919681417d192449715b2594ab58f5D002
Sei,16,0xfd78EE919681417d192449715b2594ab58f5D002
XDC,18,0xfd78EE919681417d192449715b2594ab58f5D002
HyperEVM,19,0xfd78EE919681417d192449715b2594ab58f5D002
Ink,21,0xfd78EE919681417d192449715b2594ab58f5D002
Plume,22,0xfd78EE919681417d192449715b2594ab58f5D002
EDGE,28,0x338Dfd607855BeEc17f33e539Ac2479853cC8384
Morph,30,0xfd78EE919681417d192449715b2594ab58f5D002
​
MessageV2
Blockchain,Domain,Address
Ethereum,0,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Avalanche,1,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
OP_Mainnet,2,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Arbitrum,3,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Base,6,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Polygon_PoS,7,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Unichain,10,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Linea,11,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Codex,12,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Sonic,13,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
World Chain,14,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Monad,15,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Sei,16,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
XDC,18,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
HyperEVM,19,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Ink,21,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
Plume,22,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78
EDGE,28,0x88ba38dbB2117879E500c11A0772e2B84Be000B3
Morph,30,0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78