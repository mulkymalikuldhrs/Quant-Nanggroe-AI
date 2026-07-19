# Market Data APIs & Connectors — Research Report

**Date:** July 2026  
**Scope:** Free & paid APIs for stocks, forex, crypto, futures  
**Minimum Count:** 15 APIs documented

---

## 1. yfinance (Unofficial Yahoo Finance)

| Field | Detail |
|-------|--------|
| **URL** | https://pypi.org/project/yfinance/ |
| **Type** | Python library (unofficial, scrapes Yahoo Finance) |
| **Pricing** | Free |
| **Rate Limits** | ~360 requests/hour (unofficial); Yahoo enforces throttling aggressively. Frequent blocks. |
| **Coverage** | Stocks, ETFs, forex, crypto, options, fundamentals, economic data |
| **Pros** | Free, simple, broad coverage, huge community |
| **Cons** | Unofficial — can break anytime, no SLA, increasing rate limits/blocks |
| **Best for** | Quick prototyping, personal projects, light backtesting |

---

## 2. Alpha Vantage

| Field | Detail |
|-------|--------|
| **URL** | https://www.alphavantage.co |
| **Pricing** | **Free:** 25 req/day. **Premium:** $49.99/mo (75 req/min) → $249.99/mo (1,200 req/min). Annual plans also available. |
| **Rate Limits** | Free: 25 requests/day, ~5 req/min. Paid: 75–1,200 req/min, no daily limit. |
| **Coverage** | Stocks, ETFs, forex, crypto, commodities, technical indicators, economic indicators, fundamentals |
| **Pros** | 🏆 Very generous free tier historically (now reduced), broad data, MCP server for AI agents |
| **Cons** | Free tier reduced to 25/day (was 500/day), 15-min delayed data on free |
| **Best for** | General-purpose market data, AI/agent integrations (official MCP server) |
| **Notes** | Licensed by NASDAQ, OPRA. Official MCP server listed in Anthropic's MCP catalogue. |

---

## 3. Polygon.io / Massive (rebranded Oct 2025)

| Field | Detail |
|-------|--------|
| **URL** | https://polygon.io → https://massive.com |
| **Pricing** | **Free:** Very limited (5 req/min). **Paid:** $29/mo (Basic) → custom enterprise |
| **Rate Limits** | Free: 5 API calls/min. Paid: varies by plan (higher rate limits, unlimited API calls on $29/mo plan) |
| **Coverage** | Stocks, options, forex, crypto, futures, indices — real-time & historical (30+ years) |
| **Pros** | Institutional-grade data, WebSocket streams, great API docs |
| **Cons** | Free tier extremely restrictive; pricing jumps quickly |
| **Best for** | Serious algorithmic trading, production apps needing high-quality US market data |
| **Notes** | Rebranded to Massive in Oct 2025. Old endpoint `api.polygon.io` still works; new endpoint is `api.massive.com`. Python SDK moved to `massive-com/client-python`. |

---

## 4. Twelve Data

| Field | Detail |
|-------|--------|
| **URL** | https://twelvedata.com |
| **Pricing** | **Free:** Limited daily credits. **Pro:** $229/mo (annual). **Ultra:** $999/mo (annual). |
| **Rate Limits** | Credit-based system (separate API + WebSocket credits). Free tier has very limited daily credits. |
| **Coverage** | Stocks, forex, crypto, ETFs, indices, commodities, technical indicators — 60+ exchanges |
| **Pros** | Clean API, WebSocket support, broad asset coverage, student discounts available |
| **Cons** | Credit-based pricing can be confusing; free tier very limited |
| **Best for** | Multi-asset projects needing stocks + crypto + forex in one API |

---

## 5. Finnhub

| Field | Detail |
|-------|--------|
| **URL** | https://finnhub.io |
| **Pricing** | **Free:** $0/mo. **All-In-One:** $3,500/mo (annual only) |
| **Rate Limits** | Free: 60 API calls/min. Paid: 900 calls/min (market data) + 300 calls/min (fundamental) |
| **Coverage** | **Free:** US stocks only. **Paid:** Global. Fundamentals, SEC filings, earnings estimates, news, social sentiment, ETFs |
| **Pros** | Generous free tier (60 req/min), excellent fundamental + alternative data |
| **Cons** | Free tier US-only; huge price gap to paid |
| **Best for** | US equities research + alternative data (social sentiment, SEC filings, patents) |
| **Notes** | Free: 50 WebSocket symbols. Paid: unlimited symbols. |

---

## 6. Financial Modeling Prep (FMP)

| Field | Detail |
|-------|--------|
| **URL** | https://site.financialmodelingprep.com |
| **Pricing** | **Free:** Limited req/day. **Premium:** ~$29–$49/mo. **Enterprise:** Custom. |
| **Rate Limits** | Varies by plan; free tier very limited |
| **Coverage** | Stocks, ETFs, mutual funds, financial statements (income, balance sheet, cash flow), SEC filings, ratios, DCF valuation |
| **Pros** | Excellent fundamental/financial statement data, easy JSON API |
| **Cons** | Limited real-time data, coverage focuses on fundamentals |
| **Best for** | Fundamental analysis, stock screening, valuation models |

