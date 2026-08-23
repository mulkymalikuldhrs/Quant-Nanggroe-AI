"""
Dhaher System v1.0 — Proper Backtest with SL/TP
Re-runs backtest using DhaherSystem's built-in ATR-based SL/TP
"""
import sys, json, logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

SRC = Path(r'E:/trading')
RESULT = SRC / 'results'
RESULT.mkdir(parents=True, exist_ok=True)
HERE = Path(r'D:/repositories/Quant-Nanggroe-AI-worktree')
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'quant_nanggroe' / 'engine' / 'strategies'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('dhaher_bt')

from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem
from backtest_pipeline import get_historical, gate_decision
from risk_module import kelly_fraction, strategy_score


def backtest_with_sltp(df, strategy, initial_capital=1000):
    """
    Backtest DhaherSystem respecting its ATR-based SL and TP.
    Each entry signal gets a fixed stop-loss and take-profit.
    """
    data = strategy.generate_signals(df)
    
    capital = float(initial_capital)
    equity_curve = [initial_capital] * len(data)
    trades = []
    position = 0
    entry_price = 0
    entry_sl = 0
    entry_tp = 0
    pos_start_idx = 0
    
    for i in range(len(data)):
        row = data.iloc[i]
        price = row['close']
        
        # If in a position, check SL/TP hit
        if position != 0:
            if position == 1:  # Long
                # Check stop loss
                if price <= entry_sl:
                    pnl = (entry_sl - entry_price) / entry_price * capital
                    capital += pnl
                    trades.append({"type": "sl_buy", "price": entry_sl, "pnl": pnl, "bars_held": i - pos_start_idx})
                    position = 0
                # Check take profit
                elif price >= entry_tp:
                    pnl = (entry_tp - entry_price) / entry_price * capital
                    capital += pnl
                    trades.append({"type": "tp_buy", "price": entry_tp, "pnl": pnl, "bars_held": i - pos_start_idx})
                    position = 0
            else:  # Short
                if price >= entry_sl:
                    pnl = (entry_price - entry_sl) / entry_price * capital
                    capital += pnl
                    trades.append({"type": "sl_sell", "price": entry_sl, "pnl": pnl, "bars_held": i - pos_start_idx})
                    position = 0
                elif price <= entry_tp:
                    pnl = (entry_price - entry_tp) / entry_price * capital
                    capital += pnl
                    trades.append({"type": "tp_sell", "price": entry_tp, "pnl": pnl, "bars_held": i - pos_start_idx})
                    position = 0
        
        # Entry signal — only enter if no position
        if position == 0:
            if row['entry'] == 1 and not pd.isna(row['sl']) and not pd.isna(row['tp']):
                position = 1
                entry_price = price
                entry_sl = row['sl']
                entry_tp = row['tp']
                pos_start_idx = i
                trades.append({"type": "open_buy", "price": price, "time": row.name})
            elif row['entry'] == -1 and not pd.isna(row['sl']) and not pd.isna(row['tp']):
                position = -1
                entry_price = price
                entry_sl = row['sl']
                entry_tp = row['tp']
                pos_start_idx = i
                trades.append({"type": "open_sell", "price": price, "time": row.name})
        
        # Current equity valuation
        if position == 1:
            equity = capital + (price - entry_price) / entry_price * capital
        elif position == -1:
            equity = capital + (entry_price - price) / entry_price * capital
        else:
            equity = capital
        equity_curve[i] = equity
    
    # Close any remaining position at end
    if position != 0:
        last_price = data.iloc[-1]['close']
        if position == 1:
            pnl = (last_price - entry_price) / entry_price * capital
        else:
            pnl = (entry_price - last_price) / entry_price * capital
        capital += pnl
        trades.append({"type": "final_close", "price": last_price, "pnl": pnl, "bars_held": len(data) - pos_start_idx})
    
    # Metrics
    eq = pd.Series(equity_curve, index=data.index)
    total_return = capital - initial_capital
    ret_pct = (capital - initial_capital) / initial_capital * 100
    ret_s = eq.pct_change().dropna()
    sharpe = np.sqrt(35040) * ret_s.mean() / ret_s.std() if ret_s.std() > 0 else 0
    peak = eq.expanding().max()
    dd = ((eq - peak) / peak).min() * 100
    
    closed = [t for t in trades if 'pnl' in t and t.get('type', '').startswith(('sl_', 'tp_', 'final'))]
    wins = [t for t in closed if t['pnl'] > 0]
    wr = len(wins) / len(closed) * 100 if closed else 0
    
    return {
        "strategy": strategy.name,
        "initial_capital": initial_capital,
        "final_capital": round(capital, 2),
        "total_return": round(total_return, 2),
        "return_pct": round(ret_pct, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(dd, 2),
        "win_rate": round(wr, 1),
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "avg_win": round(np.mean([t['pnl'] for t in wins]), 2) if wins else 0,
        "avg_loss": round(np.mean([t['pnl'] for t in closed if t['pnl'] <= 0]), 2) if any(t['pnl'] <= 0 for t in closed) else 0,
    }, trades, eq


def main():
    log.info("══════════════════════════════════════════════")
    log.info("  DHAHER SYSTEM v1.0 — SL/TP-AWARE BACKTEST ")
    log.info("══════════════════════════════════════════════")
    
    symbol = "EURUSD"
    log.info(f"📡 Loading {symbol} data...")
    df = get_historical(symbol, days=365, tf="M15")
    if df is None:
        log.error("❌ Data unavailable"); return
    log.info(f"📊 {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}")
    
    # Test multiple parameter sets
    configs = [
        ("default", {"lookback": 20, "atr_mult": 1.5, "rr_min": 2.0}),
        ("tighter SL", {"lookback": 20, "atr_mult": 1.2, "rr_min": 2.5}),
        ("wider SL", {"lookback": 30, "atr_mult": 2.0, "rr_min": 2.0}),
        ("faster", {"lookback": 15, "atr_mult": 1.5, "rr_min": 2.0}),
        ("max risk", {"lookback": 25, "atr_mult": 1.0, "rr_min": 3.0}),
    ]
    
    results = []
    for label, params in configs:
        strat = DhaherSystem(**params)
        bt, trades, eq = backtest_with_sltp(df, strat)
        bt['config'] = label
        bt['params'] = params
        results.append(bt)
        
        status = "✅" if bt['sharpe'] > 0.5 and bt['return_pct'] > 0 and bt['max_drawdown'] > -25 else "❌"
        log.info(f"  {label:15s}: {status} Ret={bt['return_pct']:+.2f}% SR={bt['sharpe']:.3f} DD={bt['max_drawdown']:.2f}% WR={bt['win_rate']:.1f}% Trades={bt['total_trades']}")
    
    # Sort by Sharpe
    results.sort(key=lambda r: r['sharpe'], reverse=True)
    best = results[0]
    
    log.info(f"\n{'═'*55}")
    log.info(f"  BEST CONFIG: {best['config']}")
    log.info(f"    Return: {best['return_pct']:+.2f}%")
    log.info(f"    Sharpe: {best['sharpe']:.3f}")
    log.info(f"    Max DD: {best['max_drawdown']:.2f}%")
    log.info(f"    Win Rate: {best['win_rate']:.1f}%")
    log.info(f"    Total Trades: {best['total_trades']}")
    log.info(f"    Closed: {best['closed_trades']}")
    
    # Gate check
    gate = {
        "pass": best['sharpe'] > 0.5 and best['return_pct'] > 0 and best['max_drawdown'] > -25,
        "sharpe_check": best['sharpe'] > 0.5,
        "return_check": best['return_pct'] > 0,
        "dd_check": best['max_drawdown'] > -25,
    }
    log.info(f"  Gate: {'✅ LOLOS' if gate['pass'] else '❌ GAGAL'}")
    log.info(f"    Sharpe {best['sharpe']:.3f} > 0.5: {'✅' if gate['sharpe_check'] else '❌'}")
    log.info(f"    Return {best['return_pct']:.2f}% > 0%: {'✅' if gate['return_check'] else '❌'}")
    log.info(f"    DD {best['max_drawdown']:.2f}% > -25%: {'✅' if gate['dd_check'] else '❌'}")
    
    # Save
    report = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "strategy": "DhaherSystem",
        "method": "SL/TP-aware backtest (not continuous position-hold)",
        "configs_tested": len(configs),
        "results": results,
        "best": best,
        "gate": gate,
    }
    report_file = RESULT / f"dhaher_sltp_backtest_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str))
    log.info(f"📁 Saved: {report_file}")
    return report


if __name__ == "__main__":
    main()