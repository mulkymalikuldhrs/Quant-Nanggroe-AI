# agents.crypto.tools

## Function: 

Lazy-load DexIntelligenceEngine from engine.screener.

*Line: 35*

---

## Function: 

Lazy-load MarketDataTool for real price data.

*Line: 45*

---

## Function: 

*Line: 57*

---

## Function: 

*Line: 83*

---

## Function: 

*Line: 104*

---

## Function: 

Fetch on-chain data for a cryptocurrency.

PRODUCTION: Uses DexIntelligenceEngine for real on-chain metrics
and MarketDataTool for real price/volume data.
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Crypto symbol (BTC, ETH, SOL, etc.)
    metrics: Specific on-chain metrics to fetch
    network: Blockchain network

Returns:
    JSON string with on-chain data

*Line: 135*

---

## Function: 

Analyze DEX trading activity for a cryptocurrency.

PRODUCTION: Uses DexIntelligenceEngine for real DEX analysis.
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Crypto symbol
    chain: Blockchain chain
    dex_name: Specific DEX to analyze (uniswap, sushiswap, curve, etc.)

Returns:
    JSON string with DEX analysis

*Line: 214*

---

## Function: 

Check smart contract risk for a given address.

PRODUCTION: Attempts real contract verification via block explorer APIs.
Falls back to mock data only in _MOCK_MODE.

Args:
    address: Contract address to check
    chain: Blockchain chain

Returns:
    JSON string with contract risk assessment

*Line: 272*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 19*

---

## Function: 

*Line: 23*

---

