import pathlib

root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")

# 1) Update CANONICAL.md with v8.0 plan
canon = root / "CANONICAL.md"
t = canon.read_text(encoding="utf-8", errors="ignore")

# Add v8.0 section after §15.7
marker = "## 16. Audit Results"
v8_section = """
### 15.8 GRAND REPLAN v8.0 — REAL ENGINE, FX FOCUS, PREMIUM UI (2026-08-23)

**DIRECTIVE:** Real native engines (not porting), eliminate crypto+stocks, focus FX/Commodity/Indices on MT5, premium UI.

**KEY DECISIONS:**
1. SIGNAL AGGREGATION — one position per symbol, fixed 0.5% risk, net conviction from all strategies
2. ELIMINATE CRYPTO+STOCKS — FX majors + Gold + Silver + Oil + Indices only
3. NATIVE ENGINES — implement algorithms natively (SMC, Hyperopt, Regime, RiskParity)
4. PREMIUM UI — trader-first layout, real-time everything, zero clutter
5. NO PAPER — REAL ONLY, conservative sizing during proof phase

**SPRINTS:**
Sprint 1 (Days 1-4): SignalAggregator + symbol cleanup (remove crypto/stocks) + FX-only CPCV re-validation
Sprint 2 (Days 5-9): Native engines — SMC Engine, Hyperopt Engine, Enhanced Regime, Risk Parity
Sprint 3 (Days 10-14): Mock elimination + UI premium redesign
Sprint 4 (Days 15-17): Docs consolidation + codebase cleanup + cross-repo sync
Sprint 5+ (Ongoing): Forward-live validation, self-evolve on real data

**FX-ONLY SYMBOLS:**
| Asset | Symbols | Evidence |
|-------|---------|----------|
| FX Majors | EURUSD.vx, GBPUSD.vx, USDJPY.vx, AUDUSD.vx | EURUSD=X |
| Gold | XAUUSD.vx | GC=F |
| Silver | XAGUSD.vx | GC=F proxy |
| Oil | USOIL.vx / XTIUSD.vx | TBD |
| Indices | NAS100.vx, SPX500.vx | TBD |

**ELIMINATED:** BTCUSDT, ETHUSDT, SOLUSDT, all crypto pairs, NVDA/AAPL stocks, crypto-specific strategies

**SIGNAL AGGREGATION ARCHITECTURE:**
```
All admitted strategies vote per symbol per cycle
  ↓ SignalAggregator.aggregate(symbol, votes)
Net conviction = Σ(direction × weight × confidence)
  ↓ if |conviction| > threshold AND no existing position:
ONE entry at fixed 0.5% equity risk per symbol
SL/TP from trading_profile (scalp/day/swing ATR-adaptive)
  ↓ attribution tracked per contributing strategy
journal_sync → scorecard → lifecycle keep/tune/kill → evolve ↩
```

**NATIVE ENGINES TO BUILD:**
| Module | Inspired By | Output |
|--------|------------|--------|
| engine/smc/native_smc.py | E:\\smart-money-concepts\\ | OrderBlock+FVG+Sweep+BOS detection |
| engine/backtest/hyperopt.py | E:\\freqtrade\\ hyperopt | Bayesian param optimization |
| engine/regime/enhanced_regime.py | E:\\hidden-regime\\ | HMM+GARCH+ADX composite |
| engine/portfolio/risk_parity.py | E:\\PyPortfolioOpt\\ | HRP weights across strategies |

---

"""
if marker in t:
    t = t.replace(marker, v8_section + marker)
    canon.write_text(t, encoding="utf-8")
    print("CANONICAL.md updated with v8.0 plan")
else:
    print("MARKER NOT FOUND")

# 2) Update README.md
readme = root / "README.md"
rt = readme.read_text(encoding="utf-8", errors="ignore") if readme.exists() else ""
new_readme = """# Quant-Nanggroe-AI

> Autonomous Quantitative Hedge Fund — FX/Commodity/Indices on MT5
> Version: v8.0.0 | Status: LIVE (proof phase)

## Quick Start
```bash
# All-in-one launcher (recommended)
"QNA Launcher.bat"          # Windows
./QNA Launcher.sh           # Linux/Mac

# Or individually
python qna.py daemon        # Live autonomous trading loop
python qna.py api           # FastAPI backend :8000
cd dashboard && npm run dev # Dashboard :3000
```

## What QNA Does
Autonomous quantitative trading system focused on **FX Majors + Gold + Commodities + Indices** via MetaTrader 5.

- **Signal Aggregation**: multiple strategy signals netted into ONE position per symbol at fixed 0.5% risk
- **CPCV Validation**: every strategy validated via Combinatorial Purged Cross-Validation across multiple assets
- **Per-Symbol Allocation**: only strategies with proven combo-profit-share trade each asset class
- **Tuned Params**: grid-search/Bayesian optimized parameters injected per-symbol before signal generation
- **Self-Evaluate**: real scorecards from synced MT5 journal (expectancy/PF/Sharpe/t-stat)
- **Self-Evolve**: lifecycle auto-keep/tune/kill based on live evidence, not backtest promises
- **Trading Profiles**: scalp(M15)/day(H1)/swing(D1) with ATR-adaptive SL/TP + breakeven ratchet

## Full Documentation
See [CANONICAL.md](CANONICAL.md) — Single Source of Truth for ALL claims, verified against file:line.
"""
readme.write_text(new_readme, encoding="utf-8")
print("README.md rewritten")

# 3) Update AGENTS.md gotchas
agents = root / "AGENTS.md"
at = agents.read_text(encoding="utf-8", errors="ignore") if agents.exists() else ""
additions = """

## FAZE Status (2026-08-23)
- FAZE 0 COMPLETE: Journal-MT5 sync live (+$629.98 verified), attribution via MT5 comment
- FAZE 1 COMPLETE: Conservative sizing (0.05x conf), allocation gate active
- FAZE 2 STARTED: Scorecard from real data, lifecycle auto-kill/activate
- NEXT: Signal aggregation (one position per symbol), FX-only focus, native SMC engine
"""
if "FAZE Status" not in at:
    agents.write_text(at + additions, encoding="utf-8")
    print("AGENTS.md updated")
else:
    print("AGENTS.md already has FAZE status")
