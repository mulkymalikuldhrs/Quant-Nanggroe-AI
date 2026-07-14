# Broker Connectivity Matrix — Quant Nanggroe AI

Audit date: 2026-07-13
Scope: IBKR, Alpaca, CCXT, Paper, Factory, Manager

## 1. Connect/Auth Flow Completeness

| Broker | Method | Strategy | Credential Handling | Auth Guard | Status |
|--------|--------|----------|-------------------|------------|--------|
| **IBKR** | `connect()` | Lazy-imports `ib_insync` → creates `IB()` → `ib.connectAsync(host, port, client_id)` | host/port/client_id from config.options | `_require_ib()` guard | ✅ **Complete** |
| **Alpaca** | `connect()` | Lazy-imports `alpaca.trading.client.TradingClient` → instantiates with api_key/secret/sandbox | api_key/secret from config | `_state check` | ✅ **Complete** |
| **CCXT** | `connect()` | Creates ccxt async exchange instance from `ccxt.async_support` | api_key/secret/password from config | `_require_connection()` guard | ✅ **Complete** |
| **Paper** | `connect()` | Sets `_connected = True` immediately | No credentials | State flag | ✅ **Trivial** |

### Issues
- **IBKR**: Requires TWS/IB Gateway running externally — no built-in health check on startup
- **Alpaca**: No `disconnect()` logic beyond state reset; circuit breaker only resets on success, not on disconnect
- **CCXT**: `import ccxt.async_support as ccxt` at **module level** (line 26 of `ccxt_broker.py`) — this hangs 60+ seconds on cold import and is triggered whenever any broker module is imported (via `factory.py` L43 which imports CCXTBroker wrapped in try/except)

---

## 2. Order Placement (Market / Limit / Stop / Stop-Limit / Trailing Stop)

| Broker | Market | Limit | Stop | Stop-Limit | Trailing Stop | Take Profit | Validation |
|--------|--------|-------|------|------------|---------------|-------------|------------|
| **IBKR** | ✅ MKT → MKT | ✅ LMT → LMT | ✅ STOP → STP | ✅ STP LMT → STP LMT | ❌ Not implemented | ❌ | `OrderError` on missing limit/stop price |
| **Alpaca** | ✅ market | ✅ limit | ✅ stop | ✅ stop_limit | ✅ trailing_stop | ❌ | Raises `OrderError` / `InsufficientFundsError` |
| **CCXT** | ✅ | ✅ | ✅ | ✅ | ❌ Not mapped | ✅ take_profit | Market type routing, validation |
| **Paper** | ✅ | ✅ (pending fill) | ❌ Not implemented | ❌ | ❌ | ❌ | Slippage + commission applied |

### Order Conversion (Broker-native → Order model)
- **IBKR**: `_trade_to_order()` — converts `ib_insync.Trade` → `Order` model ⚠️
- **Alpaca**: `_create_order_model()` — converts Alpaca SDK response → `Order` model ✅
- **CCXT**: `_ccxt_order_to_order()` — converts CCXT order dict → `Order` model ✅

---

## 3. Position Sync

| Broker | `get_positions()` | `get_balance()` | `get_portfolio()` | Position → Model | Empty handling |
|--------|------------------|-----------------|-------------------|-----------------|----------------|
| **IBKR** | ✅ `ib.positions()` → Position list | ✅ `ib.accountSummaryAsync()` → dict | ✅ Account + positions → Portfolio | PositionSide.LONG/SHORT via position sign | Returns `[]` |
| **Alpaca** | ✅ `client.get_all_positions()` → Position list | ✅ `client.get_account()` → dict | ✅ Account + positions → Portfolio | PositionSide via qty sign; zero-qty filtered | Returns `[]` |
| **CCXT** | ✅ `exchange.fetch_positions()` (futures only, spot returns `[]`) | ✅ `exchange.fetch_balance()` → dict | ✅ Balance + positions → Portfolio | CCXT position → Position model via qty/entryPrice | Returns `[]` |
| **Paper** | ✅ From `_positions` dict | ✅ From `cash` + positions | ✅ Combined | Custom Position model | Returns `[]` |

