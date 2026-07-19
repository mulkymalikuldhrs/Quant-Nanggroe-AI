# Dhaher Hedge Fund — Session Handoff (19 Juli 2026)

## Final State — All Systems

### Live Pipeline
- **Wyckoff Volume Spread** (Sharpe 3.02) ✅ — strategi utama
- **MeanReversion Stochastic** (Sharpe 1.98) ✅ — second opinion
- **MTF Framework** — 5 trading styles: intraday1/2, swing1/2, scalping
- **Multi-Pair Scanner** — 37 pairs, spread filter, SL jilat protection
- **Market Context** — DXY, FX Strength (live), COT/Yield/News (subagent)
- **Risk Module** — Kelly, Monte Carlo, Adaptive sizing, Composite score
- **Backtest → Walk-Forward → Gate pipeline**

### 9 Strategies in Registry
| Rank | Strategy | Return | Sharpe | Gate | Status |
|------|----------|--------|--------|------|--------|
| 1 | Wyckoff Volume Spread | +153% | 2.685 | ✅ | LIVE |
| 2 | Mean Reversion (Stoch) | +116% | 1.982 | ✅ | LIVE |
| 3 | AMDX Market Profile | +19% | 1.160 | ❌ | Standby |
| 4 | Algebra Z-Score | +23% | 0.790 | ❌ | Standby |
| 5 | MSNR | +0.6% | 0.486 | ❌ | Fixing |
| 6 | EMA+ADX | -65% | 0.878 | ❌ | Standby |
| 7 | SMC | -112% | 1.525 | ❌ | Fixing |
| 8 | Quarterly Theory | Error | - | ❌ | Fixing |
| 9 | Fibonacci | 0% | 0 | ❌ | Standby |

### Multi-Pair Universe (37 pairs)
- Majors: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD
- Minors: EURGBP, EURJPY, EURCHF, EURAUD, etc (all cross pairs)
- Exotics: XAUUSD, XAGUSD, BTCUSD, etc
- Filter: max spread 25p major, 35p minor, 50p exotic + SL jilat list
- Weekend: 6 tradable. Weekday: ~20+ tradable

### Key Commands
```bash
# Run hedge fund
cd /e/trading && PYTHONPATH="" python hedge_fund.py

# Run MTF multi-pair
cd /e/trading && PYTHONPATH="" python hedge_fund_mtf.py

# Run backtest all strategies
cd /e/trading && PYTHONPATH="" python master_backtest.py

# Run full optimizer
cd /e/trading && PYTHONPATH="" python full_optimizer.py

# Run multi-pair scanner
cd /e/trading && PYTHONPATH="" python -c "from multi_pair_scanner import scan_all_pairs; import MetaTrader5 as mt5; mt5.initialize(); scan_all_pairs(); mt5.shutdown()"

# Start MT5 terminal
/c/Program\ Files/MetaTrader\ 5/terminal64.exe /login:372044706 /password:@15September /server:ValetaxIntl_Live-2
```

### Files Created This Session
- E:/trading/strategy_registry.py — 9 strategies
- E:/trading/risk_module.py — Kelly, Monte Carlo, adaptive risk
- E:/trading/mtf_framework.py — 5 trading styles
- E:/trading/market_context.py — DXY, FX strength
- E:/trading/multi_pair_scanner.py — 37-pair scanner
- E:/trading/hedge_fund_mtf.py — MTF multi-pair executor
- E:/trading/backtest_pipeline.py — backtest + walk-forward + gate
- E:/trading/master_backtest.py — test all strategies at once
- E:/trading/full_optimizer.py — optimize all strategy params
- E:/trading/wyckoff_optimizer.py — Wyckoff parameter optimization
- E:/trading/research/ — 10 reports, 197+ resources

### Cron Jobs
- hedge-fund-runner: every 30min → Wyckoff + MeanRev → MT5

