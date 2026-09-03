# ALPHA_EVIDENCE.md — Strategy Walk-Forward Evidence (scaffold, FASE 4 fills the rest)

> **Rule:** every number below is read directly from `data/walk_forward_registry.json`
> (214 keys, verified 2026-09-03). Aggregates (`avg_*`) are the arithmetic mean of that
> strategy's per-window `test_sharpe` / `test_max_dd` values in the file — computed by
> script, not hand-estimated. WinRate is NOT stored in the registry → `TBD (FASE 4)` for all rows.
> No live-trading edge is claimed: all samples below are single-market BTC-USD daily WF
> (per each entry's `description`), not tri-asset CPCV.

## Sampled entries (exact, from registry)

| Strategy | WF Sharpe (avg test_sharpe, n windows) | MaxDD (avg test_max_dd) | WinRate | Period (test_start→test_end) | Method | Verdict |
|----------|----------------------------------------|-------------------------|---------|------------------------------|--------|---------|
| kaufman_ama | +0.7143 (n=7, min −9.3603, max +10.5209) | −0.1530 | TBD (FASE 4) | 2025-04-30→2026-07-14, BTC-USD daily | WF rolling train/test | UNVERIFIED cross-asset — huge window dispersion (min −9.36), single-market only |
| multi_timeframe | +4.8678 (n=6, min −5.7323, max +11.0764) | −0.0888 | TBD (FASE 4) | 2025-07-02→2026-07-14, BTC-USD daily | WF rolling train/test | UNVERIFIED cross-asset — implausibly high avg w/ negative worst window; likely overfit |
| ema_adx | −0.8807 (n=3, min −5.7323, max +7.9502) | −0.1397 | TBD (FASE 4) | 2025-07-02→2026-05-12, BTC-USD daily | WF rolling train/test | NO EDGE on BTC WF (negative avg) |
| kalman_filter | −5.9705 (n=7, min −20.0, max +4.3172) | −0.1731 | TBD (FASE 4) | 2025-04-30→2026-07-14, BTC-USD daily | WF rolling train/test | NO EDGE on BTC WF (deeply negative avg) |
| dxy_momentum | −2.2552 (n=6, min −9.3603, max +7.9502) | −0.1626 | TBD (FASE 4) | 2025-07-02→2026-07-14, BTC-USD daily | WF rolling train/test | NO EDGE on BTC WF (negative avg) |

## Remaining strategies

| Strategy | WF Sharpe | MaxDD | WinRate | Period | Method | Verdict |
|----------|-----------|-------|---------|--------|--------|---------|
| all other 209 registry keys | TBD (FASE 4) | TBD (FASE 4) | TBD (FASE 4) | TBD (FASE 4) | TBD (FASE 4) | TBD (FASE 4) |

## How to generate / refresh (verified script names — all exist in `scripts/`)

- `scripts/run_walkforward.py` — walk-forward validation runner (writes `data/walk_forward_registry.json`)
- `scripts/run_wf_validation.py` — alternate WF validation runner
- `scripts/run_cpcv_validation.py` — combinatorial purged CV runner (writes `data/cpcv_registry.json`)
- `scripts/ensemble_walk_forward.py` — ensemble-level WF runner
- NOTE: `scripts/run_multisymbol_wf.py` does NOT exist — do not reference it.

## Cross-asset note (already verified, CANONICAL §15.6)

Per-symbol CPCV evidence lives in `data/cpcv_registry.json` (10 strategies × BTC-USD / EURUSD=X / GC=F,
14 combos each, fields `combo_profit_share` / `avg_oos_sharpe` / `min_sharpe` / `max_sharpe`).
FASE 4 must promote only strategies with worst-combo Sharpe > 0 before any live-sizing claim.
