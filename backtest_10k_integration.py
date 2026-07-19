"""
Backtest 10K Bars — Final Integrasi Kronos + TradeBobby SMC + Dhaher System
Melakukan backtest semua strategy baru dengan 10,000 bar synthetic data.
"""
import sys, json, logging
from pathlib import Path
import pandas as pd
import numpy as np

SRC = Path(r'E:/trading')
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / 'strategies'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('bt10k')

# ─── Generate 10K bars synthetic OHLCV ────────────────────────────────────────
def generate_10k_bars(seed=42):
    """Generate 10,000 bars of synthetic OHLCV data resembling forex M15."""
    np.random.seed(seed)
    n = 10000
    
    dates = pd.date_range('2024-01-01', periods=n, freq='15min')
    
    # Random walk with mean-reversion and occasional trends
    t = np.linspace(0, 8*np.pi, n)
    trend = 5 * np.sin(t)  # cyclical macro trend
    noise = np.cumsum(np.random.randn(n)) * 0.08  # random walk
    
    close = 100.0 + trend + noise
    close = np.abs(close)  # ensure positive
    
    open_p = close + np.random.randn(n) * 0.05
    high = np.maximum(open_p, close) + np.abs(np.random.randn(n)) * 0.15 + 0.05
    low = np.minimum(open_p, close) - np.abs(np.random.randn(n)) * 0.15 - 0.05
    volume = np.abs(np.random.randn(n) * 100 + 1000)
    
    df = pd.DataFrame({
        'open': open_p.round(5),
        'high': high.round(5),
        'low': low.round(5),
        'close': close.round(5),
        'tick_volume': volume.round(0).astype(int),
    }, index=dates)
    
    # Ensure high >= open, close and low <= open, close
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    log.info(f"Generated {len(df)} bars: {df.index[0]} → {df.index[-1]}")
    return df


