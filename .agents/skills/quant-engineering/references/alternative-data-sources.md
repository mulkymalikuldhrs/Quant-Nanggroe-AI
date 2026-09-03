# Real Alternative Data Sources

## COT (Commitment of Traders) — FREE

**Source**: CFTC (Commodity Futures Trading Commission)
**URL**: `https://www.cftc.gov/MarketReports` or direct API

```python
# CFTC COT data is FREE and updated weekly (Fridays at 3:30 PM ET)
# Direct download URL pattern:
# https://www.cftc.gov/dea/futures/deacmelf.htm (current year)
# https://www.cftc.gov/dea/futures/deacmelf{year}.htm (historical)

# Or use the CFTC API:
# https://marketreports.cftc.gov/api/v1/legacyreport/dea/futures?format=json&report_type=fof

# Key fields:
# - Non-commercial (speculator) positions (net long/short)
# - Commercial (hedger) positions
# - Change from previous week
# - Extreme readings (2+ year highs/lows)

# COT Index = percentile of current net_position over N-week lookback
# Signal: when COT index < 20 → contrarian BUY (extreme bearish speculation)
# Signal: when COT index > 80 → contrarian SELL (extreme bullish speculation)
```

## On-Chain Crypto — FREE TIERS

| Provider | Free Tier | Data | Notes |
|---|---|---|---|
| Glassnode | 10 metrics, 1yr history | NUPL, SOPR, MVRV, active addresses | Best for BTC/ETH fundamentals |
| Whale Alert | 1000 alerts/mo | Large on-chain transfers ($1M+) | Good for unusual whale activity |
| Dune Analytics | Free queries | Custom SQL on blockchain data | Flexible but requires SQL skills |
| Etherscan/BscScan | 100K calls/day | Token transfers, gas, contracts | Direct blockchain queries |
| DefiLlama | Free | TVL, yields, protocol metrics | DeFi ecosystem data |
| LunarCrush | Free tier | Social + on-chain metrics | Altcoin social sentiment |

```python
# Glassnode API (free tier):
# https://api.glassnode.com/v1/metrics/indicators/sopr?a=BTC
# Requires: GLASSNODE_API_KEY (free registration)

# Whale Alert API (free tier):
# https://api.whale-alert.io/v1/transaction/{hash}
# Requires: WHALE_ALERT_API_KEY (free registration)

# On-chain signals:
# - SOPR > 1: BTC holders selling at profit (potential top)
# - SOPR < 1: BTC holders selling at loss (potential bottom)
# - MVRV > 3: Overvalued, historically mean-reverts
# - NUPL > 0.75: Euphoria zone
# - Large exchange inflows: Selling pressure
# - Large exchange outflows: Accumulation
```

## News Sentiment — FREE TIERS

| Provider | Free Tier | Coverage | Notes |
|---|---|---|---|
| Finnhub | 60 calls/min | News, SEC filings, analyst ratings | Already has provider in QNA |
| NewsAPI | 100 req/day, dev only | 70K+ sources, real-time | Good for general news |
| Alpha Vantage | 25 req/day | News sentiment scoring | Simple integration |
| StockNews API | 1000 calls/mo | News + analyst ratings | Good for stocks |
| LunarCrush | Free tier | Social + sentiment for crypto | Reddit, Twitter, etc. |

```python
# Finnhub sentiment (already wired in QNA):
# GET https://finnhub.io/api/v1/news-sentiment?symbol=AAPL
# Response: bearishPercent, bullishPercent, buzz, sentiment score

# NewsAPI integration:
# GET https://newsapi.org/v2/everything?q={symbol}&sortBy=publishedAt&language=en
# Score: positive/negative/neutral per article, aggregate

# Simple sentiment scoring:
# 1. Fetch news headlines for symbol
# 2. Score each headline (positive/negative/neutral) using keyword lists or LLM
# 3. Aggregate: weighted average by recency and source weight
# 4. Signal: sentiment > threshold → BUY, < -threshold → SELL
```

## Dark Pool / Block Trades — PAID (but free alternatives)

| Provider | Cost | Data | Free Alternative |
|---|---|---|---|
| FINRA Dark Pools | Free (delayed) | Daily block trade data | Use FINRA's TRF data directly |
| Fidelity Dark Pool | Via API | Fidelity-specific dark pool | Limited to Fidelity orders |
| Cheddar Flow | $29/mo | Options flow, dark pool prints | 7-day free trial |
| Unusual Whales | $50/mo | Options + dark pool sweeps | Twitter free posts are delayed |

```python
# FINRA TRF (Trade Reporting Facility) — FREE with delay:
# https://www.finra.org/filing-reporting/regulatory-filing-systems/trade-reporting-facility
# Dark pool data is reported to TRF exchanges (not lit exchanges)
# Use volume analysis: if total volume > exchange volume, difference is dark pool

# Proxy for dark pool activity (FREE, what most "dark pool" strategies actually use):
# 1. Calculate average daily volume over 20 days
# 2. If current volume > 3x average → potential block trade
# 3. If block trade direction matches price move → institutional accumulation/distribution
# 4. This is what QNA's DarkPoolFlowStrategy does — it's a proxy, not real dark pool data
```

## Macro / Economic — FREE

| Provider | Free Tier | Data | Notes |
|---|---|---|---|
| FRED | Free (API key required) | GDP, CPI, rates, employment | Already has provider in QNA |
| ECB SDW | Free | Euro area economic data | Good for forex |
| World Bank | Free | Global macro indicators | Good for emerging markets |
| OECD | Free | Economic outlook, indicators | Good for developed markets |
| SEC EDGAR | Free | Company filings (10-K, 10-Q) | Already has provider in QNA |

---


---

> **SSOT:** `CANONICAL.md` v8.1.0 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
