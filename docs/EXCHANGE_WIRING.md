# Exchange API Wiring Guide — Quant Nanggroe AI

**Date:** 2026-06-24
**Status:** PREPARED — waiting for API keys

## Overview

This document describes how to wire real exchange APIs into Quant Nanggroe AI
when API keys become available. The infrastructure exists — factory, broker
classes, guard pipeline, risk systems, paper daemon — all waiting for
credentials.

## Supported Exchanges

### Factory-registered (CCXT-backed, 8 exchanges)

These are wired into `quant_nanggroe/exchange/factory.py` and can be created
via `ExchangeFactory.create("name", api_key=..., api_secret=...)`:

| Exchange   | Factory key  | Passphrase required | Spot | Futures | Perps |
|------------|-------------|---------------------|------|---------|-------|
| Binance    | `binance`   | No                  | Yes  | Yes     | Yes   |
| OKX        | `okx`       | Yes                 | Yes  | Yes     | Yes   |
| Bybit      | `bybit`     | No                  | Yes  | Yes     | Yes   |
| Bitget     | `bitget`    | Yes                 | Yes  | Yes     | Yes   |
| Kraken     | `kraken`    | No                  | Yes  | Yes     | No    |
| KuCoin     | `kucoin`    | Yes                 | Yes  | Yes     | Yes   |
| Gate       | `gate`      | No                  | Yes  | Yes     | Yes   |
| Coinbase   | `coinbase`  | Yes                 | Yes  | Yes     | No    |

### Native REST clients (exchange/clients/)

Three exchanges have hand-written REST client modules that bypass CCXT:

- **Binance** — `quant_nanggroe/exchange/clients/binance_client.py`
- **Bybit** — `quant_nanggroe/exchange/clients/bybit_client.py`
- **OKX** — `quant_nanggroe/exchange/clients/okx_client.py`

These extend `quant_nanggroe/exchange/clients/base_rest_client.py` and provide
exchange-specific rate limiting, auth signing, and error handling.

### Other brokers present

| Broker         | File                          | Notes |
|----------------|-------------------------------|-------|
| Paper          | `exchange/paper_broker.py`    | Currently active daemon |
| CCXT           | `exchange/ccxt_broker.py`     | Wraps CCXT for 8 exchanges |
| Alpaca         | `exchange/alpaca_broker.py`   | US stocks broker |
| IBKR           | `exchange/ibkr_broker.py`     | Interactive Brokers |
| MT5            | `exchange/mt5_broker.py`      | MetaTrader 5 |
| Polymarket     | `exchange/polymarket_broker.py` | Prediction market |
| Solana         | `exchange/solana/broker.py`   | Solana DEX/Jupiter |

## Step 1: Get API Keys

