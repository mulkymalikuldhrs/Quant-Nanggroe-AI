"""GATE-3 wiring regression: reflect() reasons over trade awareness."""
from __future__ import annotations

from quant_nanggroe.engine.self_aware import SelfAware, SelfState


def test_reflect_uses_awareness_feed():
    sa = SelfAware()
    sa.set_state_provider(lambda: SelfState(
        equity=1000.0, peak_equity=1050.0, daily_pnl=-5.0,
        total_trades=3, open_positions=1,
        veto_count=1, approval_count=4,
        losing_streak=2,
        last_strategy="archive_aroon", last_symbol="XAUUSD.vx",
        last_run_ts=0.0,
        extra={"pipeline": "AutonomousPipeline",
               "trade_awareness": {
                   "recent_closed": 10, "wins": 3, "losses": 7,
                   "worst_strategy": "archive_amdx",
                   "top_lesson": "widening ATR stop distance",
               }},
    ))
    r = sa.reflect()
    joined = " ".join(r.statements)
    assert "closed trades" in joined
    assert "archive_amdx" in joined          # worst strategy surfaced
    assert any("losses" in a for a in r.anomalies)


def test_reflect_positive_edge_statement():
    sa = SelfAware()
    sa.set_state_provider(lambda: SelfState(
        equity=1200.0, peak_equity=1100.0, daily_pnl=20.0,
        total_trades=2, open_positions=0,
        veto_count=0, approval_count=5, losing_streak=0,
        extra={"trade_awareness": {
            "recent_closed": 8, "wins": 6, "losses": 2,
            "worst_strategy": "", "top_lesson": "",
        }},
    ))
    r = sa.reflect()
    joined = " ".join(r.statements)
    assert "6W/2L" in joined
