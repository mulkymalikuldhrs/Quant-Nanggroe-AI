"""
Backtesting Pipeline — semua strategi diuji dulu sebelum eksekusi
Backtest → Walk-Forward → Demo → Real
"""
import sys, json, time, logging, csv
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

SRC = Path(r'E:/trading')
DATA = SRC / 'data'
RESULT = SRC / 'results'
RESULT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('bt')

# ── Data Loader ──
def get_historical(symbol="EURUSD", days=365, tf="M15"):
    """Ambil data history dari MT5"""
    import MetaTrader5 as mt5
    tfs = {"M1":1, "M5":5, "M15":15, "M30":30, "H1":60, "H4":240, "D1":1440}
    tf_mt5 = tfs.get(tf, 15)
    
    # Convert MT5 timeframe to constant
    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15,
              30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4,
              1440: mt5.TIMEFRAME_D1}
    
    if not mt5.initialize():
        log.error("MT5 init failed"); return None
    
    now = datetime.now()
    from_date = now - timedelta(days=days)
    rates = mt5.copy_rates_range(symbol, tf_map[tf_mt5], from_date, now)
    mt5.shutdown()
    
    if rates is None or len(rates) < 100:
        log.error(f"Not enough data: {len(rates) if rates else 0}")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# ── Strategy SMA ──
class StrategySMA:
    """SMA/EMA crossover — tanpa RSI dulu, fix logic"""
    def __init__(self, fast=12, slow=26, use_ema=True):
        self.fast = fast
        self.slow = slow
        self.use_ema = use_ema
        self.name = f"{'EMA' if use_ema else 'SMA'}{fast}/{slow}"
    
    def generate_signals(self, df):
        df = df.copy()
        if self.use_ema:
            df['ma_fast'] = df['close'].ewm(span=self.fast).mean()
            df['ma_slow'] = df['close'].ewm(span=self.slow).mean()
        else:
            df['ma_fast'] = df['close'].rolling(window=self.fast).mean()
            df['ma_slow'] = df['close'].rolling(window=self.slow).mean()
        # Signal: 1=buy (fast>slow), -1=sell (fast<slow)
        df['signal'] = np.where(df['ma_fast'] > df['ma_slow'], 1, -1)
        C = len(df)
        # Only take entry on cross, hold until opposite cross
        df['entry'] = 0
        # First signal using iloc (positional, works with datetime index)
        sig_col = df.columns.get_loc('signal')
        ent_col = df.columns.get_loc('entry')
        current_sig = df.iat[0, sig_col]
        if current_sig != 0:
            df.iat[0, ent_col] = current_sig
        for i in range(1, C):
            sig = df.iat[i, sig_col]
            prev_sig = df.iat[i-1, sig_col]
            if sig != prev_sig:
                df.iat[i, ent_col] = sig
        return df

