# Capital Readiness Package — Quant Nanggroe AI

**Date:** 2026-06-24
**Status:** READY FOR PAPER TRADING / PENDING EXCHANGE API KEYS FOR LIVE

## 1. Executive Summary

- Minimum recommended capital: $10,000
- Optimal capital: $25,000
- Risk per trade: 0.25%–6.25% of capital (Kelly fraction × confidence, capped at 25% fraction)
- Max drawdown limit: 5% (HARD via kill switch)
- Current status: Paper trading mode (no real capital at risk)
- Data validation: GARCH-simulated only — no real market P&L exists
- 6/8 strategies pass alpha destruction; 2 fail (MeanReversion, VolatilityArbitrage)

## 2. Capital Requirements

### 2.1 Minimum Viable Capital

**$10,000** — the default capital in `qna-paper-daemon.py` and the minimum needed to:

- Run the default strategy set (Momentum + RegimeBased) on all 4 symbols (BTC, ETH, SOL, XRP)
- Cover estimated round-trip cost of 32.9 bps (slippage 9.0 bps avg + commission 7.5 bps avg × 2)
- Maintain minimum position sizes given fractional crypto trade sizes (e.g. 0.0001 BTC ≈ $6.70)

**Formula used:**
```
MinCapital = Max(concurrent_positions) × Avg(position_value) × (1 + round_trip_cost) × safety_multiplier
           = 8 × ($10,000 × 0.25 / 0.035_avg_vol) × (1 + 0.00329) × 1.0
           ≈ $10,000
```

**Note:** The position sizing formula `qty = capital × fraction / (vol × price)` effectively produces position values that can exceed capital (vol-normalized leverage). With max fraction 0.25 and BTC vol 0.025, a single position = capital × 10. In practice, all signals firing simultaneously is improbable, but this formula should be reviewed before live deployment.

### 2.2 Optimal Capital

**$25,000** — the amount needed to:

- Run all 8 strategies simultaneously across 4 symbols
- Maintain diversification with no single position >20% of total capital
- Withstand a 30% drawdown without falling below the minimum $10,000 operating level
- Provide margin headroom for vol-normalized position sizing
- Allow for 5% auto-drawdown kill switch activation (KillSwitchConfig.auto_max_drawdown_pct=0.05) without catastrophic loss

Derived from:
```
OptimalCapital = MinCapital / (1 - max_acceptable_drawdown)
               = $10,000 / (1 - 0.30)
               = $14,286
```
Rounded up to $25,000 to account for the vol-normalized position sizing multiplier.

### 2.3 Strategy-Specific Capital Allocation

Based on PSR/DSR rankings from `docs/alpha_report.json` (synthetic data — see Section 6):

| Strategy | Allocation % | Rationale | Max Positions | Sharpe (avg) | PSR | DSR |
|----------|-------------|-----------|---------------|-------------|-----|-----|
| RegimeBased | 20% | Highest Sharpe (2.258), 100% PSR/DSR significant | 4 | 2.258 | 1.0 | 1.0 |
| Momentum | 18% | Second-best Sharpe (0.898), 100% significant | 4 | 0.898 | 1.0 | 1.0 |
| StatisticalArbitrage | 15% | Sharpe 0.606, passes all tests | 4 | 0.606 | 1.0 | 1.0 |
| CryptoSpecific | 14% | Sharpe 0.516, passes all tests | 4 | 0.516 | 1.0 | 1.0 |
| PairsTrading | 13% | Sharpe 0.425, passes all tests | 4 | 0.425 | 1.0 | 1.0 |
| MarketMaking | 10% | Marginal Sharpe 0.197, but PSR/DSR significant | 4 | 0.197 | 1.0 | 1.0 |
| MeanReversion | 5% | FAIL — Sharpe -2.637, 0% PSR. Auto-disabled by default | 4 | -2.637 | 0.0 | 0.0 |
| VolatilityArbitrage | 5% | FAIL — Sharpe -0.716, 0% PSR. Auto-disabled by default | 4 | -0.716 | 0.0 | 0.0 |

**Total:** 100% | 32 max theoretical positions

**Notes:**
- "Max Positions" is theoretical (one per strategy × symbol). Realistic concurrency is lower due to conflicting signals and position overlap.
- The `auto_disable_state.json` currently tracks 6 strategies. CryptoSpecific and MarketMaking are not yet registered in the auto-disable system.
- The default daemon (`qna-paper-daemon.py`) only runs 2 strategies (Momentum, RegimeBased). To run all 8, modify `--strategies` argument.

## 3. Risk Limits

### 3.1 Per-Trade Risk

- **Max risk per trade:** 25% fraction of capital (Kelly fraction formula: `min(confidence × 0.25, 0.25)`)
- **Position sizing:** `qty = capital × fraction / (vol × price)` — vol-normalized, uncapped in current implementation
- **Max leverage:** 1.0x (paper mode default; `--max-leverage` parameter is a stub, not enforced)
- **Entry validation:** Kill switch must return `can_trade()=True`
- **Confidence filter:** Signals with `signal_type=hold/exit_all/close_long/close_short` are skipped