---

## 7. Alpaca Markets (Trading + Market Data API)

| Field | Detail |
|-------|--------|
| **URL** | https://alpaca.markets |
| **Pricing** | **Free tier:** 200 API calls/min for trading & market data. **Paid data subscriptions** for real-time SIP/OPRA data. |
| **Rate Limits** | Free: 200 API calls/min |
| **Coverage** | US stocks, ETFs, options (trading + data). Commission-free trading API. |
| **Pros** | Best free rate limit (200/min), trading + data in one platform, good SDKs (Python/Node) |
| **Cons** | US equities only (no forex, crypto for data); real-time data requires exchange subscriptions |
| **Best for** | Algorithmic trading strategies, combined trading + data needs |

---

## 8. CoinGecko (Crypto)

| Field | Detail |
|-------|--------|
| **URL** | https://www.coingecko.com/en/api |
| **Pricing** | **Free (Demo):** 10–30 calls/min. **Analyst:** ~$79/mo. **Professional:** ~$299/mo. **Enterprise:** Custom. |
| **Rate Limits** | Free: 10-30 calls/min (endpoints vary). Paid: higher tiers. |
| **Coverage** | 10,000+ cryptocurrencies, market data, exchange data, DeFi, NFTs, on-chain data |
| **Pros** | Most comprehensive crypto data API, excellent free tier, no API key needed for basic |
| **Cons** | Crypto only; rate limits vary by endpoint |
| **Best for** | Crypto portfolio tracking, market analysis, DeFi/NFT data |

---

## 9. CoinMarketCap (Crypto)

| Field | Detail |
|-------|--------|
| **URL** | https://coinmarketcap.com/api/ |
| **Pricing** | **Free:** 333 calls/day. **Basic:** $69/mo. **Hobbyist:** $299/mo. **Startup:** $899/mo. **Enterprise:** Custom. |
| **Rate Limits** | Free: 333 calls/day, 30 calls/min. Paid: higher limits. |
| **Coverage** | Cryptocurrency prices, market cap, volume, exchange listings, historical data, global metrics |
| **Pros** | Industry-standard crypto data source, widely quoted |
| **Cons** | Crypto only; free tier quite limited now |
| **Best for** | Crypto market data with industry-standard reference prices |

---

## 10. Databento (Institutional-Grade)

| Field | Detail |
|-------|--------|
| **URL** | https://databento.com |
| **Pricing** | Pay-per-use (per megabyte), no subscription required |
| **Rate Limits** | No hard rate limits — metered billing based on data volume consumed |
| **Coverage** | US equities (all exchanges + ATS, L1-L3), futures (CME/CBOT, ICE), options (full OPRA) |
| **Pros** | Institutional-grade raw exchange data (MDP format), pay only for what you use, excellent developer experience |
| **Cons** | US markets only; pricing can add up for heavy users |
| **Best for** | HFT/quants needing raw tick-level data, order book L2/L3 |

---

## 11. Marketstack

| Field | Detail |
|-------|--------|
| **URL** | https://marketstack.com |
| **Pricing** | **Free:** 100 req/month (10 req/day). **Standard:** $29.99/mo (10K req/month). **Professional:** $99.99/mo (50K req/month). **Enterprise:** $199.99/mo (unlimited). |
| **Rate Limits** | Free: 100 req/month, 10 req/day. Paid: higher. |
| **Coverage** | 70+ global stock exchanges, real-time + historical EOD data, forex, crypto, ETFs |
| **Pros** | Good global exchange coverage, simple REST API, affordable paid plans |
| **Cons** | Very restrictive free tier; intraday data limited on lower plans |
| **Best for** | Global stock data, EOD price retrieval |

---

## 12. EODHD (EOD Historical Data)

| Field | Detail |
|-------|--------|
| **URL** | https://eodhd.com |
| **Pricing** | **Free:** Limited (100 req/day). **Basic:** ~$39.99/mo. **Premium:** custom. |
| **Rate Limits** | Free: 100 req/day. Paid: varies by plan. |
| **Coverage** | Global stocks, ETFs, mutual funds, forex, crypto, fundamentals, macroeconomic, options, insider trades |
| **Pros** | Broad global coverage (100+ exchanges), fundamentals + price in one API |
| **Cons** | Free tier very limited; docs can be clunky |
| **Best for** | Global multi-asset research, fundamental + price data |

---

## 13. Tiingo

| Field | Detail |
|-------|--------|
| **URL** | https://www.tiingo.com |
| **Pricing** | **Free:** End-of-day stock data. **Paid:** ~$10-20/mo for real-time data and additional features |
| **Rate Limits** | Free: limited. Paid: higher limits. |
| **Coverage** | US stocks, ETFs, forex, crypto, fundamentals, insider trading |
| **Pros** | Affordable paid plans, clean API, end-of-day data free |
| **Cons** | Smaller provider, less coverage than bigger competitors |
| **Best for** | Budget-friendly US stock data with some crypto/forex |
| **Notes** | Has hedge fund/insider trading data which is unique |

