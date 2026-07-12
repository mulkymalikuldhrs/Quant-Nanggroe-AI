# Changelog — Quant Nanggroe AI (QNA)

## [2026-07-12] — Hedge-Fund Audit + C:→D: Merge (v0.9.2)

### Fixed
- **Kelly criterion**: fractional methods (HALF/FRACTIONAL/ADAPTIVE) no longer silently halved; ADAPTIVE_KELLY no longer crashes
- **Diversification score**: degenerate 0 for both corr=1 and corr=-1 → fixed with correlation-based normalization
- **Order→broker bridge**: ExecutionManager never reached ExchangeManager → fixed via ExchangeBrokerAdapter
- **Broker sell error msg**: test matched wrong regex
- **Test half-kelly assertion**: encoded old bug (expected ≤0.1 instead of 0.2)

### Added
- **Crucix OSINT package** (packages/crucix): 27-source intelligence terminal, ACLED conflict, ADSB flight tracking
- **Agentic-legacy archive** (packages/agentic-legacy): preserved for reference
- **nginx/nginx.conf**: production reverse proxy (WebSocket, SSL, security headers)
- **Comprehensive Makefile**: 29 targets (was 3) — test-cov, typecheck, security, docker, db migrations, CI pipeline
- **Agentic_AI_System_Prompts.docx**: 1.3MB system prompt document
- `.dockerignore`, `DOC_GAPS.md`, `GRAPHIFY.md`, `mock-data.ts`, GitHub CI workflow

### Removed
- `C:\Users\Hi\Quant-Nanggroe-AI` stale clone (179MB) — merged unique assets to D: worktree

### Changed
- Consolidation: C:→D: merge commit `42b3b5a`
- Makefile: 101-line build system replaces 19-line stub

### Tests
- 468 hedge-fund-critical tests: 0 failed (API, risk, kelly, correlation, brokers, pipeline)
- 265 targeted regression: 0 failed (risk kritis post-fix)

## [2026-06-22] — Documentation Consolidation (v0.9.1)

### Added
- Consolidated docs into `DOCUMENTATION.md`.
- Generated architecture diagram via `scripts/graphify.py`.
- Added `FILE_INDEX.md` with concise repository file list.
- Updated `README.md` to link to consolidated docs and file index.

### Fixed
- Updated `docs/architecture.md` (graphify output) to reflect latest components.


## [2026-06-22] — Production Hardening + 15 Strategies (v0.9.0)

### Added
- **6 new strategies** (total 15): SMC, ICT, S/R, SnD, Wyckoff, COT, Fundamental
- **COT Data Provider** (`engine/data/cot_provider.py`): CFTC fetcher, COT index (0-100), commercial divergence detection
- **Economic Calendar** (`engine/data/economic_calendar.py`): event provider with impact scoring, surprise detection, market risk analysis
- **Multi-Timeframe Framework** (`engine/strategy/multi_timeframe.py`): HTF (D1) trend → MTF (H1) confirm → LTF (M5) entry alignment
- **Auto Fine-Tuning** (`engine/backtest/auto_tune.py`): grid search + walk-forward validation, auto-deploy best params
- **Adaptive Strategy Selector** (`engine/strategy/strategy_selector.py`): regime→strategy compatibility matrix, rolling Sharpe tracking, weighted execution
- **Strategy API routes** (`api/routes/strategies.py`): 5 endpoints (list, detail, toggle, selector, toggles)
- **Portable launcher** (`qna.sh`): start/stop/status/dashboard/backtest on Linux/Mac/Windows/Termux
- **Trailing Stop** (`engine/risk/trailing_stop.py`): 2% activation, 1% trail from peak

### Fixed
- **Strategy lifecycle**: changed class-level `_cum_wins/_cum_losses` to `PrivateAttr` (was shared across instances)
- **Kill switch thresholds**: 0.8%/2.5%/10% (was 1.5%/4%/5% — too loose)
- **Emotional lockout**: 0.8% from peak (was 5%)
- **avg_loss calculation**: uses `total_losses` instead of `total_pnl`
- **httpx timeouts**: connect=5s prevents hanging on blocked endpoints
- **Daemon persistence**: PPID=1 via `setsid`, survives TTY detach
- **Wyckoff numpy array ambiguity**: fixed `close[-N:] - close[0]` → `close[-1] - close[-N]`
- **DataFrame symbol access**: `data.get("symbol")` → `str(data["symbol"].iloc[-1])` in all 6 pattern strategies

### Infrastructure
- **SSH relay routing chain**: direct (5s) → WARP HTTP proxy (3s) → SSH relay (15s)
- **WARP integration**: Cloudflare API registration, auto-detect OS, config generation
- **Portable config** (`qna_config.py`): auto-detects OS/paths/Python/SSH
- **Secret management**: all API keys → env vars (QNA_TELEGRAM_BOT_TOKEN, etc.)
- **HTTP proxy**: WARP HTTP proxy (172.16.0.1:2480) auto-detected via socket check

### Strategy Selector — Regime Mapping
| Regime | Best Strategies |
|--------|----------------|
| Bullish | Momentum, CryptoSpecific, Wyckoff |
| Bearish | Momentum, RegimeBased, Wyckoff |
| Ranging | MeanReversion, MarketMaking, S/R |
| Volatile | VolatilityArbitrage, Fundamental, CryptoSpecific |

### Architecture
```
Data Layer → Strategy Layer → Analysis Layer → Decision Synthesis → Risk → Execution → API/UI
```

## [2026-06-21] — Exchange Layer Unlocked + Production Bridge (v0.8.0)

### Added
- Exchange type modules: market, orders, positions (pydantic v1 compatible)
- All 8 exchange clients import: Binance, Bybit, OKX, Coinbase, KuCoin, Bitget, Kraken, Gate
- Production Bridge V2: 6 components with SyncPaperBroker
- Full pipeline verified: BULL regime → Momentum → risk filter → execution

## [2026-06-20] — Foundation (v0.7.0)

### Added
- Core engine architecture with 8 strategies
- Backtest system with SQLite persistence
- Regime detection: HMM, correlation, macro, volatility, ensemble
- Screener system: macro, fundamental, intermarket, sentiment
- Next.js dashboard with Recharts
- Flask web interface
- 45 MACD/SMA backtest-passed strategies deployed