# ─── Backtest Engine ──────────────────────────────────────────────────────────
def backtest_strategy(df, strategy, initial_capital=1000.0, lot_size=0.01):
    """
    Simple but realistic backtest with SL/TP execution.
    
    Returns dict of metrics.
    """
    try:
        signals = strategy.generate_signals(df)
    except Exception as e:
        log.error(f"  Signal gen failed: {e}")
        return {"error": str(e)}
    
    capital = float(initial_capital)
    position = 0      # 0=none, 1=long, -1=short
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    trades = []
    equity_curve = [capital]
    
    for i in range(len(signals)):
        row = signals.iloc[i]
        price = row['close']
        
        # Check open position for SL/TP
        if position != 0:
            if position == 1:  # Long
                if row['low'] <= sl_price:
                    # Stop loss
                    pnl = (sl_price - entry_price) * lot_size * 100000
                    capital += pnl
                    trades.append({"type": "sl", "pnl": pnl, "price": sl_price, 
                                   "time": row.name})
                    position = 0
                elif row['high'] >= tp_price:
                    # Take profit
                    pnl = (tp_price - entry_price) * lot_size * 100000
                    capital += pnl
                    trades.append({"type": "tp", "pnl": pnl, "price": tp_price,
                                   "time": row.name})
                    position = 0
            elif position == -1:  # Short
                if row['high'] >= sl_price:
                    pnl = (entry_price - sl_price) * lot_size * 100000
                    capital += pnl
                    trades.append({"type": "sl", "pnl": pnl, "price": sl_price,
                                   "time": row.name})
                    position = 0
                elif row['low'] <= tp_price:
                    pnl = (entry_price - tp_price) * lot_size * 100000
                    capital += pnl
                    trades.append({"type": "tp", "pnl": pnl, "price": tp_price,
                                   "time": row.name})
                    position = 0
        
        # Check entry signal (only if no position)
        if position == 0 and row['entry'] != 0:
            # Check SL/TP columns
            if 'sl' in signals.columns and not pd.isna(row.get('sl')):
                sl_price = row['sl']
            else:
                atr_est = 0.0015 * price
                sl_price = price - atr_est * 1.5 if row['entry'] == 1 else price + atr_est * 1.5
            
            if 'tp' in signals.columns and not pd.isna(row.get('tp')):
                tp_price = row['tp']
            else:
                atr_est = 0.0015 * price
                tp_price = price + atr_est * 3.0 if row['entry'] == 1 else price - atr_est * 3.0
            
            position = row['entry']
            entry_price = price
            trades.append({"type": f"open_{'buy' if position == 1 else 'sell'}", 
                          "price": price, "time": row.name})
        
        equity_curve.append(capital)
    
    # Close final position at last price
    if position != 0:
        last_price = signals['close'].iloc[-1]
        if position == 1:
            pnl = (last_price - entry_price) * lot_size * 100000
        else:
            pnl = (entry_price - last_price) * lot_size * 100000
        capital += pnl
        trades.append({"type": "close", "pnl": pnl, "price": last_price})
    
    # Calculate metrics
    eq = pd.Series(equity_curve)
    ret_pct = (capital - initial_capital) / initial_capital * 100
    
    # Sharpe (using 35040 15-min periods per year)
    eq_ret = eq.pct_change().dropna()
    sharpe = np.sqrt(35040) * eq_ret.mean() / eq_ret.std() if eq_ret.std() > 0 else 0
    
    # Max drawdown
    peak = eq.expanding().max()
    dd = ((eq - peak) / peak).min() * 100
    
    # Win rate
    closed_trades = [t for t in trades if t['type'] in ('sl', 'tp', 'close')]
    wins = [t for t in closed_trades if t.get('pnl', 0) > 0]
    wr = len(wins) / len(closed_trades) * 100 if closed_trades else 0
    
    # Profit factor
    gross_profit = sum(t['pnl'] for t in closed_trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in closed_trades if t['pnl'] < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999
    
    return {
        "initial_capital": initial_capital,
        "final_capital": round(capital, 2),
        "return_pct": round(ret_pct, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown_pct": round(dd, 2),
        "win_rate": round(wr, 1),
        "total_trades": len(closed_trades),
        "profit_factor": round(pf, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


# ─── Run ──────────────────────────────────────────────────────────────────────
def run():
    log.info("═══ 10K BAR BACKTEST — INTEGRASI FINAL ═══\n")
    
    df = generate_10k_bars()
    
    # Import all strategies (triggers @register decorators)
    import strategies  # noqa: F401 — auto-loads dhaher_system, kronos_wrapper, tradebobby_smc_scanner
    from strategy_registry import get_strategy, list_strategies
    
    log.info(f"Registered strategies: {list_strategies()}\n")
    
    # Test specific strategies
    strategies_to_test = [
        ("DhaherSystem v1.1 (TUNED)", "DhaherSystem", {"lookback": 14, "atr_mult": 1.5, "rr_min": 2.0, "min_confluence": 2, "use_adx_filter": False}),
        ("TradeBobby SMC", "TradeBobbySMCStrategy", {"swing_lookback": 5, "min_confluence": 3}),
        ("Kronos Provider", "KronosSignalProvider", {"lookback": 200, "pred_len": 5}),
        ("Kronos Ensemble", "KronosEnsembleStrategy", {"lookback": 200, "pred_len": 5}),
        ("SMC (library-based)", "SMCStrategy", {"swing_length": 10}),
        ("Wyckoff (gate-passed)", "WyckoffStrategy", {"lookback": 50, "volume_mult": 1.3}),
        ("MeanRev (gate-passed)", "MeanReversionStrategy", {"k_period": 14, "d_period": 5, "oversold": 25, "overbought": 75}),
    ]
    
    results = []
    
    for label, strat_name, params in strategies_to_test:
        log.info(f"  Testing: {label} ({strat_name})...")
        
        try:
            strat = get_strategy(strat_name, **params)
            result = backtest_strategy(df, strat)
            result["label"] = label
            result["strategy"] = strat_name
            result["params"] = str(params)
            results.append(result)
            
            if "error" in result:
                log.info(f"    ❌ {result['error']}")
            else:
                wr = result['win_rate']
                sharpe = result['sharpe']
                ret = result['return_pct']
                dd = result['max_drawdown_pct']
                pf = result['profit_factor']
                
                wr_emoji = "✅" if wr >= 30 else "⚠️" if wr >= 20 else "❌"
                gate_emoji = "✅" if (sharpe > 0.5 and ret > 0 and dd > -25 and wr > 30) else "❌"
                
                log.info(f"    WR={wr:.1f}% {wr_emoji} | Sharpe={sharpe} | Ret={ret:+.2f}% | DD={dd:.1f}% | PF={pf} | Gate={gate_emoji}")
                
        except Exception as e:
            log.info(f"    ❌ ERROR: {e}")
            results.append({"label": label, "strategy": strat_name, "error": str(e)})
    
    # Summary
    print("\n\n" + "=" * 90)
    print("  HASIL BACKTEST 10K BAR — INTEGRASI FINAL")
    print("=" * 90)
    print(f"{'Strategy':<35} {'WR%':<8} {'Sharpe':<8} {'Return%':<10} {'DD%':<8} {'PF':<8} {'Gate':<8}")
    print("-" * 90)
    
    gates_pass = 0
    gates_fail = 0
    
    for r in results:
        if "error" in r:
            print(f"  {r['label']:<35} {'ERROR':<8}")
            continue
        
        wr = r['win_rate']
        sharpe = r['sharpe']
        ret = r['return_pct']
        dd = r['max_drawdown_pct']
        pf = r['profit_factor']
        
        gate_pass = (sharpe > 0.5 and ret > 0 and dd > -25 and wr >= 30)
        gate_str = "✅ LOLOS" if gate_pass else "❌ GAGAL"
        
        if gate_pass:
            gates_pass += 1
        else:
            gates_fail += 1
        
        print(f"  {r['label']:<35} {wr:<8.1f} {sharpe:<8.3f} {ret:<+9.2f}% {dd:<8.2f} {pf:<8.2f} {gate_str}")
    
    print("-" * 90)
    print(f"  Gate: {gates_pass}/{len(results)} passed  |  {gates_fail} failed")
    print("=" * 90)
    
    # Save report
    report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "bars": len(df),
        "results": [{
            "label": r.get("label"),
            "strategy": r.get("strategy"),
            "win_rate": r.get("win_rate"),
            "sharpe": r.get("sharpe"),
            "return_pct": r.get("return_pct"),
            "max_drawdown_pct": r.get("max_drawdown_pct"),
            "profit_factor": r.get("profit_factor"),
            "total_trades": r.get("total_trades"),
            "gate_pass": r.get("sharpe", 0) > 0.5 and r.get("return_pct", 0) > 0 and r.get("max_drawdown_pct", 0) > -25 and r.get("win_rate", 0) >= 30,
        } for r in results if "error" not in r]
    }
    
    report_path = SRC / "results" / "bt_10k_integration_final.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str))
    log.info(f"\nReport saved: {report_path}")
    
    return results


if __name__ == '__main__':
    run()
