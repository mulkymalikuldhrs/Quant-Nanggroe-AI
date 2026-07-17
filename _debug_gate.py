#!/usr/bin/env python3
"""Debug risk gate error."""
import sys
sys.path.insert(0, ".")
from quant_nanggroe.engine.risk.manager import RiskManager

rm = RiskManager()
rs = rm.state
print(f"peak_equity={rs.peak_equity}, daily_pnl={rs.daily_pnl}, weekly_pnl={rs.weekly_pnl}, trades={rs.trade_count_today}")

try:
    result = rm.check_gate.evaluate(
        symbol="BTC-USD",
        account_balance=rs.peak_equity if rs.peak_equity > 0 else 1_000_000.0,
        daily_pnl=float(rs.daily_pnl),
        weekly_pnl=float(rs.weekly_pnl),
        trade_count_today=int(rs.trade_count_today),
    )
    print(f"Result: {result}")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
