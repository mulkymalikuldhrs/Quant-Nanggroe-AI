"""Risk Param Grid Search — Phase 5 WAR_PLAN optimization.

Grids kelly_fraction × sl_atr_mult × rr_target using real QNA engine modules.
Simulates equity with Monte Carlo from documented strategy metrics.
Output: best param combo maximizing Sharpe while keeping max_DD > -25%.
"""
import sys, json, numpy as np
sys.path.insert(0, r"D:/repositories/Quant-Nanggroe-AI-worktree")

from quant_nanggroe.engine.risk.kelly import KellyCriterion, KellyMethod, KellyParameters, KellyResult

# ── Documented strategy metrics (real backtest evidence) ──
STRATEGIES = {
    "Wyckoff":  {"wr": 0.596, "sharpe": 2.69, "dd": -0.307},
    "MeanRev":  {"wr": 0.544, "sharpe": 1.98, "dd": -0.248},
    "SMC":      {"wr": 0.596, "sharpe": 2.258, "dd": -0.307},
    "Dhaher":   {"wr": 0.421, "sharpe": 3.77, "dd": -0.0248},
}

# ── Grid ──
KELLY_FRACS   = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
SL_ATR_MULTS  = [1.0, 1.25, 1.5, 2.0, 2.5]
RR_TARGETS    = [1.5, 2.0, 2.5, 3.0, 3.5]

EQUITY = 10000.0
SIM_TRADES = 500
SIM_ITERS  = 200


def simulate_equity_curve(kelly_frac, sl_mult, rr, strat_metrics,
                           n_trades=SIM_TRADES, n_iters=SIM_ITERS):
    """Monte Carlo simulate equity with real Kelly sizing + SL/TP-aware trade sizing.

    Risk params (sl_mult, rr) affect the effective avg_win/avg_loss ratio:
    - sl_mult: wider stop -> larger loss per trade -> higher R:R potential
    - rr: higher reward target -> avg_win grows with rr
    We model avg_loss as 1 unit (denominator), avg_win as rr * avg_loss.
    """
    from quant_nanggroe.engine.risk.kelly import KellyMethod as KM

    kelly = KellyCriterion(max_position=0.10)

    # Effective win/loss: rr_target determines avg_win relative to avg_loss=1
    effective_avg_win  = rr          # reward = rr * avg_loss
    effective_avg_loss = 1.0        # base unit

    params = KellyParameters(
        win_rate=strat_metrics["wr"],
        avg_win=effective_avg_win,
        avg_loss=effective_avg_loss,
    )

    # Compute Kelly f* with this kelly_frac (fraction of full Kelly)
    method = KM.FRACTIONAL_KELLY
    result = kelly.calculate_kelly(params, method)
    f_star_raw = result.optimal_fraction  # full Kelly
    f_star = f_star_raw * kelly_frac  # apply fraction

    # Cap at MAX_RISK_PER_TRADE = 0.5% = 0.005
    risk_per_trade = min(f_star, 0.005)

    # Position risk amount (base currency)
    risk_amount = EQUITY * risk_per_trade

    sharpe_samples = []
    dd_samples = []

    rng = np.random.RandomState(42)

    for _ in range(n_iters):
        equity = np.zeros(n_trades + 1)
        equity[0] = EQUITY
        for t in range(n_trades):
            is_win = rng.random() < strat_metrics["wr"]
            if is_win:
                pnl = risk_amount * (effective_avg_win / effective_avg_loss)
            else:
                # Loss is sl_mult-dependent: tighter stop -> smaller loss
                # Normalize so sl_mult=1.5 gives avg_loss=1.0 (baseline)
                loss_mult = 1.5 / sl_mult
                pnl = -risk_amount * loss_mult
            equity[t + 1] = equity[t] + pnl
            if equity[t + 1] < 0:
                equity[t + 1] = 0.0

        rets = np.diff(equity) / np.maximum(equity[:-1], 1e-9)
        rets = rets[np.isfinite(rets)]
        if len(rets) > 1:
            mu  = np.mean(rets)
            sig = np.std(rets, ddof=1)
            sharpe_samples.append(np.sqrt(252) * mu / sig if sig > 1e-9 else 0.0)

        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / np.maximum(peak, 1e-9)
        dd_samples.append(float(np.min(dd)))

    return {
        "kelly_f_star": round(f_star, 6),
        "risk_per_trade": round(risk_per_trade, 6),
        "risk_amount": round(risk_amount, 2),
        "mean_sharpe": round(float(np.mean(sharpe_samples)), 4) if sharpe_samples else 0,
        "median_sharpe": round(float(np.median(sharpe_samples)), 4) if sharpe_samples else 0,
        "mean_dd": round(float(np.mean(dd_samples)), 4),
        "worst_dd": round(float(np.min(dd_samples)), 4),
    }


