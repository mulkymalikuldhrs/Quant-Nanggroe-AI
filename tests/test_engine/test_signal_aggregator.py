"""Signal Aggregator tests — ONE position per symbol, fixed risk."""
from __future__ import annotations

import pytest

from quant_nanggroe.engine.execution.signal_aggregator import (
    SignalAggregator,
    StrategyVote,
)


@pytest.fixture()
def agg():
    return SignalAggregator(min_conviction=0.30, risk_per_symbol=0.005)


def _vote(name, direction, conf=0.8, weight=1.0):
    return StrategyVote(strategy_name=name, direction=direction,
                        confidence=conf, weight=weight)


class TestAggregation:
    def test_all_buy_produces_buy(self, agg):
        votes = [_vote("a", "buy", 0.9), _vote("b", "buy", 0.8), _vote("c", "buy", 0.7)]
        r = agg.aggregate("XAUUSD.vx", votes)
        assert r.direction == "buy"
        assert r.should_trade
        assert len(r.contributors) == 3

    def test_majority_sell(self, agg):
        votes = [_vote("a", "sell", 0.9), _vote("b", "sell", 0.8), _vote("c", "buy", 0.6)]
        r = agg.aggregate("EURUSD.vx", votes)
        assert r.direction == "sell"

    def test_mixed_signals_low_conviction_holds(self, agg):
        votes = [
            _vote("a", "buy", 0.5),
            _vote("b", "sell", 0.5),
            _vote("c", "hold", 0.5),
        ]
        r = agg.aggregate("BTCUSDT", votes)
        assert r.direction == "hold"
        assert not r.should_trade

    def test_hold_votes_dont_contribute_weight(self, agg):
        votes = [_vote("a", "buy", 0.9, weight=1.0), _vote("b", "hold", 1.0)]
        r = agg.aggregate("XAUUSD", votes)
        assert r.buy_weight > 0
        assert r.sell_weight == 0
        assert "b" in r.abstainers

    def test_fixed_risk_not_scaled_by_conviction(self, agg):
        high = agg.aggregate("A", [_vote("s", "buy", 0.95, weight=2.0)])
        low = agg.aggregate("B", [_vote("s", "buy", 0.35, weight=1.0)])
        assert high.risk_pct == low.risk_pct == 0.005

    def test_empty_votes_holds(self, agg):
        r = agg.aggregate("ANY", [])
        assert r.direction == "hold"
        assert not r.should_trade

    def test_contributors_and_opposers(self, agg):
        votes = [_vote("bull_1", "buy", 0.9), _vote("bull_2", "buy", 0.8),
                 _vote("bear_1", "sell", 0.9)]
        r = agg.aggregate("GC=F", votes)
        assert "bull_1" in r.contributors
        assert "bear_1" in r.opposers

    def test_consensus_bonus_boosts_conviction(self, agg):
        # 3/3 agree → full consensus bonus
        full = agg.aggregate("A", [_vote("x", "buy", 0.8) for _ in range(3)])
        # 2/3 agree → partial bonus
        partial = agg.aggregate("B", [_vote("x", "buy", 0.8),
                                       _vote("y", "buy", 0.8),
                                       _vote("z", "hold", 0.5)])
        assert full.conviction >= partial.conviction