---

## 14. Barchart OnDemand

| Field | Detail |
|-------|--------|
| **URL** | https://www.barchart.com/ondemand |
| **Pricing** | Usage-based (pay per request/use), no fixed subscription required |
| **Rate Limits** | Flexible/negotiated — usage-based model |
| **Coverage** | Equities, futures, options, forex, commodities — deep historical + real-time |
| **Pros** | Pay only for what you use, extensive futures/options coverage |
| **Cons** | No free tier; pricing complex/custom |
| **Best for** | Futures & options traders needing professional data |

---

## 15. Intrinio

| Field | Detail |
|-------|--------|
| **URL** | https://intrinio.com |
| **Pricing** | Modular packages (Bronze/Silver/Gold). Real-time: from ~$300/mo. EOD: from ~$25/mo. |
| **Rate Limits** | Varies by package; WebSocket streams available |
| **Coverage** | US stocks, ETFs, options, fundamentals, ESG, real estate, alternative data |
| **Pros** | Modular a la carte pricing, 50+ years historical, Snowflake integration, options Greeks |
| **Cons** | Can get expensive quickly; US-focused |
| **Best for** | Options traders needing Greeks; fintechs needing packaged data sets |

---

## Comparison Matrix

| API | Free Tier | Paid From | Rate Limit (Free) | Stocks | Forex | Crypto | Futures | Real-Time |
|-----|-----------|-----------|-------------------|--------|-------|--------|---------|-----------|
| **yfinance** | ✅ Free | — | ~360/hr (unofficial) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Alpha Vantage** | ✅ 25/day | $49.99/mo | 25/day, 5/min | ✅ | ✅ | ✅ | ✅ | Paid |
| **Polygon/Massive** | ✅ 5/min | $29/mo | 5/min | ✅ | ✅ | ✅ | ✅ | Paid |
| **Twelve Data** | ✅ Credits | $229/mo | Limited credits | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Finnhub** | ✅ 60/min | $3,500/mo | 60/min | ✅ | ❌ | ❌ | ❌ | ✅ |
| **FMP** | ✅ Limited | $29/mo | Varies | ✅ | ❌ | ❌ | ❌ | Paid |
| **Alpaca** | ✅ 200/min | Free (200/min) | 200/min | ✅ | ❌ | ❌ | ❌ | Paid |
| **CoinGecko** | ✅ 10-30/min | $79/mo | 10-30/min | ❌ | ❌ | ✅ | ❌ | ✅ |
| **CoinMarketCap** | ✅ 333/day | $69/mo | 333/day, 30/min | ❌ | ❌ | ✅ | ❌ | ✅ |
| **Databento** | ❌ Metered | Pay/use | No hard limit | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Marketstack** | ✅ 100/mo | $29.99/mo | 100/mo, 10/day | ✅ | ✅ | ✅ | ❌ | Paid |
| **EODHD** | ✅ 100/day | $39.99/mo | 100/day | ✅ | ✅ | ✅ | ❌ | Paid |
| **Tiingo** | ✅ EOD | ~$10-20/mo | Limited | ✅ | ✅ | ✅ | ❌ | Paid |
| **Barchart** | ❌ | Usage-based | Usage-based | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Intrinio** | ❌ | ~$25/mo (EOD) | Package-based | ✅ | ❌ | ❌ | ❌ | Paid |

---

## Quick Recommendations

| Use Case | Recommended API |
|----------|----------------|
| **Quick prototyping / personal** | yfinance, Alpha Vantage (free), Finnhub (free) |
| **Production US stocks + trading** | Alpaca (best free rate limit), Polygon/Massive |
| **Global multi-asset data** | Twelve Data, Marketstack, EODHD |
| **Crypto-focused** | CoinGecko (best free), CoinMarketCap (industry standard) |
| **Fundamental/valuation analysis** | Financial Modeling Prep, Intrinio |
| **Institutional-grade tick data** | Databento (pay-per-use, no limit) |
| **Futures/options deep data** | Barchart, Databento |
| **AI/Agent integrations** | Alpha Vantage (official MCP server), Alpaca (MCP server) |
| **Lowest budget** | yfinance (free), Tiingo (low-cost paid), Finnhub (generous free tier) |
| **WebSocket streaming** | Polygon/Massive, Twelve Data, Finnhub, CoinGecko, Alpaca |

---

## Deprecated / Shutdown

- **IEX Cloud** — Officially shut down August 31, 2024. No longer available.

---

## Notes

- All pricing and rate limits are as of July 2026 and subject to change.
- "Free" tiers may have delayed data (15-min delay common for stocks).
- Real-time US stock and options data requires exchange fees and regulatory compliance for most commercial providers.
- Polygon.io rebranded to **Massive** in October 2025 — old API endpoint remains operational.
- IEX Cloud shut down permanently in 2024 — most users migrated to Polygon/Massive, Alpha Vantage, or Finnhub.