# ── Backtest Engine ──
def backtest(df, strategy, initial_capital=1000):
    """Backtest dengan dynamic lot sizing"""
    data = strategy.generate_signals(df)
    lot = round(max(0.01, initial_capital / 10000), 2)  # dinamis
    
    capital = float(initial_capital)
    position = 0  # 0=none, 1=buy, -1=sell
    trades = []
    equity_curve = [initial_capital] * len(data)
    entry_price = 0
    
    for i in range(len(data)):
        row = data.iloc[i]
        price = row['close']
        
        # Handle entry signal
        if row['entry'] == 1 and position != 1:
            if position == -1:  # Close sell first
                pnl = (entry_price - price) * lot * 100000
                capital += pnl
                trades.append({"type":"close_sell","price":price,"pnl":pnl,"time":row.name})
            position = 1
            entry_price = price
            trades.append({"type":"open_buy","price":price,"time":row.name})
        elif row['entry'] == -1 and position != -1:
            if position == 1:  # Close buy first
                pnl = (price - entry_price) * lot * 100000
                capital += pnl
                trades.append({"type":"close_buy","price":price,"pnl":pnl,"time":row.name})
            position = -1
            entry_price = price
            trades.append({"type":"open_sell","price":price,"time":row.name})
        
        # Current equity
        if position == 1:
            equity = capital + (price - entry_price) * lot * 100000
        elif position == -1:
            equity = capital + (entry_price - price) * lot * 100000
        else:
            equity = capital
        equity_curve[i] = equity
    
    # Close final position
    if position != 0:
        last_price = data.iloc[-1]['close']
        if position == 1:
            pnl = (last_price - entry_price) * lot * 100000
        else:
            pnl = (entry_price - last_price) * lot * 100000
        capital += pnl
        trades.append({"type":"final_close","price":last_price,"pnl":pnl,"time":data.index[-1]})
    
    # Metrics
    eq = pd.Series(equity_curve, index=data.index)
    total_return = capital - initial_capital
    ret_pct = (capital - initial_capital) / initial_capital * 100
    ret_s = eq.pct_change().dropna()
    sharpe = np.sqrt(35040) * ret_s.mean() / ret_s.std() if ret_s.std() > 0 else 0
    peak = eq.expanding().max()
    dd = ((eq - peak) / peak).min() * 100
    
    closed = [t for t in trades if 'pnl' in t and t.get('type','').startswith(('close','final'))]
    wins = [t for t in closed if t['pnl'] > 0]
    wr = len(wins)/len(closed)*100 if closed else 0
    
    return {
        "strategy": strategy.name,
        "initial_capital": initial_capital, "final_capital": round(capital,2),
        "total_return": round(total_return,2), "return_pct": round(ret_pct,2),
        "sharpe": round(sharpe,3), "max_drawdown": round(dd,2),
        "win_rate": round(wr,1), "total_trades": len(trades), "closed_trades": len(closed),
    }, trades, eq

# ── Walk-Forward ──
def walk_forward(df, strategy, folds=5, train_ratio=0.7, initial_capital=1000):
    """Walk-forward: train → test bergeser"""
    n = len(df)
    fold_size = n // folds
    results = []
    
    for fold in range(folds - 1):
        train_end = int((fold + 1) * fold_size * train_ratio + fold * fold_size * (1 - train_ratio))
        test_start = min(train_end, n)
        test_end = min(test_start + fold_size, n)
        
        if test_start >= test_end:
            break
        
        train_df = df.iloc[:train_end]
        test_df = df.iloc[test_start:test_end]
        
        if len(test_df) < 50:
            break
        
        # Train on train set (SMA doesn't need training, but walk-forward validates robustness)
        result, trades, _ = backtest(test_df, strategy, initial_capital)
        result["fold"] = fold + 1
        result["train_period"] = f"{train_df.index[0].date()} - {train_df.index[-1].date()}"
        result["test_period"] = f"{test_df.index[0].date()} - {test_df.index[-1].date()}"
        result["test_bars"] = len(test_df)
        results.append(result)
    
    if not results:
        return {"error": "Not enough data for walk-forward"}
    
    # Aggregate
    avg_return = np.mean([r["return_pct"] for r in results])
    avg_sharpe = np.mean([r["sharpe"] for r in results if r["sharpe"] != 0])
    avg_dd = np.mean([r["max_drawdown"] for r in results])
    avg_win = np.mean([r["win_rate"] for r in results if r["win_rate"] != 0])
    
    return {
        "strategy": strategy.__class__.__name__,
        "folds": len(results),
        "avg_return_pct": round(avg_return, 2),
        "avg_sharpe": round(avg_sharpe, 3),
        "avg_max_dd_pct": round(avg_dd, 2),
        "avg_win_rate": round(avg_win, 1),
        "fold_results": results,
        "conclusion": "✅ PAS" if avg_sharpe > 0.5 and avg_return > 0 else "❌ GAGAL"
    }

