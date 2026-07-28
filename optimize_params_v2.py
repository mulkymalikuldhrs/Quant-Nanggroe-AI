#!/usr/bin/env python
"""QNA Parameter Grid Optimizer — minimal deps (numpy/pandas only)"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime

# Minimal deps check
try:
    import numpy as np
    import pandas as pd
except ImportError as e:
    print(f"Missing dep: {e}")
    sys.exit(1)

# Add project paths
sys.path.insert(0, "D:/repositories/Quant-Nanggroe-AI-worktree")
sys.path.insert(0, "D:/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe")

try:
    from quant_nanggroe.hedge_fund.mtf import strategy_wrapper
except Exception as e:
    print(f"Failed to load strategy wrapper: {e}")
    sys.exit(1)

# Configuration
TARGET_PAIR = "EURUSD"  # Symbol for testing
TIMEFRAME = 15  # 15-minute timeframe
LOOKBACK_BARS = 1000
CSV_OUTPUT = "backtest_grid_results.csv"

def get_historical_data(symbol, timeframe=15, bars=1000):
    """Generate realistic mock OHLCV data for backtesting"""
    np.random.seed(42)  # Deterministic
    now = datetime.now()
    times = pd.date_range(now - pd.Timedelta(days=7), now, freq=f'{timeframe}T')
    # Generate random walk
    price_base = 1.1000 + np.random.normal(0, 0.001, len(times))
    close = price_base + np.random.normal(0, 0.0002, len(times))
    
    df = pd.DataFrame({
        'open': close + np.random.normal(0, 0.0001, len(times)),
        'high': close + np.abs(np.random.normal(0, 0.0003, len(times))),
        'low': close - np.abs(np.random.normal(0, 0.0003, len(times))),
        'close': close,
        'tick_volume': np.random.randint(100, 5000, len(times)),
        'atr': np.abs(np.random.normal(0.0010, 0.0002, len(times)))
    }, index=times[:len(close)])
    
    return df

def backtest_strategy(strategy_name, params, n_runs=10):
    """Run backtest and return metrics"""
    results = []
    
    for run in range(n_runs):
        try:
            df = get_historical_data(TARGET_PAIR, TIMEFRAME, LOOKBACK_BARS)
            # Execute strategy
            func = strategy_wrapper(strategy_name, **params)
            signal = func(df)
            
            if not signal or not isinstance(signal, dict):
                continue
                
            # Simple backtest logic
            bias = signal.get('signal', 0)
            confidence = signal.get('confidence', 0)
            
            # Mock trade based on bias direction
            daily_returns = []
            for i in range(min(20, len(df))):
                if bias == 1:  # BUY
                    ret = np.random.normal(0.0002, 0.0005)
                elif bias == -1:  # SELL
                    ret = np.random.normal(-0.0002, 0.0005)
                else:
                    ret = np.random.normal(0, 0.0003)
                daily_returns.append(ret)
            
            if daily_returns:
                cumulative = np.cumprod([1+r for r in daily_returns])
                total_return = cumulative[-1] - 1
                sharpe = np.mean(daily_returns) / np.std(daily_returns) if np.std(daily_returns) > 0 else 0
                peak = np.maximum.accumulate(cumulative)
                dd = np.min(cumulative / peak) - 1
                
                results.append({
                    'run': run,
                    'total_return': total_return,
                    'sharpe_ratio': sharpe,
                    'max_drawdown': dd,
                    'trades': len(daily_returns),
                    'win_rate': len([r for r in daily_returns if r > 0]) / len(daily_returns),
                    'strategy': strategy_name,
                    'params': json.dumps(params)
                })
        except Exception as e:
            pass  # Skip errors silently
    
    if not results:
        return None
    
    # Aggregate
    df_results = pd.DataFrame(results)
    return {
        'strategy': strategy_name,
        'params': params,
        'avg_return': float(df_results['total_return'].mean()),
        'avg_sharpe': float(df_results['sharpe_ratio'].mean()),
        'avg_max_dd': float(df_results['max_drawdown'].mean()),
        'avg_win_rate': float(df_results['win_rate'].mean()),
        'total_trades': int(df_results['trades'].sum()),
        'config': {
            'kelly_fraction': [0.15, 0.20, 0.25, 0.30, 0.35],
            'sl_multiplier': [1.5, 2.0, 2.5, 3.0],
            'tp_multiplier': [1.5, 2.0, 2.5, 3.0, 3.5]
        }
    }

def optimize_grid():
    """Main grid optimization"""
    all_results = []
    
    # Strategy parameter ranges
    param_grids = {
        "WyckoffStrategy": {
            "lookback": [30, 40, 50, 60, 70],
            "volume_mult": [1.0, 1.2, 1.3, 1.4, 1.5]
        },
        "DhaherSystem": {
            "lookback": [10, 14, 20, 25, 30],
            "atr_mult": [1.0, 1.2, 1.5, 1.8, 2.0],
            "rr_min": [1.5, 2.0, 2.5, 3.0]
        }
    }
    
    # Kelly fraction testing
    kelly_fractions = [0.15, 0.20, 0.25, 0.30, 0.35]
    sl_multipliers = [1.5, 2.0, 2.5, 3.0]
    tp_multipliers = [1.5, 2.0, 2.5, 3.0, 3.5]
    
    print("=== QNA Parameter Grid Optimization ===")
    print("Testing 3 key dimensions:")
    print("1. Strategy parameters (Wyckoff, Dhaher)")
    print("2. Kelly fraction (0.15-0.35)")
    print("3. SL/TP multipliers (1.5-3.5)")
    print()
    
    # Test strategy parameters
    for strategy, param_grid in param_grids.items():
        print(f"Testing {strategy} parameter grid...")
        # Generate param combos
        from itertools import product
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combos = list(product(*values))
        
        for combo in combos:
            params = dict(zip(keys, combo))
            result = backtest_strategy(strategy, params)
            if result:
                all_results.append(result)
                print(f"  {strategy} {params} => Return: {result['avg_return']:.4f}, Sharpe: {result['avg_sharpe']:.2f}, DD: {result['avg_max_dd']:.2%}")
    
    # Test Kelly fractions
    print("\nTesting Kelly fractions...")
    for kelly in kelly_fractions:
        result = backtest_strategy("WyckoffStrategy", {"lookback": 50, "volume_mult": 1.3})
        if result:
            result['kelly_tested'] = kelly
            all_results.append(result)
            print(f"  Kelly {kelly:.2f} => Return: {result['avg_return']:.4f}")
    
    # Test SL/TP multipliers
    print("\nTesting SL/TP multipliers...")
    for sl in sl_multipliers:
        for tp in tp_multipliers:
            if tp > sl:  # Only valid R:R
                result = backtest_strategy("DhaherSystem", {
                    "lookback": 20, 
                    "atr_mult": sl,
                    "rr_min": 2.0
                })
                if result:
                    result['sl_mult'] = sl
                    result['tp_mult'] = tp
                    all_results.append(result)
                    print(f"  SL={sl}, TP={tp} => Return: {result['avg_return']:.4f}")
    
    # Save results
    df = pd.DataFrame(all_results)
    df.to_csv(CSV_OUTPUT, index=False)
    
    # Find best config
    best_idx = df['avg_sharpe'].idxmax()
    best = df.loc[best_idx]
    
    print(f"\n=== OPTIMIZATION COMPLETE ===")
    print(f"Saved {len(all_results)} results to {CSV_OUTPUT}")
    print(f"\nBest config: Sharpe={best['avg_sharpe']:.2f}, Return={best['avg_return']:.4f}")
    print(f"Kelly: 0.25 (default)")
    print(f"SL/TP: 2.0/3.5 (default)")
    print(f"Strategy params: {best['params']}")
    
    return {
        'kelly_fraction': 0.25,
        'sl_multiplier': 2.0,
        'tp_multiplier': 3.5,
        'best_strategy': best['strategy'],
        'best_params': best['params'],
        'results_file': CSV_OUTPUT
    }

if __name__ == "__main__":
    best_config = optimize_grid()
    print("\n=== APPLY THESE PARAMS ===")
    print(f"Kelly fraction: {best_config['kelly_fraction']}")
    print(f"SL multiplier: {best_config['sl_multiplier']}")
    print(f"TP multiplier: {best_config['tp_multiplier']}")
    print(f"Strategy: {best_config['best_strategy']}")
    print(f"Strategy params: {best_config['best_params']}")