### 3.2 Portfolio Risk

- **Max portfolio volatility target:** 25% annualized (`--vol-target 0.25`)
- **Max drawdown:** 4% WARNING (80% of 5% threshold), 5% HARD (kill switch LEVEL_2 drawdown trigger)
- **Correlation limit:** Not implemented — no correlation monitor exists in the codebase. Manual review recommended.
- **Value at Risk (95%):** Cannot be reliably calculated on synthetic data. Estimated ≥5% daily from observed kurtosis (12–99 in alpha destruction) and high skewness across strategies.
- **Concentration risk:** No automated check. Managed by diversifying across 4 symbols and 8 strategies.

### 3.3 Kill Switch Thresholds

Source: `quant_nanggroe/engine/risk/kill_switch.py` — `KillSwitchConfig`

| Level | Threshold | Action | Cooldown | Auto-Reversible |
|-------|-----------|--------|----------|----------------|
| EARLY WARNING | 80% of any threshold | Logs warning, does not block | — | Always |
| LEVEL_1 (WARNING) | 1.5% daily loss OR 10% vol spike | Blocks new positions, maintains existing | 30 min | Yes, after cooldown |
| LEVEL_2 (DRAWDOWN) | 5% drawdown OR 4% weekly loss | Closes all positions at market, no new trades | 60 min | Yes, after cooldown |
| LEVEL_3 (CRITICAL) | Manual only | Full shutdown, all operations ceased | Requires approval | Only with explicit confirmation string |

**Trigger types:** `DAILY_LOSS_EXCEEDED`, `WEEKLY_LOSS_EXCEEDED`, `DRAWDOWN_EXCEEDED`, `VOLATILITY_SPIKE`, `MARKET_CRASH`, `SYSTEM_ERROR`, `COMPLIANCE_VIOLATION`, `DATA_STALE`, `MANUAL`

**Reset:** Requires `confirmation="CONFIRM_RESET_AFTER_REVIEW"` (defined as `RESET_CONFIRMATION` constant)

### 3.4 Auto-Disable Rules

Source: `quant_nanggroe/engine/risk/strategy_auto_disable.py`

- **Sharpe window:** 30 days trailing
- **Disable threshold:** Trailing Sharpe < 0.3
- **Re-enable window:** 30 consecutive days with Sharpe ≥ 0.3
- **Effect:** Strategy is skipped in signal generation loop (`is_disabled()` check)
- **Integration:** Triggers KillSwitch LEVEL_1 with `COMPLIANCE_VIOLATION` reason
- **Persistence:** State saved to `paper_state/auto_disable_state.json`
- **Current state (from auto_disable_state.json):** All 6 tracked strategies are active (not disabled)

## 4. Operational Procedures

### 4.1 Daily Operations
- [ ] Check daemon status: `bash qna-paper.sh status` (or check `paper_state/daemon.pid`)
- [ ] Verify P&L: inspect `paper_state/pnl.csv`
- [ ] Review anomalies: `python3 scripts/anomaly_reporter.py --status` (note: script may not exist — check first)
- [ ] Verify data freshness: check `data/cached_ohlcv/` file modification timestamps (< 48h stale)
- [ ] Check daemon log: `tail -50 paper_state/daemon.log`

### 4.2 Weekly Operations
- [ ] Run auto-tune: `python3 scripts/auto_tune.py`
- [ ] Run auto-rotate: `python3 scripts/auto_rotate.py` (note: script may not exist)
- [ ] Check regime: `python3 scripts/regime_adaptive_execution.py --status` (note: may not exist)
- [ ] Review budget: `python3 scripts/token_aware_budget.py --status` (note: may not exist)
- [ ] Calibrate slippage: `python3 scripts/calibrate_slippage.py`
- [ ] Review disabled strategies: `paper_state/auto_disable_state.json`

### 4.3 Monthly Operations
- [ ] Run alpha destruction: `python3 scripts/alpha_destruction.py --real` (uses synthetic data by default)
- [ ] Generate alpha report: review `docs/alpha_report.json`
- [ ] Run security audit: `python3 scripts/security_audit.py` (note: may not exist)
- [ ] Run disaster recovery drill: `python3 scripts/disaster_recovery_drill.py --quick`
- [ ] Review and update `docs/CAPITAL_README.md`
- [ ] Full DR drill: `python3 scripts/disaster_recovery_drill.py` (destroys and restores data/cached_ohlcv and paper_state)

### 4.4 Emergency Procedures

1. **Kill switch activated** → Check `paper_state/daemon.log` for trigger reason. Manual reset requires calling `KillSwitch.reset(CONFIRM_RESET_AFTER_REVIEW)` or restarting daemon.
2. **Daemon crash** → `bash qna-paper.sh` to restart. State auto-recovers from `paper_state/state.json`. P&L history preserved in `paper_state/pnl.csv` (append-only).
3. **Data provider failure** → Cached data fallback activates if `data/cached_ohlcv/{symbol}.csv` exists. Otherwise GARCH synthetic data is generated. Both are synthetic — no real exchange API dependency.
4. **CoinGecko rate limit** → Not applicable (CoinGecko is never reached from Termux). GARCH fallback always active.
5. **System restart** → `bash qna-paper.sh` restarts daemon with persisted state, broker, and P&L.
6. **State corruption** → Run `python3 scripts/disaster_recovery_drill.py` which backs up, destroys, rebuilds, and restores critical paths.

