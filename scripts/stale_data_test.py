#!/usr/bin/env python3
"""Manual stale-data test — simulates old data and triggers kill switch.

Usage:
    python scripts/stale_data_test.py [--level 1|2|3] [--no-trigger]

Examples:
    python scripts/stale_data_test.py              # LEVEL_1 (default: 6 min)
    python scripts/stale_data_test.py --level 3     # LEVEL_3 (61 min)
    python scripts/stale_data_test.py --no-trigger  # fresh data, no trigger
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta

from quant_nanggroe.data.monitor import DataFreshnessMonitor
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel
from quant_nanggroe.types.market import TimeFrame


def main():
    parser = argparse.ArgumentParser(description="Test stale data → kill switch.")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], default=1,
                        help="Staleness level to simulate (1=6min, 2=16min, 3=61min)")
    parser.add_argument("--no-trigger", action="store_true",
                        help="Use fresh data — expect no trigger")
    args = parser.parse_args()

    age_map = {1: 6, 2: 16, 3: 61}
    age_minutes = 0 if args.no_trigger else age_map[args.level]

    ks = KillSwitch()
    mon = DataFreshnessMonitor(kill_switch=ks)

    if age_minutes > 0:
        old = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
        mon._last_fetch["BTC/USDT"]["1h"] = old
        print(f"Seeded data {age_minutes} min old for BTC/USDT [H1]")
    else:
        mon.record_fetch("BTC/USDT", TimeFrame.H1)
        print("Recorded fresh data for BTC/USDT [H1]")

    result = mon.check_and_trigger_kill_switch()

    print(f"\nKill switch active: {ks.is_active}")
    print(f"Current level:     {ks.current_level.value if ks.current_level else 'none'}")
    print(f"Trigger result:    {result}")

    if ks.is_active:
        event = ks.events[-1]
        print(f"Trigger:           {event.trigger.value}")
        print(f"Reason:            {event.reason}")
        print(f"Auto-activated:    {event.auto_activated}")
        print("\n✓ Kill switch fired as expected")
    else:
        print("\n− No kill switch activation (expected for fresh data or no trigger)")

    return 0 if (result is None) == args.no_trigger else 1


if __name__ == "__main__":
    sys.exit(main())
