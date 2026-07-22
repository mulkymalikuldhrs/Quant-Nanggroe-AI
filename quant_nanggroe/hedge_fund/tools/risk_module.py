"""
Risk Module — Kelly Criterion + Monte Carlo + Dynamic Sizing
Semua berbasis matematika, bukan feeling.
"""
import numpy as np
import pandas as pd
from pathlib import Path
import json, logging, random, math
from datetime import datetime

_HF_TOOLS_DIR = Path(__file__).resolve().parent
SRC = _HF_TOOLS_DIR
log = logging.getLogger('risk')

# ── 1. KELLY CRITERION ──
def kelly_fraction(win_rate, avg_win, avg_loss):
    """
    Kelly Criterion: f* = (p * b - q) / b
    p = win rate, q = loss rate (1-p), b = avg_win/avg_loss (odds)
    """
    if avg_loss == 0: return 0
    b = avg_win / abs(avg_loss)  # odds
    p = win_rate / 100 if win_rate > 1 else win_rate
    q = 1 - p
    kelly = (p * b - q) / b if b > 0 else 0
    # Fractional Kelly (25% for safety)
    return max(0, min(0.25, kelly * 0.25))

def kelly_lot_size(balance, kelly_pct, stop_loss_pips=50, pip_value=10):
    """
    Lot size dari Kelly: lot = (balance * kelly%) / (SL_pips * pip_value)
    Untuk EURUSD 1 lot = $10/pip
    """
    risk_amount = balance * kelly_pct
    lot = risk_amount / (stop_loss_pips * pip_value)
    return round(max(0.01, min(lot, balance / 5000)), 2)

# ── 2. MONTE CARLO ──
def monte_carlo_simulation(trades, simulations=10000, confidence=0.95):
    """
    Monte Carlo: random sampling of historical trades
    Returns: VaR, CVaR, probability of profit, best/worst case
    """
    if not trades or len(trades) < 5:
        return {"error": "Need at least 5 trades"}
    
    pnls = [t.get('pnl', 0) for t in trades if 'pnl' in t]
    if not pnls:
        return {"error": "No PnL data"}
    
    results = []
    for _ in range(simulations):
        sampled = random.choices(pnls, k=len(pnls))
        results.append(sum(sampled))
    
    results.sort()
    var_idx = int((1 - confidence) * simulations)
    cvar_idx = int((1 - confidence) * simulations / 2)
    
    return {
        "simulations": simulations,
        "confidence": confidence,
        "mean_return": round(np.mean(results), 2),
        "median_return": round(np.median(results), 2),
        "var_95pct": round(results[var_idx], 2),  # Value at Risk
        "cvar_95pct": round(np.mean(results[:cvar_idx]), 2),  # Conditional VaR
        "prob_profit": round(sum(1 for r in results if r > 0) / simulations * 100, 1),
        "best_case": round(results[-1], 2),
        "worst_case": round(results[0], 2),
        "std_dev": round(np.std(results), 2),
    }

# ── 3. SHARPE & SORTINO ──
def performance_metrics(equity_curve, rf_rate=0.05):
    """Sharpe ratio, Sortino ratio, Calmar ratio, max DD"""
    eq = pd.Series(equity_curve) if not isinstance(equity_curve, pd.Series) else equity_curve
    ret = eq.pct_change().dropna()
    
    # Annualized (assuming 15min bars ≈ 35040/year)
    ann_factor = np.sqrt(35040)
    ann_ret = ret.mean() * 35040
    ann_vol = ret.std() * ann_factor
    
    sharpe = (ann_ret - rf_rate) / ann_vol if ann_vol > 0 else 0
    
    # Sortino (downside deviation only)
    downside = ret[ret < 0]
    down_dev = downside.std() * ann_factor if len(downside) > 0 else 0.001
    sortino = (ann_ret - rf_rate) / down_dev if down_dev > 0 else 0
    
    # Max drawdown
    peak = eq.expanding().max()
    dd = ((eq - peak) / peak)
    max_dd = dd.min() * 100
    
    # Calmar (return / max DD)
    calmar = ann_ret / abs(max_dd) * 100 if abs(max_dd) > 0 else 0
    
    return {
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "annualized_return_pct": round(ann_ret * 100, 2),
        "annualized_vol_pct": round(ann_vol * 100, 2),
    }

