# ALPHA_EVIDENCE.md — Strategy Walk-Forward Evidence (scaffold, FASE 4 fills the rest)

> **Rule:** every number below is read directly from `data/walk_forward_registry.json`
> (214 keys, verified 2026-09-03). Aggregates (`avg_*`) are the arithmetic mean of that
> strategy's per-window `test_sharpe` / `test_max_dd` values in the file — computed by
> script, not hand-estimated. CPCV re-run 2026-09-04 (`scripts/run_cpcv_validation.py::build_cpcv_entry`)
> added a `win_rate` key to `data/cpcv_registry.json`, but it is `null` on all 29 legs —
> `WalkForwardResult` carries no per-window win_rate — so WinRate stays `TBD (FASE 4)` for all rows.
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

## FASE 4 cross-asset verdict (2026-09-04, from `data/cpcv_registry.json`, 10 strategies)

> Bar: `min_sharpe` > 0 on every leg (all 14 combos profitable per asset) across all three assets (BTC-USD / EURUSD=X / GC=F).
> Computed by script from exact registry values — no hand estimates.

| Strategy | BTC-USD (avg, min) | EURUSD=X (avg, min) | GC=F (avg, min) | Verdict |
|----------|--------------------|--------------------|-----------------|---------|
| archive_aroon | +0.356, −0.199 | +0.329, −1.152 | +0.649, +0.165 | FAIL strict bar (EURUSD min −1.15); GC=F leg alone passes |
| archive_amdx | +0.627, −0.020 | 0.0, 0.0 (no data) | +0.446, −0.631 | FAIL (incomplete EURUSD leg) |
| archive_algebra | +0.201, −1.070 | +0.006, −0.744 | −0.018, −1.294 | FAIL (negative GC=F avg, all mins negative) |
| archive_gold_inflation | +0.268, −0.380 | −0.228, −1.459 | +0.465, −0.744 | FAIL (negative EURUSD avg) |
| kaufman_ama | +0.160, −0.684 | +0.672, −0.199 | +1.083, −0.391 | FAIL strict bar — but BEST of lot (all three avgs positive) |
| multi_timeframe | +0.172, −0.618 | −0.074, −1.412 | +0.892, −1.885 | FAIL (negative EURUSD avg) |
| archive_wyckoff | +0.061, −1.451 | 0.0, 0.0 (no data) | −0.340, −1.529 | FAIL (negative GC=F, incomplete EURUSD) |
| archive_mean_rev | +0.272, −0.402 | −0.449, −1.629 | +0.194, −0.155 | FAIL (negative EURUSD avg) |
| archive_ict_ote | +0.544, −0.334 | −0.574, −1.685 | +0.990, +0.411 | FAIL strict bar (EURUSD leg negative); BTC+GC legs strong |
| native_smc | −0.444, −1.058 | (no leg) | +0.200, −0.701 | FAIL (negative BTC avg, no EURUSD leg) |

> Note: the two all-zero legs (`archive_amdx` + `archive_wyckoff` EURUSD 0.0/0.0, `profitable_combos`=0) are no-data sentinels, not zero-edge; `native_smc` has no EURUSD leg at all — all per `data/cpcv_registry.json` (`archive_amdx`, `archive_wyckoff`, `native_smc` keys).

**Result: 0/10 pass the strict cross-asset bar. NOTHING is promoted to live-sizing on this evidence.**
Least-bad candidate for further research: `kaufman_ama` (only strategy with all-positive
avg_oos_sharpe: +0.16 / +0.67 / +1.08). Next step is NOT live size — it is a fresh
tri-asset WF run with trade logging (to fill WinRate) + embargo, then re-grade.

## Remaining strategies

| Strategy | WF Sharpe | MaxDD | WinRate | Period | Method | Verdict |
|----------|-----------|-------|---------|--------|--------|---------|
| all other 209 registry keys | TBD | TBD | TBD (`win_rate` key exists in cpcv_registry post-2026-09-04 re-run but is null on all legs — analyzer needs win-rate propagation first) | TBD | TBD | TBD |

## How to generate / refresh (verified script names — all exist in `scripts/`)

- `scripts/run_walkforward.py` — walk-forward validation runner (writes `data/walk_forward_registry.json`)
- `scripts/run_wf_validation.py` — alternate WF validation runner
- `scripts/run_cpcv_validation.py` — combinatorial purged CV runner (writes `data/cpcv_registry.json`)
- `scripts/ensemble_walk_forward.py` — ensemble-level WF runner
- NOTE: `scripts/run_multisymbol_wf.py` does NOT exist — do not reference it.

## Cross-asset note (already verified, CANONICAL §15.6)

Per-symbol CPCV evidence lives in `data/cpcv_registry.json` (10 strategies × BTC-USD / EURUSD=X / GC=F,
14 combos each, fields `combo_profit_share` / `avg_oos_sharpe` / `min_sharpe` / `max_sharpe`).
FASE 4 must promote only strategies with `min_sharpe` > 0 on every leg before any live-sizing claim.