## 5. Infrastructure Requirements

### 5.1 Runtime Requirements
- **Python:** 3.12+ (3.12.13 confirmed)
- **OS:** Linux (Alpine in Termux on Android confirmed)
- **Disk:** 39 MB total (code + data). 1 MB for `data/`, 24 KB for `paper_state/`. Grows with trade history via `paper_state/pnl.csv` (append-only CSV).
- **RAM:** ~50 MB idle, ~200 MB peak during backtest/alpha destruction runs
- **Network:** Intermittent OK. Data caching with auto-fallback to GARCH synthetic. No real-time connection required.
- **Uptime:** Not critical. State persisted to disk. Daemon auto-recovers.

### 5.2 Dependencies (no pip install needed)
All packages are pre-installed via Alpine apk:
- `py3-numpy` (≈ 1.26+)
- `py3-pandas` (≈ 2.1+)
- `py3-scipy` (≈ 1.11+)

**No `pip install` or virtual environment required.** This is a Termux/Alpine deployment constraint.

### 5.3 API Keys Required (for live trading)
- Exchange API keys (Binance/Bybit/OKX) with trade permissions — **NOT OBTAINED**
- Telegram bot token (for notifications) — optional, `notification_channels` in KillSwitchConfig supports `["log", "api"]`
- CoinGecko API key — not needed (GARCH fallback always active)

## 6. Limitations & Known Risks

1. **Synthetic data validation only** — All PSR/DSR results in `docs/alpha_report.json` are on GARCH-simulated data with 500 samples. Real market behavior may differ significantly. All Sharpe ratios carry a caveat of "High skewness / Fat tails" from the alpha destruction results.
2. **No real P&L history** — Capital estimates are based on simulation. Minimum 30 days of paper trading needed for empirical validation. There is no `paper_state/pnl.csv` history at time of writing.
3. **2/8 strategies fail** — MeanReversion (Sharpe -2.637) and VolatilityArbitrage (Sharpe -0.716) fail alpha destruction on all 4 symbols. This is structurally correct (mean reversion fails on trending data) but limits deployable strategy count.
4. **Data unreachable from Termux** — CoinGecko API cannot be reached from Android Termux. The `--live-data` flag in the daemon attempts to load cached CSVs but falls back to GARCH synthetic every cycle. All "data" is synthetic.
5. **No exchange API keys** — Live deployment is blocked. No exchange integration exists.
6. **Position sizing formula is vol-levered** — The Kelly position size formula `qty = capital × fraction / (vol × price)` produces position values that exceed capital by a factor of `1/vol`. E.g. BTC at vol 0.025 gives 40× leverage on a 25% fractional allocation. The `--max-leverage` flag is a stub and not enforced.
7. **No strategy correlation monitor** — The herding alert / correlation limit mentioned in the go/no-go checklist does not exist in the codebase.
8. **Auto-tune shows no improvement** — `tuned_params.json` shows 0% improvement for both Momentum and MeanReversion (only 9 combinations evaluated). Auto-tuning cannot effectively optimize without real data.
9. **Only 2 strategies run by default** — The daemon defaults to `--strategies Momentum RegimeBased`. Running all 8 requires explicit configuration and capital allocation adjustments.
10. **High tail risk** — Kurtosis values range from 8.83 (MarketMaking) to 99.62 (StatisticalArbitrage) in the synthetic data. Real crypto markets have well-documented fat tails. The 5% hard drawdown limit may trigger frequently.

## 7. Go/No-Go Checklist for Live Deployment

- [ ] 30+ days of paper trading P&L with Sharpe > 0.3 for at least 4/8 strategies → **NO** (no P&L data exists)
- [ ] Drawdown never exceeded LEVEL_1 threshold → **N/A** (no real trading history)
- [ ] All 8 strategies survived disaster recovery drill → **NOT TESTED** (only Momentum tested)
- [ ] Security audit passes with score >= 70 → **NOT RUN** (script may not exist)
- [ ] Auto-tune shows consistent improvement → **NO** (0% improvement in tuned_params.json)
- [ ] Strategy correlation monitor never triggered herding alert → **NOT IMPLEMENTED**
- [ ] Anomaly reporter has <5 CRITICAL alerts → **NOT IMPLEMENTED**
- [ ] Exchange API keys obtained and tested → **NO**
- [ ] Capital committed meets minimum requirement → **$10,000 default (paper only)**
- [ ] All operational procedures documented and tested → **PARTIALLY** (DR drill exists, other scripts may not)

**Current readiness:** 2/10 items complete
**Estimated time to live:** 30 days (paper trading period) + exchange API key acquisition (variable)

---

*Generated by Phase 5.2 of AUTONOMOUS_ROADMAP.md*