# ── Gate decision ──
def gate_decision(wf_result):
    hasil = {"pass": False, "reason": "", "checks": []}
    if wf_result.get("error"):
        hasil["reason"] = wf_result["error"]
        return hasil
    
    checks = [
        (wf_result["avg_sharpe"] > 0.5, f"Sharpe {wf_result['avg_sharpe']} > 0.5"),
        (wf_result["avg_return_pct"] > 0, f"Return {wf_result['avg_return_pct']}% > 0%"),
        (wf_result["avg_max_dd_pct"] > -25, f"Drawdown {wf_result['avg_max_dd_pct']}% > -25%"),
    ]
    
    hasil["pass"] = all(c[0] for c in checks)
    hasil["reason"] = "✅ Lolos" if hasil["pass"] else f"❌ Gagal: {', '.join(c[1] for c in checks if not c[0])}"
    hasil["checks"] = [list(c) for c in checks]  # convert tuple to list for JSON
    return hasil

# ── Main ──
def run():
    log.info("═══ Backtest Pipeline ═══")
    
    symbol = "EURUSD"
    log.info(f"Loading {symbol} data...")
    df = get_historical(symbol, days=365, tf="M15")
    if df is None:
        log.error("Data unavailable"); return
    
    log.info(f"Data: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}")
    
    # 1. Full backtest — test multiple params
    log.info("📊 Testing multiple EMA/SMA strategies...")
    
    params = [
        ("EMA12/26", StrategySMA(12,26, True)),
        ("EMA5/13", StrategySMA(5,13, True)),
        ("EMA8/21", StrategySMA(8,21, True)),
        ("EMA20/50", StrategySMA(20,50, True)),
        ("SMA5/13", StrategySMA(5,13, False)),
        ("SMA10/30", StrategySMA(10,30, False)),
    ]
    best = None
    for name, strat in params:
        r, _, _ = backtest(df, strat, initial_capital=1000)
        wf = walk_forward(df, strat, folds=5)
        gate = gate_decision(wf)
        log.info(f"   {name}: Ret={r['return_pct']}% SR={r['sharpe']} WF={wf['avg_return_pct']}% Gate={'✅' if gate['pass'] else '❌'}")
        if gate['pass'] and (best is None or wf['avg_sharpe'] > best['sharpe']):
            best = {"name": name, "strategy": strat, "result": r, "walkforward": wf}
    
    if best:
        log.info(f"🏆 BEST: {best['name']} — Sharpe {best['walkforward']['avg_sharpe']}")
        bt_result, trades, equity = backtest(df, best['strategy'])
        wf = best['walkforward']
    else:
        log.info("⚠️ No strategy passes gate — using best available")
        log.info("🔄 Walk-forward default SMA...")
        wf = walk_forward(df, StrategySMA(fast=5, slow=13), folds=5)
    log.info(f"   Avg return: {wf['avg_return_pct']}% | Sharpe: {wf['avg_sharpe']} | DD: {wf['avg_max_dd_pct']}%")
    
    # 3. Gate decision
    log.info("🚦 Gate decision...")
    gate = gate_decision(wf)
    log.info(f"   {gate['reason']} | {gate.get('checks','')}")
    
    # Save
    report = {"symbol": symbol, "backtest": bt_result, "walkforward": wf, "gate": gate}
    report_file = RESULT / f"backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str))
    log.info(f"Report saved: {report_file}")
    
    # Log trades
    trade_file = RESULT / f"trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    with open(trade_file, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=["type","price","pnl","time"])
        w.writeheader()
        for t in trades:
            t_clean = {k: (str(v) if hasattr(v, 'strftime') else v) for k, v in t.items()}
            w.writerow(t_clean)
    
    return report

if __name__ == "__main__":
    report = run()
    if report:
        print("\n=== RESULT ===")
        try:
            b = report.get("best", {})
            if b:
                print(f"🏆 Best: {b.get('name','?')} | Ret={b.get('result',{}).get('return_pct','?')}% | Sharpe={b.get('walkforward',{}).get('avg_sharpe','?')}")
                print(f"✅ Gate: LULUS — strategi siap demo")
            else:
                wf = report.get("walkforward", {})
                print(f"❌ Gate: SEMUA GAGAL — tidak ada strategi yang lolos")
                print(f"   Best WF return: {wf.get('avg_return_pct','?')}%")
        except: pass