# ── 4. ADAPTIVE RISK (market condition based) ──
def adaptive_risk(balance, atr, win_rate_24h, regime="neutral"):
    """
    Risk adjustment based on market conditions
    Bear/volatile → reduce risk. Bull/calm → normal risk.
    """
    base_risk_pct = 0.02  # 2% base risk
    
    # Regime adjustment
    regime_mult = {"bull": 1.0, "bear": 0.5, "neutral": 0.75, "volatile": 0.3}
    mult = regime_mult.get(regime, 0.75)
    
    # Recent performance adjustment
    perf_mult = 1.0
    if win_rate_24h < 30: perf_mult = 0.5  # losing streak → cut risk
    elif win_rate_24h > 70: perf_mult = 1.2  # hot streak → slight increase
    
    # ATR adjustment (higher ATR = lower size)
    atr_mult = max(0.3, min(1.0, 0.0010 / max(atr, 0.0001)))
    
    risk_pct = base_risk_pct * mult * perf_mult * atr_mult
    risk_pct = max(0.005, min(risk_pct, 0.05))  # clamp 0.5%-5%
    
    return {
        "risk_per_trade_pct": round(risk_pct * 100, 2),
        "max_lot": round(max(0.01, balance * risk_pct / 500), 2),
        "regime_mult": round(mult, 2),
        "perf_mult": round(perf_mult, 2),
        "atr_mult": round(atr_mult, 2),
    }

# ── 5. SCORE: Composite Strategy Score ──
def strategy_score(backtest_result, walkforward_result):
    """
    Composite score for ranking strategies.
    Weighted: Sharpe 40%, Return 20%, DD 20%, WinRate 10%, Kelly 10%
    """
    bt = backtest_result
    wf = walkforward_result
    
    shp = max(-2, min(3, bt.get('sharpe', 0)))  # clamp
    ret = max(-50, min(100, bt.get('return_pct', 0)))
    dd = max(-50, min(0, bt.get('max_drawdown', -50)))
    wr = bt.get('win_rate', 0)
    
    # Kelly
    kelly = kelly_fraction(wr, 
                          bt.get('avg_win', bt.get('return_pct', 1) / max(bt.get('closed_trades', 1), 1)),
                          bt.get('avg_loss', -ret / max(bt.get('closed_trades', 1), 1)))
    
    # Walk-forward penalty
    wf_ret = wf.get('avg_return_pct', 0) if wf else ret
    wf_penalty = 0.5 if wf_ret < 0 else 1.0
    
    score = (shp / 3 * 40) + (ret / 100 * 20) + (dd / -50 * 20) + (wr / 100 * 10) + (kelly * 10)
    score = score * wf_penalty
    
    return {
        "composite_score": round(max(0, min(100, score)), 1),
        "sharpe_score": round(shp / 3 * 40, 1),
        "return_score": round(max(0, ret) / 100 * 20, 1),
        "drawdown_score": round(min(20, abs(dd) / 50 * 20), 1),
        "winrate_score": round(wr / 100 * 10, 1),
        "kelly_score": round(kelly * 10, 1),
        "wf_penalty": round(wf_penalty, 2),
    }

if __name__ == "__main__":
    # Demo
    print("=== Risk Module Demo ===\n")
    
    # Kelly
    print(f"Kelly fraction (40% WR, 2:1 RR): {kelly_fraction(0.4, 200, 100):.4f}")
    print(f"Kelly lot ($1000, 50pip SL): {kelly_lot_size(1000, 0.05, 50):.2f}")
    
    # Monte Carlo
    demo_trades = [{'pnl': random.uniform(-50, 150)} for _ in range(100)]
    mc = monte_carlo_simulation(demo_trades, simulations=1000)
    print(f"\nMonte Carlo: VaR95=${mc.get('var_95pct',0)} Profit%={mc.get('prob_profit',0)}%")
    
    # Adaptive risk
    ar = adaptive_risk(1000, 0.0015, 55, "neutral")
    print(f"Adaptive risk: {ar['risk_per_trade_pct']}% per trade, max lot {ar['max_lot']}")
    
    # Composite score
    bt = {"sharpe":1.8, "return_pct":45, "max_drawdown":-12, "win_rate":55, "closed_trades":50}
    wf = {"avg_return_pct": 22}
    sc = strategy_score(bt, wf)
    print(f"Composite score: {sc['composite_score']}/100")
