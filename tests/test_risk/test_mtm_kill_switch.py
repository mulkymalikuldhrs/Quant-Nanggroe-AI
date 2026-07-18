"""Regression test — P4 / pitfall #41: mark-to-market kill-switch blindness.

Open-position unrealized loss must trip the kill switch mid-crash, not only at
trade close. Before this fix, ``update_mtm`` did not exist and the switch was
fed solely by realized P&L.
"""
from __future__ import annotations

import os
import unittest

# ponytail: isolate from on-disk kill-switch state ("Crash" active from a
# prior session) — use the in-memory persistence backend so the manager
# boots with a clean, inactive kill switch.
os.environ.setdefault("PERSISTENCE_BACKEND", "memory")

from quant_nanggroe.engine.risk.manager import RiskManager


class TestMarkToMarketKillSwitch(unittest.TestCase):
    def setUp(self) -> None:
        # peak_equity == initial_equity == 100_000, MAX_DAILY_LOSS = 1%.
        self.rm = RiskManager(initial_equity=100_000.0)

    def test_mtm_loss_trips_daily_kill_switch(self) -> None:
        """An open unrealized loss >= 1% of peak equity must activate the switch."""
        self.assertFalse(self.rm.kill_switch.is_active, "switch must start inactive")
        # Loss big enough to exceed MAX_DAILY_LOSS (1%) of peak_equity.
        breach = self.rm.state.peak_equity * 0.02  # 2% of peak -> over 1% limit
        self.rm.update_mtm(-breach)
        self.assertTrue(
            self.rm.kill_switch.is_active,
            "MTM open loss (2% of peak) must trip the daily kill switch (>1% limit)",
        )
        self.assertEqual(self.rm.state.unrealized_pnl, -breach)

    def test_drawdown_monitor_seeded_with_equity(self) -> None:
        """DrawdownMonitor peak must equal initial_equity, not the 1M default.

        Regression for a real bug: DrawdownMonitor() was constructed without
        initial_equity, so its peak defaulted to 1_000_000. Every account under
        1M (incl. the 100k default) read as a ~90% drawdown and false-tripped
        the kill switch on the first MTM update.
        """
        self.assertEqual(self.rm.drawdown_monitor._peak, 100_000.0)
        # A modest open gain must NOT report a breached drawdown.
        self.rm.update_mtm(+2_000)
        self.assertFalse(
            self.rm.drawdown_monitor.is_breached,
            "drawdown must not breach on a 2% open gain from a correctly-seeded peak",
        )

    def test_mtm_gain_does_not_trip(self) -> None:
        """An open 2% unrealized gain must NOT activate the switch."""
        gain = self.rm.state.peak_equity * 0.02
        self.rm.update_mtm(+gain)
        self.assertFalse(self.rm.kill_switch.is_active)

    def test_mtm_loss_below_limit_stays_open(self) -> None:
        """A small open loss under the limit must not trip."""
        small = self.rm.state.peak_equity * 0.005  # 0.5% < 1%
        self.rm.update_mtm(-small)
        self.assertFalse(self.rm.kill_switch.is_active)


if __name__ == "__main__":
    unittest.main()