### Binance
1. Log in to [Binance](https://www.binance.com)
2. API Management → Create API → select "System Generated"
3. Permissions: **Enable Spot & Margin Trading** (do NOT enable futures initially)
4. **Restrict IP addresses** to your deployment server IP
5. Save key and secret immediately — secret shown only once

### Bybit
1. Log in to [Bybit](https://www.bybit.com)
2. API Management → Create Key → select "System Generated"
3. Permissions: **Spot Trade**, **Read** (no futures/derivatives)
4. **IP whitelist** recommended
5. Save key and secret

### OKX
1. Log in to [OKX](https://www.okx.com)
2. API → Create API Key → "Trading"
3. Permissions: **Trade**, **Read** (spot only)
4. **Passphrase** will be required — store it securely alongside key/secret
5. IP whitelist recommended

### Other exchanges
For Bitget, Kraken, KuCoin, Gate, Coinbase — API key creation flows are similar:
- Create API key with **Trade + Read** permissions
- Enable **spot trading only** (no futures/margin for initial deployment)
- **IP whitelist** where supported
- Save passphrase if required (see table above)

## Step 2: Configure Keys

Create `paper_state/exchange_config.json`:

```json
{
    "exchange": "binance",
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET",
    "passphrase": null,
    "testnet": true,
    "paper_first": true,
    "market_type": "spot"
}
```

| Field        | Description |
|-------------|-------------|
| `exchange`  | One of: `binance`, `okx`, `bybit`, `bitget`, `kraken`, `kucoin`, `gate`, `coinbase` |
| `api_key`   | Your exchange API key |
| `api_secret` | Your exchange API secret |
| `passphrase` | Required for OKX, Bitget, KuCoin, Coinbase; `null` otherwise |
| `testnet`   | `true` to use exchange sandbox/testnet (recommended first) |
| `paper_first` | `true` to test via paper broker before real execution |
| `market_type` | `"spot"` for initial deployment, `"futures"` or `"perps"` later |

Alternatively, set these environment variables (the factory reads them if
`create()` receives `None` for those params):

```bash
export EXCHANGE_API_KEY="your_key_here"
export EXCHANGE_API_SECRET="your_secret_here"
```

## Step 3: Test Connectivity

Run the readiness check:

```bash
python3 scripts/check_exchange_ready.py
```

Test factory import and broker creation:

```bash
python3 -c "
from quant_nanggroe.exchange.factory import ExchangeFactory
f = ExchangeFactory()
print('Supported:', f.list_supported_exchanges())
print('Capabilities:', f.get_capabilities('binance'))
"
```

Test live connectivity (with keys configured):

```bash
python3 -c "
from quant_nanggroe.exchange.factory import ExchangeFactory
f = ExchangeFactory()
b = f.create('binance', api_key='YOUR_KEY', api_secret='YOUR_SECRET', sandbox=True)
print(b.fetch_balance())
"
```

The testnet endpoint is used when `sandbox=True`. Binance testnet requires a
separate API key from https://testnet.binance.vision/.

## Step 4: Paper → Real Transition Protocol

This project has been running a paper daemon that simulates trading. Before
switching to real money:

1. **Paper track record**: Verify the daemon has been running for 30+ days
   with consistent positive P&L in `paper_state/pnl.csv`.

2. **Strategy health**: Check `paper_state/auto_disable_state.json` — no
   strategy should be auto-disabled due to low Sharpe.

3. **10% capital first**: Configure `exchange_config.json` with 10% of
   paper capital for the real exchange. Keep the paper daemon running
   alongside with the remaining 90%.

4. **Monitor for 7 days**: Watch daily P&L, slippage, fill rates.
   Compare real fills against paper broker fills.

5. **Scale up**: If 7-day real P&L tracks paper P&L within 20%, increase
   allocation to 50%. After another 7 days, go to 100%.

6. **Kill switch test**: Before going live, manually trigger the kill
   switch to verify it closes all positions:
   ```python
   from quant_nanggroe.engine.risk.kill_switch import KillSwitch
   ks = KillSwitch()
   ks.activate(level=KillSwitch.LEVEL_2, reason="Pre-live test")
   ```

## Step 5: Wire the Exchange in Code

### Option A — Through the factory (recommended)

Modify `scripts/qna-paper-daemon.py`:

1. Import the factory:
   ```python
   from quant_nanggroe.exchange.factory import ExchangeFactory
   ```

2. Create a real broker alongside the paper broker:
   ```python
   factory = ExchangeFactory()
   if args.live:
       config = json.loads(Path("paper_state/exchange_config.json").read_text())
       live_broker = factory.create(
           config["exchange"],
           api_key=config["api_key"],
           api_secret=config["api_secret"],
           passphrase=config.get("passphrase"),
           sandbox=config.get("testnet", True),
       )
   ```

3. Route orders through both brokers — paper for record-keeping, real
   for execution. The guard pipeline applies to both.

### Option B — Direct CCXTBroker

```python
from quant_nanggroe.exchange.ccxt_broker import CCXTBroker
from quant_nanggroe.exchange.base import ExchangeConfig

cfg = ExchangeConfig(
    exchange_id="binance",
    api_key="...",
    api_secret="...",
    sandbox=True,
    options={"defaultType": "spot"},
)
broker = CCXTBroker(cfg)
```

## Risk Settings for Live Trading

| Parameter | Value | Mechanism |
|-----------|-------|-----------|
| Max position size | 1% of capital | `MaxPositionGuard` in guard pipeline |
| Max daily loss | 2% (HARD STOP) | Risk manager & kill switch trigger |
| Max drawdown | 5% (HARD STOP) | Kill switch auto-activation |
| Max weekly loss | 4% (HARD STOP) | Risk manager |
| Allowed markets | Spot only | Exchange factory market type |
| Whitelist symbols | BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT | `WhitelistGuard` |

### Guard pipeline (already implemented)

File: `quant_nanggroe/exchange/guards.py`

```python
from quant_nanggroe.exchange.guards import (
    GuardPipeline,
    WhitelistGuard,
    CooldownGuard,
    MaxPositionGuard,
)
```

Every order passes through the configured guard pipeline before reaching
the exchange. Vetoes are logged and reported via the risk API.

## Rollback Plan

If anything goes wrong during live trading:

### Automatic (kill switch)
The kill switch in `quant_nanggroe/engine/risk/kill_switch.py` monitors
daily loss, weekly loss, and drawdown. If thresholds are breached:

- **LEVEL_1**: New positions blocked, existing positions maintained
- **LEVEL_2**: All positions closed at market, no new trades
- **LEVEL_3**: Full system shutdown, all operations ceased

These fire automatically based on risk manager state.

### Manual
```bash
# Stop the daemon
bash qna-stop.sh

# Verify all positions via exchange web UI
# Check paper_state/state.json and daemon.log for last trades

# Restart in paper-only mode (remove exchange_config.json or set
# exchange_config.json paper_first to true)
python3 scripts/qna-paper-daemon.py --capital 10000
```

### Recovery steps
1. Kill switch fires (or you hit Ctrl+C on the daemon)
2. Verify all positions closed via exchange web UI
3. Remove or rename `paper_state/exchange_config.json`
4. Restart daemon in paper-only mode
5. Investigate cause — review daemon logs, kill switch activation reason,
   correlation monitor state
6. Fix issue, re-test on paper, then re-enable live

## Files to Modify When Going Live

| File | Change |
|------|--------|
| `paper_state/exchange_config.json` | Create with real keys |
| `scripts/qna-paper-daemon.py` | Add `--live` flag + factory.create() for real broker |
| `quant_nanggroe/exchange/factory.py` | May need proxy config for restricted networks |
| `paper_state/guards_config.json` | Tighten position sizing for real capital |

## FAQ

**Q: Do I need to install CCXT?**
A: Yes. `pip install ccxt`. The factory imports it lazily.

**Q: Can I use the native REST clients instead of CCXT?**
A: The REST clients in `exchange/clients/` exist but the factory uses CCXTBroker.
If you prefer native clients, wire them directly — they implement the same
`ExchangeInterface`.

**Q: What about WebSocket?**
A: The interface defines `subscribe_websocket()`. CCXT supports WebSocket
via `ccxt.pro` (separate install: `pip install ccxtpro`). The native clients
may have their own WebSocket implementations.

**Q: Should I use testnet first?**
A: Always. Set `testnet: true` in exchange_config.json. Binance testnet
requires a separate API key at https://testnet.binance.vision/.

**Q: What happens if the daemon crashes mid-trade?**
A: Unfilled orders remain on the exchange. On restart, fetch open orders
via `broker.fetch_open_orders()` and reconcile. The paper broker is
stateless per cycle.
