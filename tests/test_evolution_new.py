"""C5: Tests for previously-untested evolution engine logic.

Covers:
  - evolution_config: per-account JSON config load/save/merge
  - weight_updater: Bayesian + scorer-weight helpers (offline)
  - strategy_disabler: threshold evaluation + regime-aware gating
  - closed_trade_handler: journal-backed trade recording/querying
  - evolver (core.scoring.evolver): ScoreJournal + WeightEvolver alignment

All use temp-file backends — no broker/MT5, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_nanggroe.core.scoring.evolver import ScoreJournal, WeightEvolver
from quant_nanggroe.engine.evolution.evolution_config import EvolutionConfig
from quant_nanggroe.engine.evolution.closed_trade_handler import ClosedTradeHandler
from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal
from quant_nanggroe.engine.evolution.strategy_disabler import StrategyDisabler
from quant_nanggroe.engine.evolution.weight_updater import WeightUpdater


# ─────────────────────────────────────────────────────────────────────────────
# EvolutionConfig
# ─────────────────────────────────────────────────────────────────────────────
class TestEvolutionConfig:
    def test_defaults_applied(self, tmp_path):
        cfg = EvolutionConfig(path=tmp_path / "evo.json")
        assert cfg.get("threshold_trades") == 20
        assert cfg.get("min_win_rate") == 0.40

    def test_get_set_persists(self, tmp_path):
        cfg = EvolutionConfig(path=tmp_path / "evo.json")
        cfg.set("threshold_trades", 50)
        assert cfg.get("threshold_trades") == 50
        # reload from disk
        cfg2 = EvolutionConfig(path=tmp_path / "evo.json")
        assert cfg2.get("threshold_trades") == 50

    def test_account_override_merges(self, tmp_path):
        cfg = EvolutionConfig(path=tmp_path / "evo.json")
        cfg.set_account_config("acc1", {"threshold_trades": 5, "min_win_rate": 0.5})
        acc = cfg.get_account_config("acc1")
        assert acc["threshold_trades"] == 5
        assert acc["min_win_rate"] == 0.5
        # account-specific key should not leak into global
        assert cfg.get("threshold_trades") == 20

    def test_account_fallback_to_global(self, tmp_path):
        cfg = EvolutionConfig(path=tmp_path / "evo.json")
        assert cfg.get_account_config("unknown")["threshold_trades"] == 20

    def test_corrupt_file_falls_back(self, tmp_path):
        p = tmp_path / "evo.json"
        p.write_text("{not valid json")
        cfg = EvolutionConfig(path=p)
        assert cfg.get("threshold_trades") == 20


# ─────────────────────────────────────────────────────────────────────────────
# EvolutionJournal + ClosedTradeHandler
# ─────────────────────────────────────────────────────────────────────────────
class TestClosedTradeHandler:
    def _journal(self, tmp_path):
        return EvolutionJournal(path=tmp_path / "j.json")

    def test_record_and_recent(self, tmp_path):
        h = ClosedTradeHandler(journal=self._journal(tmp_path))
        h.record_trade({
            "strategy": "sma_cross", "symbol": "BTCUSD", "direction": "buy",
            "entry_price": 100.0, "exit_price": 110.0, "pnl": 10.0, "pnl_pct": 0.1,
        })
        trades = h.get_recent_trades("sma_cross", limit=10)
        assert len(trades) == 1
        assert trades[0]["symbol"] == "BTCUSD"

    def test_strategy_stats(self, tmp_path):
        h = ClosedTradeHandler(journal=self._journal(tmp_path))
        for pnl in (10.0, -5.0, 8.0):
            h.record_trade({
                "strategy": "sma_cross", "symbol": "BTCUSD", "direction": "buy",
                "entry_price": 100.0, "exit_price": 100.0 + pnl, "pnl": pnl, "pnl_pct": 0.01,
            })
        stats = h.get_strategy_stats("sma_cross")
        assert stats["trade_count"] == 3
        assert stats["wins"] == 2
        assert stats["losses"] == 1
        assert 0 <= stats["win_rate"] <= 1

    def test_all_trades(self, tmp_path):
        h = ClosedTradeHandler(journal=self._journal(tmp_path))
        for i in range(3):
            h.record_trade({"strategy": f"strat{i}", "symbol": "X", "pnl": 1.0})
        assert len(h.get_all_trades(limit=100)) >= 3


# ─────────────────────────────────────────────────────────────────────────────
# StrategyDisabler
# ─────────────────────────────────────────────────────────────────────────────
class TestStrategyDisabler:
    def _disabler(self, **kw):
        return StrategyDisabler(**kw)

    def test_insufficient_trades_skipped(self):
        d = self._disabler(min_trades=10)
        out = d.evaluate([{"strategy_name": "weak", "trade_count": 3,
                            "sharpe": -1.0, "win_rate": 0.2, "max_drawdown": 30.0}])
        assert out == []

    def test_below_thresholds_flagged(self):
        d = self._disabler(min_trades=5, min_sharpe=0.5, min_win_rate=0.4, max_drawdown=15.0)
        out = d.evaluate([{
            "strategy_name": "weak", "trade_count": 20,
            "sharpe": 0.1, "win_rate": 0.3, "max_drawdown": 20.0,
        }])
        assert len(out) == 1
        assert out[0]["strategy_name"] == "weak"
        assert "sharpe" in out[0]["reason"]
        assert "win_rate" in out[0]["reason"]

    def test_passing_strategy_not_disabled(self):
        d = self._disabler(min_trades=5, min_sharpe=0.5, min_win_rate=0.4, max_drawdown=15.0)
        out = d.evaluate([{
            "strategy_name": "strong", "trade_count": 20,
            "sharpe": 1.5, "win_rate": 0.7, "max_drawdown": 8.0,
        }])
        assert out == []

    def test_regime_aware_preserves_specialist(self):
        # Without journal, no regime edge -> to_disable
        d = self._disabler(journal=None)
        res = d.evaluate_with_regime([{
            "strategy_name": "weak", "trade_count": 20,
            "sharpe": 0.1, "win_rate": 0.3, "max_drawdown": 20.0,
        }])
        assert res["to_disable"]
        assert res["regime_dependent"] == []


# ─────────────────────────────────────────────────────────────────────────────
# WeightUpdater helpers (Bayesian / scorer-weight)
# ─────────────────────────────────────────────────────────────────────────────
class TestWeightUpdater:
    def test_bayesian_weight_high_win_rate(self):
        w = WeightUpdater()
        # 90% win rate over 100 trades -> ~ (1 + 90) / (1+1+100) ≈ 0.891
        val = w._compute_bayesian_weight(0.9, 100)
        assert 0.8 < val < 0.95

    def test_bayesian_weight_low_win_rate(self):
        w = WeightUpdater()
        val = w._compute_bayesian_weight(0.1, 100)
        assert val < 0.2

    def test_scorer_weight_clamped_to_max_change(self):
        w = WeightUpdater()
        # sharpe high -> multiplier up to 1.2, change capped at 5% of old
        new = w._compute_scorer_weight(sharpe=5.0, old_weight=1.0)
        assert new <= 1.05 + 1e-9
        assert new >= 0.95 - 1e-9

    def test_scorer_weight_min_max_bounds(self):
        w = WeightUpdater()
        new = w._compute_scorer_weight(sharpe=10.0, old_weight=0.05)
        assert new >= 0.05  # not below weight_min
        new2 = w._compute_scorer_weight(sharpe=-10.0, old_weight=3.0)
        assert new2 <= 3.0

    def test_update_weights_signal_only(self):
        w = WeightUpdater()
        res = w.update_weights([
            {"strategy_name": "sma", "win_rate": 0.7, "trade_count": 50, "sharpe": 1.0},
        ])
        assert len(res["signal_updates"]) == 1
        assert res["signal_updates"][0]["provider"] == "sma"


# ─────────────────────────────────────────────────────────────────────────────
# ScoreJournal + WeightEvolver (core.scoring.evolver)
# ─────────────────────────────────────────────────────────────────────────────
class TestScoreJournal:
    def test_record_and_len(self, tmp_path):
        j = ScoreJournal(path=str(tmp_path / "sj.json"))
        j.record("t1", "BTCUSD", {"TechnicalScorer": {"score": 30.0, "confidence": 0.8}},
                 actual_pnl=10.0, predicted_bias="buy")
        assert len(j) == 1
        assert j.last_n(1)[0].trade_id == "t1"

    def test_persists_to_disk(self, tmp_path):
        p = str(tmp_path / "sj.json")
        j = ScoreJournal(path=p)
        j.record("t1", "BTCUSD", {"TechnicalScorer": {"score": 30.0, "confidence": 0.8}},
                 actual_pnl=10.0, predicted_bias="buy")
        j2 = ScoreJournal(path=p)
        assert len(j2) == 1


class TestWeightEvolver:
    def _journal(self, tmp_path):
        return ScoreJournal(path=str(tmp_path / "sj.json"))

    def test_not_enough_trades_no_eval(self, tmp_path):
        we = WeightEvolver(journal=self._journal(tmp_path), evolve_every=20)
        for i in range(5):
            we.record_trade(f"t{i}", "X", {"TechnicalScorer": {"score": 30.0, "confidence": 0.8}},
                            actual_pnl=10.0, predicted_bias="buy")
        assert we.evaluate() is None

    def test_default_weights_sum_to_one(self):
        we = WeightEvolver()
        assert abs(sum(we.default_weights.values()) - 1.0) < 1e-3

    def test_apply_weights_sets_scorer(self):
        we = WeightEvolver()
        we.current_weights = {"TechnicalScorer": 0.42}
        class _S:
            weight = 0.10
            __class__ = type("TechnicalScorer", (), {})
        s = _S()
        s.__class__.__name__ = "TechnicalScorer"
        we.apply_weights([s])
        assert abs(s.weight - 0.42) < 1e-6

    def test_evaluate_runs_after_threshold(self, tmp_path):
        # Use small evolve_every so we don't need 20+ trades to trigger an eval path,
        # but enough trades to clear the n>=2 alignment requirement.
        we = WeightEvolver(journal=self._journal(tmp_path), evolve_every=3,
                           max_adj_pct=0.05, max_total_shift_pct=0.20)
        # Aligned scorer: positive score + positive pnl
        for i in range(6):
            we.record_trade(f"t{i}", "X",
                            {"Tech": {"score": 30.0, "confidence": 0.8},
                             "Bad": {"score": -5.0, "confidence": 0.2}},
                            actual_pnl=10.0, predicted_bias="buy")
        result = we.evaluate()
        assert isinstance(result, dict)
        assert abs(sum(result.values()) - 1.0) < 1e-3  # normalized

    def test_reset_to_defaults(self, tmp_path):
        we = WeightEvolver(journal=self._journal(tmp_path))
        we.current_weights["TechnicalScorer"] = 0.99
        we.reset_to_defaults()
        assert abs(we.current_weights["TechnicalScorer"] -
                   we.default_weights["TechnicalScorer"]) < 1e-9
