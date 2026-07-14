#!/usr/bin/env python3
"""Fast backtest ALL 106 strategies on BTC-USD and EURUSD.

Imports each strategy file individually (no heavy __init__.py chain).
Uses numpy/pandas/yfinance. Outputs comparison table to backtest_all_results.md.
"""
import numpy as np
import pandas as pd
import warnings, sys, os, importlib, time
from pathlib import Path
warnings.filterwarnings("ignore")

STRAT_DIR = Path(r"D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe\engine\strategy\strategies")
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")

def load_data(symbol, period="2y"):
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    if df.empty:
        raise ValueError(f"No data for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

def compute_metrics(signals, data):
    """Compute backtest metrics from signals."""
    close = data['close'].values
    n = len(close)
    trades = []
    position = 0
    entry_price = 0
    
    for i in range(1, n):
        sig = signals.iloc[i] if i < len(signals) else 0
        if sig == 1 and position == 0:
            position = 1
            entry_price = close[i]
        elif sig == -1 and position == 0:
            position = -1
            entry_price = close[i]
        elif sig == -1 and position == 1:
            pnl = (close[i] - entry_price) / entry_price
            trades.append(pnl)
            position = 0
        elif sig == 1 and position == -1:
            pnl = (entry_price - close[i]) / entry_price
            trades.append(pnl)
            position = 0
    
    if not trades:
        return {"return": 0, "wr": 0, "sharpe": 0, "maxdd": 0, "pf": 0, "trades": 0, "avg_win": 0, "avg_loss": 0, "rr": 0}
    
    trades = np.array(trades)
    wins = trades[trades > 0]
    losses = trades[trades < 0]
    
    total_return = np.prod(1 + trades) - 1
    wr = len(wins) / len(trades) * 100 if len(trades) > 0 else 0
    
    # Sharpe (annualized)
    if np.std(trades) > 0:
        sharpe = np.mean(trades) / np.std(trades) * np.sqrt(252)
    else:
        sharpe = 0
    
    # Max drawdown
    equity = np.cumprod(1 + trades)
    running_max = np.maximum.accumulate(equity)
    drawdowns = (equity - running_max) / running_max
    maxdd = np.min(drawdowns) * 100
    
    # Profit factor
    gross_profit = np.sum(wins) if len(wins) > 0 else 0
    gross_loss = abs(np.sum(losses)) if len(losses) > 0 else 1e-10
    pf = gross_profit / gross_loss
    
    avg_win = np.mean(wins) * 100 if len(wins) > 0 else 0
    avg_loss = abs(np.mean(losses)) * 100 if len(losses) > 0 else 0
    rr = avg_win / avg_loss if avg_loss > 0 else 0
    
    return {
        "return": total_return * 100,
        "wr": wr,
        "sharpe": sharpe,
        "maxdd": maxdd,
        "pf": pf,
        "trades": len(trades),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "rr": rr,
    }

def backtest_strategy(strategy_file, data):
    """Import and run a single strategy file with bar-by-bar simulation."""
    try:
        spec = importlib.util.spec_from_file_location("strategy_module", strategy_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        strategy_class = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and attr_name.endswith("Strategy") and attr_name != "BaseStrategy":
                strategy_class = attr
                break
        
        if not strategy_class:
            return None
        
        try:
            instance = strategy_class()
        except TypeError:
            try:
                instance = strategy_class(params={})
            except:
                return None
        
        if not hasattr(instance, 'generate_signal'):
            return None
        
        # Bar-by-bar simulation
        signals = pd.Series(0, index=data.index)
        warmup = instance.warmup_period() if hasattr(instance, 'warmup_period') else 50
        
        for i in range(warmup, len(data)):
            window = data.iloc[:i+1]
            try:
                result = instance.generate_signal(window)
                if result is None:
                    continue
                if isinstance(result, pd.Series):
                    signals.iloc[i] = result.iloc[-1] if len(result) > 0 else 0
                elif hasattr(result, 'signal_type'):
                    st = result.signal_type.value if hasattr(result.signal_type, 'value') else str(result.signal_type)
                    if st == 'buy': signals.iloc[i] = 1
                    elif st == 'sell': signals.iloc[i] = -1
            except Exception:
                continue
        
        return compute_metrics(signals, data)
    except Exception:
        return None

def main():
    # Load data
    print("Loading BTC-USD data...")
    btc = load_data("BTC-USD")
    print(f"  {len(btc)} bars loaded")
    
    print("Loading EURUSD data...")
    eurusd = load_data("EURUSD=X")
    print(f"  {len(eurusd)} bars loaded")
    
    # Find all strategy files
    strategy_files = sorted(STRAT_DIR.glob("*.py"))
    strategy_files = [f for f in strategy_files if f.name not in ("__init__.py", "base_strategy.py")]
    
    print(f"\nBacktesting {len(strategy_files)} strategies...\n")
    
    results = []
    for i, sf in enumerate(strategy_files):
        name = sf.stem
        sys.stdout.write(f"\r  [{i+1}/{len(strategy_files)}] {name:40s}")
        sys.stdout.flush()
        
        # BTC-USD
        btc_metrics = backtest_strategy(sf, btc)
        # EURUSD
        eur_metrics = backtest_strategy(sf, eurusd)
        
        verdict = "UNTESTED"
        if btc_metrics and btc_metrics["trades"] > 0 and eur_metrics and eur_metrics["trades"] > 0:
            btc_sharpe = btc_metrics["sharpe"]
            eur_sharpe = eur_metrics["sharpe"]
            if btc_sharpe > 0.5 and eur_sharpe > 0.5:
                verdict = "KEEP"
            elif btc_sharpe > 0.5 or eur_sharpe > 0.5:
                verdict = "MARGINAL"
            elif btc_sharpe < -0.5 and eur_sharpe < -0.5:
                verdict = "ELIMINATE"
            else:
                verdict = "MARGINAL"
        elif btc_metrics and btc_metrics["trades"] > 0:
            if btc_metrics["sharpe"] > 0.5: verdict = "KEEP"
            elif btc_metrics["sharpe"] < -0.5: verdict = "ELIMINATE"
            else: verdict = "MARGINAL"
        elif eur_metrics and eur_metrics["trades"] > 0:
            if eur_metrics["sharpe"] > 0.5: verdict = "KEEP"
            elif eur_metrics["sharpe"] < -0.5: verdict = "ELIMINATE"
            else: verdict = "MARGINAL"
        else:
            verdict = "SKIP"
        
        results.append({
            "name": name,
            "btc": btc_metrics or {"return": 0, "wr": 0, "sharpe": 0, "maxdd": 0, "pf": 0, "trades": 0, "avg_win": 0, "avg_loss": 0, "rr": 0},
            "eur": eur_metrics or {"return": 0, "wr": 0, "sharpe": 0, "maxdd": 0, "pf": 0, "trades": 0, "avg_win": 0, "avg_loss": 0, "rr": 0},
            "verdict": verdict,
        })
    
    print(f"\n\nBacktest complete: {len(results)} strategies")
    
    # Write results
    lines = ["# All-Strategy Backtest Results", "", f"Run: {time.strftime('%Y-%m-%d %H:%M')}", f"Strategies: {len(results)}", ""]
    lines.append("| Strategy | BTC Return | BTC Sharpe | BTC WR | BTC MaxDD | BTC Trades | EUR Return | EUR Sharpe | EUR WR | Verdict |")
    lines.append("|----------|-----------|-----------|--------|-----------|------------|-----------|-----------|--------|---------|")
    
    for r in sorted(results, key=lambda x: x["btc"]["sharpe"], reverse=True):
        b, e, v = r["btc"], r["eur"], r["verdict"]
        emoji = {"KEEP": "✅", "MARGINAL": "⚠️", "ELIMINATE": "❌", "SKIP": "⏭️", "UNTESTED": "?"}.get(v, "")
        lines.append(f"| {r['name']:30s} | {b['return']:8.1f}% | {b['sharpe']:7.2f} | {b['wr']:5.1f}% | {b['maxdd']:7.1f}% | {b['trades']:5d} | {e['return']:8.1f}% | {e['sharpe']:7.2f} | {e['wr']:5.1f}% | {emoji} {v} |")
    
    # Summary
    keep = sum(1 for r in results if r["verdict"] == "KEEP")
    marginal = sum(1 for r in results if r["verdict"] == "MARGINAL")
    eliminate = sum(1 for r in results if r["verdict"] == "ELIMINATE")
    skip = sum(1 for r in results if r["verdict"] == "SKIP")
    untested = sum(1 for r in results if r["verdict"] == "UNTESTED")
    lines.extend(["", f"## Summary", f"- KEEP: {keep}", f"- MARGINAL: {marginal}", f"- ELIMINATE: {eliminate}", f"- SKIP: {skip}", f"- UNTESTED: {untested}"])
    
    out = Path(r"D:\repositories\Quant-Nanggroe-AI-worktree\backtest_all_results.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Results saved to {out}")
    print(f"\nKEEP: {keep} | MARGINAL: {marginal} | ELIMINATE: {eliminate} | SKIP: {skip}")

if __name__ == "__main__":
    main()
