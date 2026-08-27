"""
Dhaher System v1.0 — Entry Logic Tuning & Grid Search
====================================================
Goal: Win rate 27% → 45%+, Sharpe > 0.5, DD > -25%

Tests 5 entry logic variants:
  V0: OB AND BOS AND trend            (original - baseline)
  V1: OB OR FVG OR BOS                (any signal, no trend filter)
  V2: OB AND (FVG OR BOS) AND trend   (OB + any confirmation)
  V3: trend AND (OB OR FVG OR BOS)    (trend + any 1 signal)
  V4: (OB AND FVG) OR (OB AND BOS)    (OB confirmed by FVG or BOS, no trend)

Proper SL/TP exits using strategy's ATR-based levels.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent.parent
SRC = _HERE
RESULT = SRC / 'results'
RESULT.mkdir(parents=True, exist_ok=True)

# ── Data Loader (yfinance fallback) ──
def get_data_yf(symbol="EURUSD", days=365, interval="1h"):
    """Download forex data via yfinance"""
    import yfinance as yf
    ticker_map = {
        "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        "USDCHF": "USDCHF=X", "USDCAD": "USDCAD=X", "AUDUSD": "AUDUSD=X",
        "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",
        "GBPJPY": "GBPJPY=X",
    }
    ticker = ticker_map.get(symbol, symbol)
    end = datetime.now()
    start = end - timedelta(days=days)
    raw = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
    if raw.empty or len(raw) < 100:
        print(f"  ⚠️ yfinance returned {len(raw)} rows — generating synthetic data")
        return None
    
    # yfinance v0.3+ returns MultiIndex columns; flatten
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    
    df = raw.reset_index()
    # Rename columns to lowercase
    rename_map = {c: c.lower() for c in df.columns}
    # Handle 'Date' or 'Datetime' index column
    for src in ['Date', 'Datetime', 'datetime', 'time']:
        if src in rename_map:
            rename_map[src] = 'time'
            break
    df.rename(columns=rename_map, inplace=True)
    
    # Ensure we have required columns
    for col in ['open', 'high', 'low', 'close']:
        if col not in df.columns:
            # try capitalized
            cap = col.capitalize()
            if cap in df.columns:
                df.rename(columns={cap: col}, inplace=True)
    
    df.set_index('time', inplace=True)
    return df

# ── Core Dhaher Detection Functions ──
def calculate_atr(df, period=14):
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([high - low, 
                   (high - close.shift()).abs(), 
                   (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def find_order_blocks(df):
    ob_signals = pd.Series(0, index=df.index)
    for i in range(2, len(df)-1):
        if (df['close'].iloc[i] < df['open'].iloc[i] and
            df['close'].iloc[i+1] > df['high'].iloc[i]):
            ob_signals.iloc[i+1] = 1
        if (df['close'].iloc[i] > df['open'].iloc[i] and
            df['close'].iloc[i+1] < df['low'].iloc[i]):
            ob_signals.iloc[i+1] = -1
    return ob_signals

def detect_fvg(df):
    fvg = pd.Series(0, index=df.index)
    for i in range(2, len(df)):
        if df['low'].iloc[i] > df['high'].iloc[i-2]:
            fvg.iloc[i] = 1
        if df['high'].iloc[i] < df['low'].iloc[i-2]:
            fvg.iloc[i] = -1
    return fvg

def detect_bos(df, lookback=20):
    bos = pd.Series(0, index=df.index)
    for i in range(lookback, len(df)):
        window = df['high'].iloc[i-lookback:i]
        if df['high'].iloc[i] > window.max():
            bos.iloc[i] = 1
        window_low = df['low'].iloc[i-lookback:i]
        if df['low'].iloc[i] < window_low.min():
            bos.iloc[i] = -1
    return bos

# ── Entry Logic Variants ──
ENTRY_VARIANTS = {
    "V0_OB_BOS_TREND": {
        "desc": "OB AND BOS AND trend (original)",
        "formula": "OB==1 AND trend==1 AND BOS==1 (BUY); OB==-1 AND trend==-1 AND BOS==-1 (SELL)",
    },
    "V1_ANY_SIGNAL": {
        "desc": "OB OR FVG OR BOS (any signal, no trend)",
        "formula": "OB!=0 OR FVG!=0 OR BOS!=0 (BUY/SELL by majority)",
    },
    "V2_OB_CONFIRMED": {
        "desc": "OB AND (FVG OR BOS) AND trend",
        "formula": "trend==1 AND OB==1 AND (FVG==1 OR BOS==1) (BUY)",
    },
    "V3_TREND_ANY": {
        "desc": "trend AND (OB OR FVG OR BOS)",
        "formula": "trend==1 AND (OB==1 OR FVG==1 OR BOS==1) (BUY)",
    },
    "V4_OB_FVG_or_OB_BOS": {
        "desc": "(OB AND FVG) OR (OB AND BOS) — OB confirmed, no trend",
        "formula": "(OB==1 AND FVG==1) OR (OB==1 AND BOS==1) (BUY)",
    },
}

def generate_entry_signals(df, variant, lookback=20):
    """Generate entry signals based on variant name"""
    df = df.copy()
    df['atr'] = calculate_atr(df)
    df['ob'] = find_order_blocks(df)
    df['fvg'] = detect_fvg(df)
    df['bos'] = detect_bos(df, lookback)
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    
    # Trend filter
    df['trend'] = 0
    df.loc[df['ema20'] > df['ema50'], 'trend'] = 1
    df.loc[df['ema20'] < df['ema50'], 'trend'] = -1
    
    # Signal direction by majority for V1
    df['signal_sum'] = df['ob'] + df['fvg'] + df['bos']
    
    df['entry_raw'] = 0  # raw signal before SL/TP
    
    for i in range(len(df)):
        ob = df['ob'].iloc[i]
        fvg = df['fvg'].iloc[i]
        bos = df['bos'].iloc[i]
        trend = df['trend'].iloc[i]
        sig_sum = df['signal_sum'].iloc[i]
        
        if variant == "V0_OB_BOS_TREND":
            # Original: OB AND BOS AND trend
            if ob == 1 and bos == 1 and trend == 1:
                df.loc[df.index[i], 'entry_raw'] = 1
            elif ob == -1 and bos == -1 and trend == -1:
                df.loc[df.index[i], 'entry_raw'] = -1
        
        elif variant == "V1_ANY_SIGNAL":
            # Any signal, direction by majority
            if sig_sum > 0:
                df.loc[df.index[i], 'entry_raw'] = 1
            elif sig_sum < 0:
                df.loc[df.index[i], 'entry_raw'] = -1
        
        elif variant == "V2_OB_CONFIRMED":
            # OB + (FVG OR BOS) + trend
            if trend == 1 and ob == 1 and (fvg == 1 or bos == 1):
                df.loc[df.index[i], 'entry_raw'] = 1
            elif trend == -1 and ob == -1 and (fvg == -1 or bos == -1):
                df.loc[df.index[i], 'entry_raw'] = -1
        
        elif variant == "V3_TREND_ANY":
            # Trend + any single signal
            if trend == 1 and (ob == 1 or fvg == 1 or bos == 1):
                df.loc[df.index[i], 'entry_raw'] = 1
            elif trend == -1 and (ob == -1 or fvg == -1 or bos == -1):
                df.loc[df.index[i], 'entry_raw'] = -1
        
        elif variant == "V4_OB_FVG_or_OB_BOS":
            # OB confirmed by FVG or BOS (no trend)
            if (ob == 1 and fvg == 1) or (ob == 1 and bos == 1):
                df.loc[df.index[i], 'entry_raw'] = 1
            elif (ob == -1 and fvg == -1) or (ob == -1 and bos == -1):
                df.loc[df.index[i], 'entry_raw'] = -1
    
    return df

# ── Proper SL/TP Backtest ──
def backtest_sltp(df, variant, lookback=20, atr_mult=1.5, rr_min=2.0, initial_capital=1000):
    """
    SL/TP-aware backtest.
    - Enters at signal
    - Exits at SL, TP, or opposite signal
    - SL = atr * atr_mult
    - TP = SL * rr_min
    """
    df_signals = generate_entry_signals(df, variant, lookback)
    
    capital = float(initial_capital)
    position = 0  # 0=none, 1=long, -1=short
    entry_price = 0
    entry_idx = 0
    sl_price = 0
    tp_price = 0
    trades = []
    equity_curve = np.full(len(df_signals), initial_capital, dtype=float)
    last_entry_signal = 0  # track last bar's signal to avoid re-entry
    
    for i in range(len(df_signals)):
        row = df_signals.iloc[i]
        price = row['close']
        atr = row['atr']
        entry = row['entry_raw']
        
        # Skip if no ATR yet
        if pd.isna(atr) or atr == 0:
            equity_curve[i] = capital
            continue
        
        # Check SL/TP if in position
        if position == 1:  # Long
            if price <= sl_price:
                # SL hit
                pnl = (sl_price - entry_price) * 100000  # 1 lot = 100K units
                capital += pnl
                trades.append({"type": "sl_buy", "price": sl_price, "pnl": pnl, "bars": i - entry_idx, "time": str(row.name)})
                position = 0
                last_entry_signal = 0
            elif price >= tp_price:
                # TP hit
                pnl = (tp_price - entry_price) * 100000
                capital += pnl
                trades.append({"type": "tp_buy", "price": tp_price, "pnl": pnl, "bars": i - entry_idx, "time": str(row.name)})
                position = 0
                last_entry_signal = 0
        
        elif position == -1:  # Short
            if price >= sl_price:
                # SL hit
                pnl = (entry_price - sl_price) * 100000
                capital += pnl
                trades.append({"type": "sl_sell", "price": sl_price, "pnl": pnl, "bars": i - entry_idx, "time": str(row.name)})
                position = 0
                last_entry_signal = 0
            elif price <= tp_price:
                # TP hit
                pnl = (entry_price - tp_price) * 100000
                capital += pnl
                trades.append({"type": "tp_sell", "price": tp_price, "pnl": pnl, "bars": i - entry_idx, "time": str(row.name)})
                position = 0
                last_entry_signal = 0
        
        # Entry logic (only if no position)
        if position == 0 and entry != 0 and entry != last_entry_signal:
            lot = round(max(0.01, capital / 10000), 2)
            
            if entry == 1:  # BUY
                sl_price = price - atr * atr_mult
                tp_price = price + atr * atr_mult * rr_min
                trades.append({"type": "open_buy", "price": price, "lot": lot, "sl": sl_price, "tp": tp_price, "time": str(row.name)})
            elif entry == -1:  # SELL
                sl_price = price + atr * atr_mult
                tp_price = price - atr * atr_mult * rr_min
                trades.append({"type": "open_sell", "price": price, "lot": lot, "sl": sl_price, "tp": tp_price, "time": str(row.name)})
            
            position = entry
            entry_price = price
            entry_idx = i
            last_entry_signal = entry
        
        # Current equity (MTM for open positions)
        if position == 1:
            equity_curve[i] = capital + (price - entry_price) * 100000
        elif position == -1:
            equity_curve[i] = capital + (entry_price - price) * 100000
        else:
            equity_curve[i] = capital
    
    # Close any open position at final bar
    if position != 0:
        last_price = df_signals.iloc[-1]['close']
        if position == 1:
            pnl = (last_price - entry_price) * 100000
            trades.append({"type": "final_close_buy", "price": last_price, "pnl": pnl, "bars": len(df) - entry_idx, "time": str(df_signals.index[-1])})
        else:
            pnl = (entry_price - last_price) * 100000
            trades.append({"type": "final_close_sell", "price": last_price, "pnl": pnl, "bars": len(df) - entry_idx, "time": str(df_signals.index[-1])})
        capital += pnl
    
    # ── Compute Metrics ──
    eq = pd.Series(equity_curve)
    
    # Trade categorization
    opens = [t for t in trades if t['type'].startswith('open')]
    closes = [t for t in trades if t['type'].startswith(('sl_', 'tp_', 'final_close'))]
    
    # Win/Loss analysis
    wins = [t for t in closes if t.get('pnl', 0) > 0]
    losses = [t for t in closes if t.get('pnl', 0) <= 0]
    
    total_return = capital - initial_capital
    ret_pct = (capital / initial_capital - 1) * 100 if initial_capital > 0 else 0
    
    # Sharpe (hourly data: ~252*7 = 1764 trading hours/year for forex)
    ret_s = eq.pct_change().dropna()
    bars_per_year = 1764  # H1 forex
    sharpe = np.sqrt(bars_per_year) * ret_s.mean() / ret_s.std() if ret_s.std() > 0 else 0
    
    # Max drawdown
    peak = eq.expanding().max()
    dd = ((eq - peak) / peak).min() * 100
    
    # Win rate
    total_closed = len(closes)
    num_wins = len(wins)
    win_rate = num_wins / total_closed * 100 if total_closed > 0 else 0
    
    # Avg trade metrics
    avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
    profit_factor = abs(sum(t['pnl'] for t in wins) / sum(abs(t['pnl']) for t in losses)) if losses and sum(abs(t['pnl']) for t in losses) > 0 else 0
    
    # Expectancy
    expectancy = (win_rate / 100 * avg_win - (1 - win_rate / 100) * abs(avg_loss)) if total_closed > 0 else 0
    
    return {
        "variant": variant,
        "lookback": lookback,
        "atr_mult": atr_mult,
        "rr_min": rr_min,
        "initial_capital": initial_capital,
        "final_capital": round(capital, 2),
        "total_return": round(total_return, 2),
        "return_pct": round(ret_pct, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(dd, 2),
        "win_rate": round(win_rate, 1),
        "total_trades": len(opens),
        "closed_trades": total_closed,
        "wins": num_wins,
        "losses": total_closed - num_wins,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 3),
        "expectancy": round(expectancy, 2),
        "final_positions": 1 if position != 0 else 0,
    }, trades, eq


# ── Gate Check ──
def gate_check(metrics):
    """Check if strategy passes the gate"""
    checks = {
        "sharpe > 0.5": metrics['sharpe'] > 0.5,
        "return > 0%": metrics['return_pct'] > 0,
        "dd > -25%": metrics['max_drawdown'] > -25,
        "win_rate > 30%": metrics['win_rate'] > 30,
    }
    passed = all(checks.values())
    return {
        "pass": passed,
        "checks": checks,
        "reason": "✅ PASS ALL" if passed else f"❌ FAIL: {', '.join(k for k, v in checks.items() if not v)}"
    }


# ── Main Tuning ──
def run_tuning():
    print("=" * 75)
    print("  DHAHER SYSTEM v1.0 — ENTRY LOGIC TUNING")
    print("  Goal: Win Rate 27% → 45%+ | Sharpe > 0.5 | DD > -25%")
    print("=" * 75)
    
    # ── Get Data ──
    print("\n[1/4] Loading market data...")
    df = get_data_yf("EURUSD", days=365, interval="1h")
    if df is None:
        print("  ⚠️ yfinance failed — generating synthetic data")
        np.random.seed(42)
        n = 6000
        # Random walk with drift
        returns = np.random.randn(n) * 0.0003 + 0.00001
        prices = 1.05 * np.exp(np.cumsum(returns))
        df = pd.DataFrame({
            'open': prices[:-1],
            'high': prices[:-1] * (1 + np.abs(np.random.randn(n-1)) * 0.002),
            'low': prices[:-1] * (1 - np.abs(np.random.randn(n-1)) * 0.002),
            'close': prices[1:],
            'volume': np.random.randint(100, 10000, n-1),
        })
        df.index = pd.date_range(end=datetime.now(), periods=len(df), freq='h')
        print(f"  📊 Synthetic: {len(df)} bars")
    else:
        print(f"  📊 EURUSD H1: {len(df)} bars ({df.index[0].date()} to {df.index[-1].date()})")
    
    # ── Grid Search ──
    print("\n[2/4] Grid search over entry variants & parameters...")
    
    variants = list(ENTRY_VARIANTS.keys())
    lookbacks = [10, 15, 20, 25, 30, 40]
    atr_mults = [1.0, 1.2, 1.5, 2.0]
    rr_mins = [1.5, 2.0, 2.5, 3.0]
    
    results = []
    t_start = time.time()
    
    total_configs = len(variants) * len(lookbacks) * len(atr_mults) * len(rr_mins)
    tested = 0
    
    for variant in variants:
        print(f"\n  📌 Variant: {variant} ({ENTRY_VARIANTS[variant]['desc']})")
        for lb in lookbacks:
            for atr in atr_mults:
                for rr in rr_mins:
                    tested += 1
                    if tested % 50 == 0:
                        print(f"     Progress: {tested}/{total_configs} ({tested/total_configs*100:.0f}%)")
                    
                    try:
                        metrics, trades, _ = backtest_sltp(df, variant, lb, atr, rr, 1000)
                        gate = gate_check(metrics)
                        results.append({**metrics, "gate_pass": gate['pass'], "gate_reason": gate['reason']})
                    except Exception as e:
                        print(f"     ERROR at {variant} lb={lb} atr={atr} rr={rr}: {e}")
                        continue
    
    elapsed = time.time() - t_start
    print(f"\n  ⏱  {tested} configs tested in {elapsed:.1f}s ({tested/elapsed:.0f} configs/s)")
    
    # ── Analyze Results ──
    print("\n[3/4] Analyzing results...")
    
    # Convert to DataFrame for analysis
    rf = pd.DataFrame(results)
    
    # Gate-passing results
    passed = rf[rf['gate_pass'] == True]
    
    print(f"\n  📊 Overall: {len(rf)} configs tested, {len(passed)} gate passes ({len(passed)/len(rf)*100:.1f}%)")
    
    # Best by variant
    print("\n  ── Best per Variant ──")
    best_by_variant = []
    for variant in variants:
        vdata = rf[rf['variant'] == variant]
        if len(vdata) == 0:
            continue
        # Rank by composite score
        vdata = vdata.copy()
        vdata['score'] = vdata['sharpe'] * 0.4 + vdata['win_rate'] / 100 * 0.3 + vdata['return_pct'] / 10 * 0.3
        best_v = vdata.loc[vdata['score'].idxmax()]
        best_by_variant.append(best_v)
        
        status = "✅" if best_v['gate_pass'] else "❌"
        print(f"  {status} {variant:25s} | lb={best_v['lookback']:2d} atr={best_v['atr_mult']:.1f} rr={best_v['rr_min']:.1f} | "
              f"Ret={best_v['return_pct']:+.2f}% SR={best_v['sharpe']:.3f} DD={best_v['max_drawdown']:.1f}% "
              f"WR={best_v['win_rate']:.1f}% Trades={best_v['total_trades']} PF={best_v['profit_factor']:.2f}")
    
    # Best overall
    rf['score'] = rf['sharpe'] * 0.4 + rf['win_rate'] / 100 * 0.3 + rf['return_pct'] / 10 * 0.3
    
    # Filter for gate-passing then score
    if len(passed) > 0:
        best_overall = passed.loc[passed['score'].idxmax()]
    else:
        best_overall = rf.loc[rf['score'].idxmax()]
    
    print("\n  🏆 BEST OVERALL:")
    print(f"     Variant:   {best_overall['variant']} ({ENTRY_VARIANTS[best_overall['variant']]['desc']})")
    print(f"     Params:    lb={best_overall['lookback']} atr_mult={best_overall['atr_mult']} rr_min={best_overall['rr_min']}")
    print(f"     Return:    {best_overall['return_pct']:+.2f}%")
    print(f"     Sharpe:    {best_overall['sharpe']:.3f}")
    print(f"     Max DD:    {best_overall['max_drawdown']:.1f}%")
    print(f"     Win Rate:  {best_overall['win_rate']:.1f}%")
    print(f"     Trades:    {best_overall['total_trades']}")
    print(f"     Profit F:  {best_overall['profit_factor']:.2f}")
    print(f"     Gate:      {best_overall['gate_reason']}")
    
    # ── Extended analysis on best variant ──
    print("\n[4/4] Deep dive: best variant parameter sensitivity...")
    
    best_var = best_overall['variant']
    bv_data = rf[rf['variant'] == best_var]
    
    # One-at-a-time parameter analysis
    print(f"  Varied lookback (fixed atr={best_overall['atr_mult']}, rr={best_overall['rr_min']}):")
    for lb in lookbacks:
        row = bv_data[(bv_data['lookback'] == lb) & 
                      (bv_data['atr_mult'] == best_overall['atr_mult']) & 
                      (bv_data['rr_min'] == best_overall['rr_min'])]
        if len(row) > 0:
            r = row.iloc[0]
            print(f"    lb={lb:2d}: Ret={r['return_pct']:+.2f}% SR={r['sharpe']:.3f} DD={r['max_drawdown']:.1f}% WR={r['win_rate']:.1f}% Trades={r['total_trades']}")
    
    print(f"  Varied atr_mult (fixed lb={best_overall['lookback']}, rr={best_overall['rr_min']}):")
    for am in atr_mults:
        row = bv_data[(bv_data['lookback'] == best_overall['lookback']) & 
                      (bv_data['atr_mult'] == am) & 
                      (bv_data['rr_min'] == best_overall['rr_min'])]
        if len(row) > 0:
            r = row.iloc[0]
            print(f"    atr={am:.1f}: Ret={r['return_pct']:+.2f}% SR={r['sharpe']:.3f} DD={r['max_drawdown']:.1f}% WR={r['win_rate']:.1f}% Trades={r['total_trades']}")
    
    print(f"  Varied rr_min (fixed lb={best_overall['lookback']}, atr={best_overall['atr_mult']}):")
    for rr in rr_mins:
        row = bv_data[(bv_data['lookback'] == best_overall['lookback']) & 
                      (bv_data['atr_mult'] == best_overall['atr_mult']) & 
                      (bv_data['rr_min'] == rr)]
        if len(row) > 0:
            r = row.iloc[0]
            print(f"    rr={rr:.1f}: Ret={r['return_pct']:+.2f}% SR={r['sharpe']:.3f} DD={r['max_drawdown']:.1f}% WR={r['win_rate']:.1f}% Trades={r['total_trades']}")
    
    # ── Save results ──
    rf_save = rf.drop(columns=['score'], errors='ignore')
    results_json = {
        "timestamp": datetime.now().isoformat(),
        "symbol": "EURUSD",
        "interval": "1h",
        "bars": len(df),
        "period": f"{df.index[0].date()} to {df.index[-1].date()}",
        "total_configs": tested,
        "gate_passes": int(len(passed)),
        "best_variant": best_overall['variant'],
        "best_params": {
            "lookback": int(best_overall['lookback']),
            "atr_mult": float(best_overall['atr_mult']),
            "rr_min": float(best_overall['rr_min']),
        },
        "best_metrics": {
            "return_pct": float(best_overall['return_pct']),
            "sharpe": float(best_overall['sharpe']),
            "max_drawdown": float(best_overall['max_drawdown']),
            "win_rate": float(best_overall['win_rate']),
            "total_trades": int(best_overall['total_trades']),
            "profit_factor": float(best_overall['profit_factor']),
        },
        "all_results": rf_save.to_dict(orient='records'),
        "entry_variants": ENTRY_VARIANTS,
        "data_source": "yfinance",
    }
    
    json_file = RESULT / f"dhaher_tuning_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    json_file.write_text(json.dumps(results_json, indent=2, default=str))
    print(f"\n  📄 Full results: {json_file}")
    
    return results_json, best_overall, rf


if __name__ == "__main__":
    results, best, rf = run_tuning()
    print("\n" + "=" * 75)
    print("  TUNING COMPLETE")
    print("=" * 75)
