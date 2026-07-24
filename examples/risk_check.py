"""Check risk gates before placing a trade — example usage of risk API."""
import logging

logging.basicConfig(level=logging.INFO)

try:
    from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchConfig

    ks = KillSwitch(KillSwitchConfig())

    if ks.can_trade():
        print("Trade allowed — no kill switch active")
    else:
        print(f"Trade blocked — kill switch at level {ks.current_level}")

    warning = ks.check_warning(daily_pnl_pct=-0.8, weekly_pnl_pct=-1.5)
    if warning:
        print("WARNING: Approaching risk limits")
    else:
        print("Risk levels within normal range")

except ImportError as e:
    print(f"Could not import QNA modules: {e}")
except Exception as e:
    print(f"Risk check failed: {e}")