### Local Caching
- **IBKR**: `_local_orders`, `_local_positions`, `_execution_reports` dicts
- **Alpaca**: `_orders`, `_open_orders_cache` dicts
- **CCXT**: No local order/position caching
- **Paper**: `_orders`, `_positions`, `_pending_orders`, `_ohlcv_history`

---

## 4. Error Handling

| Broker | Connection failures | Order failures | Auth failures | Rate limit | Market data | Circuit breaker | Retry |
|--------|-------------------|----------------|--------------|------------|-------------|----------------|-------|
| **IBKR** | `ConnectionError` | `OrderError` | Not specific | Not specific | `MarketDataError` | ❌ None | ❌ None |
| **Alpaca** | `ConnectionError` | `OrderError` | `AuthenticationError` | `RateLimitError` | `MarketDataError` | ✅ CircuitBreaker (5 errors / 60s cooldown) | ✅ `_retry_operation` (2 retries) |
| **CCXT** | `ConnectionError` | `OrderError` | Not specific | Not specific | `MarketDataError` | ❌ None | ✅ `_call_with_retry` (exponential backoff) |
| **Paper** | `ConnectionError` | ValueError | N/A | N/A | N/A | N/A | N/A |

### Error hierarchy (base.py)
```
ExchangeError
├── ConnectionError
├── OrderError
├── RateLimitError
├── AuthenticationError
├── InsufficientFundsError
└── MarketDataError
```

### Gaps
- **CCXT**: Does not map CCXT's specific auth errors to `AuthenticationError` (nets under general `ExchangeError`)
- **IBKR**: No specific `RateLimitError` or `AuthenticationError` handling
- **Alpaca**: Circuit breaker is effective but tests 3/4 async circuit-breaker tests are **broken** (see §7)

---

## 5. Factory / Broker Manager Integration

### ExchangeFactory (`factory.py`)
| Integration | Status |
|------------|--------|
| Creates CCXT exchanges (binance, okx, bybit, bitget, kraken, kucoin, gate, coinbase) | ✅ Via `_create_ccxt_broker()` |
| Creates PaperExchangeBroker | ✅ Via `paper_exchange_id` option |
| **Creates IBKR** | ❌ **Not integrated** — no `ibkr` in `_CCXT_ONLY_EXCHANGES` or capability registry |
| **Creates Alpaca** | ❌ **Not integrated** — no `alpaca` in capability registry |
| Market type validation (spot/futures/perp) | ✅ |
| Config validation | ✅ Warns on missing credentials |
| Capability detection | ✅ Via `_CAPABILITY_REGISTRY` |

### ExchangeManager (`manager.py`)
| Integration | Status |
|------------|--------|
| Register any ExchangeInterface | ✅ Accepts any `ExchangeInterface` |
| Role-based routing (primary/failover/data-only) | ✅ |
| Health checks + reconnection | ✅ |
| Aggregated portfolio across exchanges | ✅ |
| Auto-wires to factory | ❌ **Not wired** — manual `register()` calls required |

### Current wiring gap
```
[User Code] → creates brokers manually → registers with ExchangeManager
                ↓ no automated path
[ExchangeFactory] → only creates CCXT + Paper
                → IBKR & Alpaca: NO factory path
```

---

## 6. Test Coverage

