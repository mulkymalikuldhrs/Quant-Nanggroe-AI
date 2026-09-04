# Backtest Engine Specification

## Core Requirements

### Event-Driven Simulation
```
for each bar in historical_data:
    update_prices()
    check_stop_losses_and_take_profits()
    generate_signal(current_state)
    if signal and passes_risk_check():
        execute_order(signal)
        apply_slippage_and_commission()
        update_position()
    track_metrics()
```

### Fill Model
- **Market orders**: Fill at bar close ± slippage (slippage = f(order_size / bar_volume, spread))
- **Limit orders**: Fill if bar low <= limit_price (buy) or bar high >= limit_price (sell)
- **Stop orders**: Trigger if bar price crosses stop level, fill at stop ± slippage
- **Partial fills**: For large orders (>10% of bar volume), model partial fill percentage
- **Rejected orders**: Insufficient margin, price limit not reached

### Commission Model
- Per-trade base commission (e.g., $0.50 or 0.001% of notional)
- Exchange/regulatory fees
- Financing cost for leveraged positions (overnight borrowing rate)
- Slippage cost (separate from commission)

### Metrics to Compute
| Metric | Formula | Target |
|---|---|---|
| Total Return | (final_equity - initial_capital) / initial_capital | > 0 after costs |
| CAGR | (1 + total_return) ^ (252/trading_days) - 1 | > risk-free rate |
| Sharpe Ratio | mean(excess_returns) / std(returns) * sqrt(252) | > 1.0 |
| Sortino Ratio | mean(excess_returns) / std(negative_returns) * sqrt(252) | > 1.5 |
| Calmar Ratio | CAGR / max_drawdown | > 1.0 |
| Max Drawdown | max((peak - trough) / peak) | < 20% |
| Profit Factor | sum(wins) / abs(sum(losses)) | > 1.5 |
| Win Rate | count(wins) / total_trades | > 40% |
| Avg Win / Avg Loss | mean(wins) / abs(mean(losses)) | > 1.5 |
| Recovery Factor | total_return / max_drawdown | > 3.0 |
| Trades per Year | total_trades / years | > 12 |
| Average Holding Period | mean(bar_diff(entry, exit)) | Context-dependent |

### Walk-Forward Protocol
```
1. Define train window (e.g., 2 years) and test window (e.g., 6 months)
2. Optimize parameters on train window
3. Fix parameters, run on test window
4. Record test metrics
5. Roll window forward by test_window_size
6. Repeat until end of data
7. Aggregate test metrics (NOT train metrics)
```

### Parameter Optimization
- Grid search with cross-validation (NOT on full dataset)
- Overfitting detection: compare in-sample vs out-of-sample Sharpe
- Rule of thumb: if in-sample Sharpe > 3x out-of-sample, overfitting is likely
- Minimum trades per parameter combination: 30

### Statistical Significance
- Bootstrap confidence intervals for Sharpe ratio
- Deflated Sharpe Ratio (account for multiple testing)
- p-value for strategy returns > 0
- Minimum backtest length: 3 years daily, 1 year hourly

---


---

> **SSOT:** `CANONICAL.md` v8.1.4 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
