# Strategy Runbook: RegimeBased

**Version:** 1.0
**Status:** ACTIVE (paper phase)
**Last Updated:** 2026-06-28

## Overview

RegimeBased is the sole surviving strategy after Hedge Fund Council Theme 1 vote.
It uses a regime detection heuristic (SMA crossover + volatility clustering) to identify
market regimes and applies regime-adaptive Kelly sizing.

## Detection Logic

```
SMA_21 > SMA_63 AND vol_21 < 1.5%  → bull_trend  (confidence: 0.5 + price_distance * 5, capped 0.8)
SMA_21 < SMA_63 AND vol_21 > 1%    → bear_trend  (confidence: 0.5 + vol * 10, capped 0.8)
vol_21 > 2.5%                        → high_volatility (confidence: 0.5 + vol * 8, capped 0.8)
else                                 → sideways (confidence: 0.5)
```

## Risk Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Kelly fraction | 0.25 × risk_multiplier (0.4–1.0) | StrategyConfig |
| ATR trailing stop | 2.5× ATR, trail-only (never widen) | Council Theme 6 |
| Hard stop at entry | 3.0× ATR | P1-26 |
| Max position | 10% of portfolio | MAX_POSITION_SIZE_PCT |
| Max daily loss | 1% per asset | P1-26 |
| Drawdown limit | 15% total | MAX_DRAWDOWN_PCT |
| OOS Sharpe (fixed WFA) | -0.335 | alpha_destruction.py |

## Execution

- **Timeframe:** Daily (D1 bars from Alpha Vantage / cached CSV)
- **Assets:** BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT
- **Sizing:** Volatility-targeted Kelly (vol_target=0.25, max leverage=1.0)
- **Stop:** 2.5× ATR trailing stop (hardened at 3.0× from entry)
- **Signal direction:** Determined by regime (bull=buy, bear=sell, sideways=hold)

## Monitoring

- **Regime state:** Written to `regime_state.json` each cycle
- **P&L attribution:** Logged per-symbol to `pnl_attribution.csv`
- **Audit trail:** `audit_YYYYMMDD.json` via AuditLogger
- **Kill switch:** Activates LEVEL_1 on stale data, LEVEL_2 on drawdown breach
- **Watchdog:** `qna-watchdog.py` auto-restarts daemon and refreshes data

## Council Decisions Applied

1. Kill 7/8 strategies — ONLY RegimeBased active (Theme 1 CIO veto)
2. No arxiv/ML research until 30d validation (Theme 2 PM veto)
3. No dragable UI — fixed grid only (Theme 3 PM veto)
4. ATR 2.5× as sole primary stop, no HH/HL/breakeven (Theme 6, 3-0 vote)
5. No monetary auto-fix in paper phase (Theme 5 Ops Manager decision)
6. Per-asset budgets + hard stop at entry (P1-26)
7. Chinese Wall: SIGNAL→RISK→EXECUTION (P1-11)

## Reverting to Synthetic

```bash
python3 scripts/qna-paper-daemon.py --interval 3600 --capital 10000
```

## Production Gate Conditions

1. 30-day paper run without KillSwitch breach
2. OOS Sharpe > -0.2 (less negative than current -0.335)
3. Compliance sign-off (runbook review + security audit)
4. Per Kim: Alpaca paper API keys wired
