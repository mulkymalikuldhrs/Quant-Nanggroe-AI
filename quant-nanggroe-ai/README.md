# Quant Nanggroe AI — Agentic Trading Intelligence OS

> **Cluster 1 Foundation**: Types, Data Providers, Quant Engines, and Utilities

[![CI](https://github.com/nanggroe/quant-nanggroe-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/nanggroe/quant-nanggroe-ai/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Overview

Quant Nanggroe AI is an **Agentic Trading Intelligence OS** that combines quantitative analysis, multi-agent coordination, and real-time market data into a unified decision-making system. This is Phase 1 — the Foundation layer that everything else builds on.

### Core Principles

1. **Risk > Opportunity**: Risk assessment must always precede opportunity assessment
2. **Regime > Strategy**: Market regime must allow strategy execution
3. **Structure > Indicator**: Market structure overrides indicator signals
4. **Invalidation > R/R**: Invalidation logic overrides risk/reward calculations
5. **NO_TRADE is Valid**: Choosing not to trade is always a valid decision

## Architecture

```
quant_nanggroe/
├── config/          # Pydantic Settings, structured logging
├── types/           # Shared type definitions (Pydantic v2)
│   ├── market.py    # OHLCV, Ticker, OrderBook
│   ├── orders.py    # Market, Limit, Stop, StopLimit orders
│   ├── positions.py # Position tracking with P&L
│   ├── signals.py   # Signals with confidence scores
│   ├── risk.py      # VaR, CVaR, Drawdown, Constitution
│   ├── agents.py    # Agent configs, states, contracts
│   └── decisions.py # Regimes, pressures, confluence, decisions
├── data/            # Data access layer
│   ├── providers/   # Yahoo, Binance, Alpaca, Alpha Vantage, CoinGecko, Polygon, FRED
│   ├── cache.py     # Redis/file/memory cache with TTL
│   ├── normalizer.py # Cross-provider data normalization
│   └── manager.py   # DataProviderManager with AutoSwitch failover
├── engine/          # Core quant engines
│   ├── indicators.py # RSI, SMA, EMA, MACD, Bollinger, VWAP, ATR, ADX, Stochastic, CCI
│   ├── market_state.py # Market regime detection (6 regimes)
│   └── pressure.py  # Pressure normalization (weighted sensor fusion)
└── utils/           # Shared utilities
    ├── math.py      # Safe divide, clamp, pct change, rolling sum
    ├── time.py      # Market hours, timezone handling
    └── validation.py # Input validation with detailed errors
```

## Quick Start

```bash
# Install dependencies
make install

# Run tests
make test

# Run with coverage
make test-cov

# Lint and format
make lint
make format
```

## Data Providers

| Provider | Asset Class | Auth Required | Trust Score |
|----------|-------------|---------------|-------------|
| Yahoo Finance | Equities, ETFs | No | 0.85 |
| Binance | Crypto | Optional | 0.95 |
| Alpaca | US Equities | Yes | 0.90 |
| Alpha Vantage | Equities, Forex | Yes | 0.80 |
| CoinGecko | Crypto | No | 0.85 |
| Polygon.io | Equities, Crypto | Yes | 0.92 |
| FRED | Macro/Economic | Yes | 0.98 |

The `DataProviderManager` provides automatic failover — if one provider fails, it automatically tries the next healthiest provider.

## Technical Indicators

All indicators use **Wilder's Smoothing** (not SMA proxy) for RSI, ATR, and ADX:

- **RSI**: 14-period Wilder's Smoothing
- **MACD**: 12/26/9 EMA standard
- **Bollinger Bands**: 20-period, 2σ
- **VWAP**: Cumulative typical price weighted by volume
- **ATR**: 14-period Wilder's Smoothing
- **ADX**: Proper Wilder's Smoothing (not SMA approximation)
- **Stochastic**: 14/3 %K/%D
- **CCI**: 20-period

## Market Regime Detection

The `MarketStateEngine` classifies markets into 6 regimes:

| Regime | Condition | Agent Action |
|--------|-----------|--------------|
| TRENDING | ADX > 25 | Follow trend strategies |
| RANGE | Low ADX, neutral RSI | Range-bound strategies |
| MEAN_REVERT | Low ADX, RSI extremes | Contrarian strategies |
| RISK_OFF | Price drop 2–5% | Reduce exposure |
| PANIC | Price drop > 5% | All agents idle |
| NO_TRADE | Insufficient data | All agents idle |

## Pressure Normalization

Agent outputs are converted to numerical pressures with configurable weights:

| Agent | Weight | Input |
|-------|--------|-------|
| Quant Scanner | 25% | Trend strength + structure state |
| SMC Agent | 30% | Liquidity sweep + displacement |
| News Sentinel | 20% | Impact score + sentiment bias |
| Flow/Whale | 25% | Positioning bias + flow imbalance |

## Configuration

All configuration is via environment variables (or `.env` file):

```bash
# Core
APP_ENV=development
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./data/quant_nanggroe.db
REDIS_URL=redis://localhost:6379/0

# API Keys (all optional depending on provider)
ALPHA_VANTAGE_API_KEY=
POLYGON_API_KEY=
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
FRED_API_KEY=
BINANCE_API_KEY=
BINANCE_SECRET_KEY=

# Risk Parameters
MAX_LEVERAGE=3.0
DAILY_DRAWDOWN_LIMIT=0.05
VAR_CONFIDENCE_LEVEL=0.95
```

## Docker

```bash
# Build and run
make docker-build
make docker-up

# Stop
make docker-down
```

## Testing

```bash
# All tests
make test

# Specific test suites
make test-types     # Type definition tests
make test-data      # Data layer tests
make test-engine    # Engine calculation tests

# With coverage report
make test-cov
```

## License

MIT
