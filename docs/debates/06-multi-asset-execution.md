# Debate Record: Theme 6 — Multi-Asset & Multi-TF Execution

**Date:** 2026-06-28
**Presiding:** PM (w: 2.0, Veto Strategy)
**Council:** QT (w: 1.2), QR (w: 1.5), CRO (w: 2.0, Veto Halt)
**Questions:** Q70-Q72

---

## Round 1: Initial Stances

### PM
- **Multi-asset:** Yes — forex 60%, crypto 25%, saham 15%. Max 3 positions/asset class until $50k AUM.
- **Multi-TF:** Max 2 (swing 4H/D1 directional + intraday 15m/1H execution). No scalping. Higher TF wins conflicts, size cut 50%.
- **Stops:** Structure-based (HH/HL) for swing, ATR for intraday. Breakeven +1R, trail +1.5R. Portfolio -8% monthly hard floor.
- **Gate:** RegimeBased 20 trades live paper Sharpe >1.0.
- **Veto:** >40% any asset, scalping, ATR-only without structure, >2 TFs, multi-asset before validation.

### QT
- **Asset classes:** Crypto 24/7 slippage, forex tight spreads 24h, saham market hours. Fill logic must be asset-aware.
- **TFs:** Scalp + swing don't mix. Intraday + swing coherent in separate sub-accounts. Sub-account separation mandatory.
- **Stops:** ATR trailing (2.5x) only one that survives live crypto. HH/HL destroyed in chop. Breakeven = psychological crutch.
- **Priority:** Fix RegimeBased OOS → ATR trailing → sub-account separation.

### QR
- **Research:** Multi-asset factors are asset-class specific. Expanding before fixing core pipeline is reckless.
- **TFs:** Lower TF → lower Sharpe, higher overfitting. Hsu (2020): mixing swing + intraday is documented overfitting trap. Single TF only.
- **Stops:** ATR trailing strongest empirical backing (Chande 1995, Kaufman 2013, Kaminski & Lo 2007). HH/HL lacks support. Breakeven Sharpe-negative.
- **Priority:** Fix OOS ≥3/8 pass → ATR volatility regime filter → cross-asset RegimeBased extension.

### CRO
- **Risk:** Correlation breakdown critical threat. 3x broker ecosystems = 3x failure surface. Per-asset risk budgets mandatory.
- **TFs:** Phantom netting — multiple TFs same direction = 3x exposure. Liquidation cascade risk. One TF direction per symbol.
- **Stops:** ATR superior — adapts to regime. HH/HL structurally lagging. Breakeven destroys expectancy. Max single-trade ≤ 1% equity.
- **Gate:** Per-asset risk budgets, correlation regime detector live, cross-asset margin monitoring, kill switch per asset, 60-day paper per asset.

---

## Round 2: PM Final Decision

### Multi-Asset Timing (Phased Gates)
- **Phase 1:** Single-asset (forex first) until RegimeBased passes ≥3/8 OOS AND 20 live paper trades Sharpe >1.0
- **Phase 2:** Second asset approved with per-asset risk budgets + 30-day paper (compromise from CRO's 60)
- **Phase 3:** Full multi-asset only after correlation regime detector and cross-asset margin monitor live
- No asset added until previous phase conditions met

### Multi-TF Approach
**Single TF (swing 4H/D1) for all execution.** Intraday (1H) possible per-asset after 60-day validation in separate sub-account. High TF (D1) used only as regime filter for direction — never simultaneous positions. One TF direction per symbol enforced by CRO's monitoring.

**Scalping permanently vetoed.**

### Stop Type
**ATR trailing (2.5x) as sole primary stop mechanism** across all timeframes and asset classes.
- HH/HL demoted to **confirmation overlay only** — never primary
- **Breakeven eliminated** entirely (3-0 council opposition, Sharpe-negative per QR, expectancy-destroying per CRO, psychological crutch per QT)
- Hard stop at entry for every position (CRO requirement)
- Max 1% equity per trade

### Priority Ranking
1. Fix RegimeBased OOS validation pipeline — target ≥3/8 pass
2. Implement ATR trailing (2.5x) — replace all HH/HL and breakeven logic
3. Deploy single TF swing (4H/D1) on paper — validate 20 trades minimum
4. Establish per-asset risk budgets with hard stop at entry — CRO prerequisite
5. Phase 2: second asset with per-asset budgets + 30-day paper in sub-account
6. Build correlation regime detector and cross-asset margin monitoring
7. Phase 3: full multi-asset rollout

### Vetoes
1. Scalping in any form
2. >2 TFs per symbol (effectively: any multi-TF in same account)
3. HH/HL as primary stop mechanism
4. Breakeven stops (all types)
5. Multi-asset before single-asset RegimeBased validation
6. >40% allocation to any single asset class
7. ATR-only stops without structure confirmation overlay

---

**Status: COMPLETE**
**Next:** Theme 7 — Plenary: Sub-Agent Orchestration & 100/100 Gaps (ALL roles)