| Test file | Tests | Pass/Fail | Notes |
|-----------|-------|-----------|-------|
| `tests/test_exchange/test_ibkr_broker.py` | **81 tests** | 28 ✅ / 53 ❌ | All async tests fail — missing `pytest.mark.asyncio` or `asyncio_mode=auto` config not loaded. Non-async tests (models, mappings) pass. |
| `tests/test_exchange/test_alpaca_broker.py` | **20 tests** | 16 ✅ / 4 ❌ | Same async issue. Synchronous tests (CircuitBreaker, mappings, conversions) all pass. |
| `tests/test_exchange/test_paper_broker_comprehensive.py` | **~40 tests** | ❓ Not run | Uses unittest (not pytest-asyncio issue, but extremely slow collection). |
| `tests/test_brokers.py` | **20 tests** | 20 ✅ **All pass** | Tests `quant_nanggroe.connectors` (legacy SimulatedBroker), not the new exchange interface. Light imports. |
| **CCXT broker tests** | **0 tests** | — | **No test file exists!** |

### Root cause of test failures
The `ccxt.async_support` import at module level of `ccxt_broker.py` (line 26) triggers a 60+ second blocking import that stalls pytest collection. Additionally `pytest-asyncio 1.4.0` and `anyio 4.12.1` are both installed, but `asyncio_mode=auto` in `pyproject.toml` is **not recognized** on this version, causing all async tests to error with *"async def functions are not natively supported."*

---

## 7. Broker Connectivity Matrix — Summary

| Area | IBKR | Alpaca | CCXT | Paper |
|------|------|--------|------|-------|
| **Connect** | ✅ Complete | ✅ Complete | ✅ Complete (slow import) | ✅ Trivial |
| **Disconnect** | ✅ Complete | ⚠️ State-only, no real disconnect | ✅ Complete | ✅ Trivial |
| **Market orders** | ✅ | ✅ | ✅ | ✅ |
| **Limit orders** | ✅ | ✅ | ✅ | ✅ (pending) |
| **Stop orders** | ✅ | ✅ | ✅ | ❌ |
| **Stop-limit** | ✅ | ✅ | ✅ | ❌ |
| **Trailing stop** | ❌ | ✅ | ❌ | ❌ |
| **Take profit** | ❌ | ❌ | ✅ | ❌ |
| **Position sync** | ✅ | ✅ | ✅ (futures only) | ✅ |
| **Balance sync** | ✅ | ✅ | ✅ | ✅ |
| **Portfolio** | ✅ | ✅ | ✅ | ✅ |
| **Order cancel** | ✅ | ✅ | ✅ | ✅ |
| **Order status** | ✅ | ✅ | ✅ | ✅ |
| **Error handling** | ⚠️ Partial (no auth/rate specifics) | ✅ Best (auth, rate-limit, circuit breaker) | ⚠️ Partial (generic wrapping) | N/A |
| **Factory integration** | ❌ None | ❌ None | ✅ Direct | ✅ Direct |
| **Tests** | 81 (53 async-broken) | 20 (4 async-broken) | **0** ❌ | ~40 (unittest) |
| **Live-ready** | ⚠️ Needs TWS/Gateway | ✅ Paper/live both handled | ⚠️ Needs keys; no CCXT tests | ✅ Works offline |

---

## 8. Key Recommendations

1. **Fix ccxt import bottleneck**: Move `import ccxt.async_support as ccxt` inside `CCXTBroker.connect()` (lazy import), and make `factory.py` import `CCXTBroker` lazily or via deferred import. This alone would unlock the entire test suite.

2. **Fix pytest-asyncio config**: Pin `pytest-asyncio>=0.23` (when `asyncio_mode` was introduced) or add `@pytest.mark.asyncio` to all 57 async test functions across `test_ibkr_broker.py` and `test_alpaca_broker.py`.

3. **Add IBKR & Alpaca to factory**: Register both in `ExchangeFactory` with appropriate capability entries so they can be created via the same `factory.create()` flow.

4. **Write CCXT broker tests**: Zero test coverage on a 100+ exchange adapter is a critical gap.

5. **Factory → Manager auto-wiring**: Have `ExchangeFactory.create()` optionally register with an `ExchangeManager` instance to eliminate the dead-manual `register()` dance.
