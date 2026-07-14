# QUANT-NANGGROE-AI — MASTER PROMPT (Honest Version)

## MISSION
Build a quant research framework that can evolve toward hedge fund grade. Be honest about gaps. Never claim "done" when it's not.

## HONEST SCORE: 15/100 toward Hedge Fund Grade

We built a quant research framework with:
- 106 strategy implementations (basic, not production-quality)
- API framework (defined, not stress-tested)
- UI pages (exist, partially wired)
- Kill switch (code path wired, not tested with real flow)

This is valuable. It's not a hedge fund.

## WHAT'S REAL (Verified)
- 106 strategies: all importable, all have generate_signal()
- 10 symbols backtested: BTC, ETH, SOL, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD
- 17 KEEP strategies: positive Sharpe on majority of symbols
- API endpoints: defined and importable
- UI pages: exist with basic rendering
- Kill switch: wired in code path (ExecutionManager)

## WHAT'S NOT REAL (Honest Gaps)
- Strategies are 50-150 lines, not production-quality
- Backtest uses yfinance historical, not live data
- No slippage/market impact modeling
- No VaR/CVaR/portfolio optimization
- No real execution engine (paper only)
- No compliance, no audit trail
- No walk-forward with proper cross-validation
- Kill switch never tested with real money flow
- MT5 configured but terminal not running

## PRIORITY 1: Fix the Foundation
1. **Proper backtest engine** — slippage, costs, fill simulation
2. **Risk models** — VaR, CVaR, stress testing
3. **Portfolio optimizer** — Kelly sizing, risk parity
4. **Walk-forward with cross-validation**

## PRIORITY 2: Build Execution
5. **Real data pipeline** — live feeds, not just historical
6. **Execution engine** — smart order routing, TCA
7. **Position management** — partial fills, rollovers

## PRIORITY 3: Add Infrastructure
8. **Real-time monitoring** — live P&L, risk dashboards
9. **Compliance** — regulatory reporting
10. **Audit trail** — every decision logged

## VERIFICATION STANDARD
Every claim must be backed by REAL tool output.
"Done" means: tested, verified, documented, production-ready.
"Almost done" means: not done.

## RULE
When unsure, say "I don't know" or "this needs more work".
Never claim "hedge fund grade" until it actually is.