def full_grid_search():
    results = []

    for kelly_f in KELLY_FRACS:
        for sl_m in SL_ATR_MULTS:
            for rr_t in RR_TARGETS:
                sharpes = []
                dds = []
                for name, sm in STRATEGIES.items():
                    sim = simulate_equity_curve(kelly_f, sl_m, rr_t, sm)
                    sharpes.append(sim["mean_sharpe"])
                    dds.append(sim["worst_dd"])

                avg_sharpe = np.mean(sharpes)
                avg_dd = np.mean(dds)

                results.append({
                    "kelly_frac": kelly_f,
                    "sl_atr_mult": sl_m,
                    "rr_target": rr_t,
                    "avg_sharpe": round(float(avg_sharpe), 4),
                    "avg_dd": round(float(avg_dd), 4),
                    "worst_dd": round(float(min(dds)), 4),
                })

    # Gate: DD > -25% AND Sharpe > 0
    passing = [r for r in results if r["worst_dd"] > -0.25 and r["avg_sharpe"] > 0]
    passing.sort(key=lambda r: r["avg_sharpe"], reverse=True)

    return results, passing


if __name__ == "__main__":
    all_results, passing = full_grid_search()

    print(f"TOTAL_COMBOS: {len(all_results)}")
    print(f"GATE_PASSING (Sharpe>0, DD>-25%): {len(passing)}")

    if passing:
        best = passing[0]
        print(f"\nBEST: kelly={best['kelly_frac']}, sl_atr={best['sl_atr_mult']}, rr={best['rr_target']}")
        print(f"  avg_sharpe={best['avg_sharpe']}, worst_dd={best['worst_dd']}")

        print(f"\nCURRENT: kelly=0.25, sl_atr=1.5, rr=2.0")
        current = [r for r in all_results if r["kelly_frac"]==0.25 and r["sl_atr_mult"]==1.5 and r["rr_target"]==2.0]
        if current:
            c = current[0]
            print(f"  avg_sharpe={c['avg_sharpe']}, worst_dd={c['worst_dd']}")

        print("\nTOP_10:")
        for i, r in enumerate(passing[:10], 1):
            print(f"  {i}. kelly={r['kelly_frac']} sl={r['sl_atr_mult']} rr={r['rr_target']} -> Sharpe={r['avg_sharpe']} DD={r['worst_dd']}")
    else:
        print("NO_GATE_PASSING -- relax constraints or fix strategy metrics")
        all_results.sort(key=lambda r: r["avg_sharpe"], reverse=True)
        print("TOP_10 by sharpe (ignoring DD gate):")
        for i, r in enumerate(all_results[:10], 1):
            print(f"  {i}. kelly={r['kelly_frac']} sl={r['sl_atr_mult']} rr={r['rr_target']} -> Sharpe={r['avg_sharpe']} DD={r['worst_dd']}")

    print("\n__JSON_START__")
    print(json.dumps({
        "total": len(all_results),
        "passing": len(passing),
        "best": passing[0] if passing else all_results[0],
        "current": {"kelly_frac": 0.25, "sl_atr_mult": 1.5, "rr_target": 2.0},
    }))
    print("__JSON_END__")
