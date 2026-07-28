#!/usr/bin/env python
"""Grid backtest optimizer for QNA trading parameters"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime

# Add project paths
sys.path.insert(0, "D:/repositories/Quant-Nanggroe-AI-worktree")
sys.path.insert(0, "D:/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe")

try:
    import MetaTrader5 as mt5
    from quant_nanggroe.engine.risk.constants import MAX_RISK_PER_TRADE, MAX_DRAWDOWN_PCT
    from quant_nanggroe.hedge_fund.mtf import BEST_STRATEGIES, strategy_wrapper
except Exception as e:
    print(f"Failed to load imports: {e}")
    sys.exit(1)

# Configuration
TARGET_PAIR = "oAndaEURUSD"  # MT5 symbol format
TIMEFRAME = 15  # 15-minute
LOOKBACK_BARS = 1000
CSV_OUTPUT = "backtest_grid_results.csv"

# Strategy-specific parameters to optimize
STRATEGY_PARAMS = {
    "WyckoffStrategy": ["lookback", "volume_mult"],
    "MeanReversionStrategy": ["k_period", "d_period", "oversold", "overbought"],
    "DhaherSystem": ["lookback", "atr_mult", "rr_min"]
}

def get_historical_data(symbol, timeframe=15, bars=500):
    """Get historical OHLCV data from MT5"""
    # Make sure we're using the correct python for this environment
    import sys
    import pathlib
    pathlib.Path("D:\repositories\Quant-Nanggroe-AI-worktree")
    
    import ctypes
    try:
        api_client = ctypes.WinDLL("api-ms-win-core-path-l1-1-1.dll"
                                 ).GetFullPathNameWW
    except:
        api_client = None
    
    # Try real MT5 data first
    try:
        if not mt5.initialize():
            raise Exception("MT5 init failed")
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            raise Exception("No rates data")
        mt5.shutdown()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df
    except Exception as e:
        print(f"Using mock data: {e}")
    
    # Mock data fallback
    np.random.seed(hash(symbol) % (2**31))
    now = datetime.now()
    times = pd.date_range(now - pd.Timedelta(days=7), now, freq=f'{timeframe}T')
    price = 1.1000 + np.random.normal(0, 0.0005, len(times))
    ohlc = pd.DataFrame({
        'open': price + np.random.uniform(-0.0002, 0.0002, len(times)),
        'high': price + np.abs(np.random.uniform(0, 0.0003, len(times))),
        'low': price - np.abs(np.random.uniform(0, 0.0003, len(times))),
        'close': price + np.random.uniform(-0.0002, 0.0002, len(times)),
        'tick_volume': np.random.randint(100, 5000, len(times))
    }, index=times)
    return ohlc

def execute_strategy(strategy_name, params, df):
    """Execute strategy and return trading signals"""
    try:
        # Create strategy wrapper
        func = strategy_wrapper(strategy_name, **params)
        # Generate signals (this is simplified - actual strategy may need more args)
        signal = func(df)
        return signal
    except Exception as e:
        print(f"Strategy {strategy_name} failed: {e}")
        return None

def drawdown(series):
    """Calculate maximum drawdown from a series of returns"""
    cumulative = (1 + series).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    return drawdown.max()

def backtest_strategy(strategy_name, params, data_params=None, n_runs=5):
    """Run multiple backtests and return metrics"""
    if params is None:
        params = {}
    
    results = []
    for i in range(n_runs):
        # Get data
        df = get_historical_data(TARGET_PAIR, TIMEFRAME, LOOKBACK_BARS)
        
        # Execute strategy
        signal = execute_strategy(strategy_name, params, df)
        if not signal:
            continue
            
        # Simple backtest logic (very simplified)
        bias = signal.get('signal', 0)
        confidence = signal.get('confidence', 0)
        
        # Mock trade execution based on bias
        daily_ret = np.random.normal(0, 0.01)  # Mock daily return
        if bias != 0:
            daily_ret *= 1 if bias == 1 else -1
            
        results.append({
            'run': i,
            'bias': bias,
            'confidence': confidence,
            'daily_return': daily_ret,
            'cumulative_return': np.cumsum([0] + [bias * 0.0005 * i for i in range(len(results))])[-1] if results else 0,
        })
    
    if not results:
        return None
        
    df_results = pd.DataFrame(results)
    cumulative = (1 + df_results['daily_return']).cumprod()
    drawdown_val = drawdown(df_results['daily_return'])
    total_return = cumulative.iloc[-1] - 1
    
    return {
        'total_return': total_return,
        'sharpe_ratio': np.mean(df_results['daily_return']) / np.std(df_results['daily_return']) 
                        if np.std(df_results['daily_return']) > 0 else 0,
        'max_drawdown': drawdown_val,
        'win_rate': df_results[df_results['daily_return'] > 0].shape[0] / len(df_results),
        'trades': len(df_results),
        'details': json.dumps({
            'strategy': strategy_name,
            'params': params,
            'final_cumulative_return': float(cumulative.iloc[-1]) if len(cumulative) > 0 else 0
        })
    }

def optimize_parameters():
    """Main optimization function"""
    all_results = []
    
    # Get registered strategies
    strategies = ["WyckoffStrategy"]  # Start with known gate-passing ones
    
    print("Registering strategy parameters...")
    # Add the strategy parameter ranges
    param_spaces = {
        "WyckoffStrategy": {
            "lookback": range(30, 81, 10),  # 30 to 80 step 10
            "volume_mult": [1.0, 1.2, 1.4, 1.6],  # Different multipliers
            "min_confluence": [1, 2, 3]  # Different confluence levels
        },
        "DhaherSystem": {
            "lookback": range(10, 31, 5),  # 10 to 30 step 5
            "atr_mult": [1.0, 1.2, 1.5, 1.8],  # Different multipliers
            "rr_min": [1.5, 2.0, 2.5, 3.0]    # Different risk-reward ratios
        }
    }
    
    # Generate all parameter combinations for testing
    def generate_combinations(param_space):
        from itertools import product
        keys = list(param_space.keys())
        values = list(param_space.values())
        all_combinations = list(product(*values))
        return [dict(zip(keys, combo)) for combo in all_combinations]
    
    # Run parameter optimization
    for strategy in strategies:
        print(f"Optimizing {strategy}...")
        param_space = param_spaces.get(strategy, {})
        if not param_space:
            continue
            
        combinations = generate_combinations(param_space)
        print(f"  Testing {len(combinations)} parameter combinations")
        
        for params in combinations:
            try:
                result = backtest_strategy(strategy, params)
                if result:
                    all_results.append(result)
                    
                    # Print simple summary
                    if len(all_results) <= 5:  # Only show first few
                        print(f"  {strategy} params={params} - Return={result['total_return']:.4f}, "
                              f"Shr={result['sharpe_ratio']:.2f}, DD={result['max_drawdown']:.2%}")
            except Exception as e:
                print(f"  Error testing {strategy} params={params}: {e}")
    
    # Save results
    if all_results:
        df_results = pd.DataFrame(all_results)
        df_results.to_csv(CSV_OUTPUT, index=False)
        print(f"\nSaved {len(all_results)} results to {CSV_OUTPUT}")
        print("Top 5 highest return strategies:")
        print(df_results.sort_values('total_return', ascending=False)['details'].head(5))
    else:
        print("No backtest results generated!")
    
    return all_results

if __name__ == "__main__":
    print("Starting QNA parameter grid optimization...")
    optimize_results = optimize_parameters()
    
    if optimize_results:
        print("\nOptimization complete. Apply best parameters to:")
        print("- Kelly fraction configuration")
        print("- Dynamic lot sizing factor")
        print("- SL/TP multi-pliers in execution layer")
        print("- Strategy-specific configuration parameters")
    else:
        print("Optimization failed!")