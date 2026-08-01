"""C5: Tests for previously-untested core scoring scorers.

Covers the individual scoring modules in quant_nanggroe.core.scoring:
  - TechnicalScorer, VolatilityScorer, SentimentScorer, MacroScorer,
    GeopoliticalScorer, BondScorer, CryptoScorer, EconomicScorer
  - FusionEngine weighted aggregation + safety clamping

External APIs (FNG, FRED, Binance) are mocked/stubbed so tests run
offline and deterministically.
"""

from __future__ import annotations

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp
from quant_nanggroe.core.scoring.fusion_engine import FusionEngine, ScoredSignal
from quant_nanggroe.core.scoring.technical_scorer import TechnicalScorer
from quant_nanggroe.core.scoring.volatility_scorer import VolatilityScorer
from quant_nanggroe.core.scoring.sentiment_scorer import SentimentScorer
from quant_nanggroe.core.scoring.macro_scorer import MacroScorer
from quant_nanggroe.core.scoring.geo_scorer import GeopoliticalScorer
from quant_nanggroe.core.scoring.bond_scorer import BondScorer
from quant_nanggroe.core.scoring.crypto_scorer import CryptoScorer
from quant_nanggroe.core.scoring.economic_scorer import EconomicScorer


# ─────────────────────────────────────────────────────────────────────────────
# TechnicalScorer
# ─────────────────────────────────────────────────────────────────────────────
class TestTechnicalScorer:
    def test_no_ict_signal_returns_zero(self):
        s = TechnicalScorer()
        r = s.score({"symbol": "EURUSD", "ict_signal": {}})
        assert isinstance(r, ScorerResult)
        assert r.score == 0.0
        assert r.confidence == 0.0

    def test_ict_long_pattern_bullish(self):
        s = TechnicalScorer()
        ctx = {
            "symbol": "EURUSD",
            "ict_signal": {
                "direction": 1,
                "confidence": 0.8,
                "pattern": "order_block",
                "volume_ratio": 1.5,
            },
        }
        r = s.score(ctx)
        assert r.score > 0
        assert 0 < r.confidence <= 1
        assert r.metadata["ict_mode"] == "all"

    def test_ict_invalid_pattern_zero_conf(self):
        s = TechnicalScorer()
        ctx = {
            "symbol": "EURUSD",
            "ict_signal": {
                "direction": -1,
                "confidence": 0.9,
                "pattern": "garbage",
                "volume_ratio": 1.0,
            },
        }
        r = s.score(ctx)
        assert r.score < 0  # negative direction
        assert r.confidence < 0.9  # pattern invalid lowers confidence

    def test_score_clamped(self):
        s = TechnicalScorer()
        ctx = {
            "symbol": "EURUSD",
            "ict_signal": {
                "direction": 1,
                "confidence": 100.0,
                "pattern": "fvg",
                "volume_ratio": 100.0,
            },
        }
        r = s.score(ctx)
        assert -100.0 <= r.score <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# VolatilityScorer
# ─────────────────────────────────────────────────────────────────────────────
class TestVolatilityScorer:
    def test_no_vix_unavailable(self):
        s = VolatilityScorer()
        r = s.score({"vix": None})
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert r.metadata["source"] == "unavailable"

    def test_extreme_high_vix_bearish(self):
        s = VolatilityScorer()
        r = s.score({"vix": 45.0})
        assert r.score < 0  # high vol -> risk-off -> negative
        assert r.metadata["regime"] == "extreme_fear"

    def test_low_vix_complacent(self):
        s = VolatilityScorer()
        r = s.score({"vix": 10.0})
        assert r.score > 0
        assert r.metadata["regime"] == "complacent"

    def test_baseline_vix_neutral(self):
        s = VolatilityScorer()
        r = s.score({"vix": 18.0})
        assert abs(r.score) < 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# SentimentScorer
# ─────────────────────────────────────────────────────────────────────────────
class TestSentimentScorer:
    def test_use_api_false_no_call(self, monkeypatch):
        s = SentimentScorer(use_api=False)
        # Even with no fng in ctx, with use_api False it must not hit network
        r = s.score({"symbol": "BTCUSD"})
        assert r.score == 0.0
        assert r.confidence == 0.0

    def test_explicit_fng_bearish(self):
        s = SentimentScorer(use_api=False)
        r = s.score({"symbol": "BTCUSD", "fear_greed_index": 10})
        assert r.score > 0  # extreme fear -> contrarian bullish
        assert 0 < r.confidence <= 1

    def test_explicit_fng_bullish(self):
        s = SentimentScorer(use_api=False)
        r = s.score({"symbol": "BTCUSD", "fear_greed_index": 90})
        assert r.score < 0  # extreme greed -> contrarian bearish

    def test_fng_midpoint_neutral(self):
        s = SentimentScorer(use_api=False)
        r = s.score({"symbol": "BTCUSD", "fear_greed_index": 50})
        assert abs(r.score) < 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# MacroScorer
# ─────────────────────────────────────────────────────────────────────────────
class TestMacroScorer:
    def test_risk_on_es_bullish(self):
        s = MacroScorer()
        r = s.score({"macro_regime": "RISK_ON", "dxy_change_pct": 0.0})
        assert r.score > 0  # ES1! bias positive in RISK_ON

    def test_risk_off_es_bearish(self):
        s = MacroScorer()
        r = s.score({"macro_regime": "RISK_OFF", "dxy_change_pct": 0.0})
        assert r.score < 0

    def test_neutral_confidence_halved(self):
        s = MacroScorer()
        r = s.score({"macro_regime": "NEUTRAL_MIXED", "dxy_change_pct": 0.0})
        assert 0 <= r.confidence <= 0.5

    def test_dxy_change_combined(self):
        s = MacroScorer()
        r = s.score({"macro_regime": "RISK_ON", "dxy_change_pct": -1.0})
        assert isinstance(r.score, float)
        assert -100 <= r.score <= 100


# ─────────────────────────────────────────────────────────────────────────────
# GeopoliticalScorer
# ─────────────────────────────────────────────────────────────────────────────
class TestGeopoliticalScorer:
    def test_empty_context(self):
        s = GeopoliticalScorer()
        r = s.score({})
        assert r.score == 0.0
        assert r.confidence == 0.0

    def test_gpr_high_bearish(self):
        s = GeopoliticalScorer()
        r = s.score({"gpr_index": 150.0})
        assert r.score < 0
        assert r.confidence > 0
        assert "gpr_150" in r.metadata["signals"]

    def test_active_conflicts_penalize(self):
        s = GeopoliticalScorer()
        r = s.score({"active_conflicts": ["ukraine", "gaza"]})
        assert r.score < 0
        assert r.confidence > 0

    def test_clamped(self):
        s = GeopoliticalScorer()
        r = s.score({
            "gpr_index": 300.0,
            "geopolitical_risk_delta": 500.0,
            "active_conflicts": ["a", "b", "c", "d", "e"],
        })
        assert -100.0 <= r.score <= 100.0
        assert 0 <= r.confidence <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# BondScorer
# ─────────────────────────────────────────────────────────────────────────────
class TestBondScorer:
    def test_missing_data_unavailable(self):
        s = BondScorer()
        r = s.score({"t10_yield": None, "t2_yield": None})
        assert r.score == 0.0
        assert r.metadata["source"] == "unavailable"

    def test_inverted_2s10s_bearish(self):
        s = BondScorer()
        r = s.score({"t10_yield": 3.0, "t2_yield": 4.0})  # inverted
        assert r.score < 0
        assert r.metadata["inverted"] is True

    def test_steep_curve_bullish(self):
        s = BondScorer()
        r = s.score({"t10_yield": 4.0, "t2_yield": 2.0})
        assert r.score > 0
        assert r.metadata["inverted"] is False

    def test_3m10s_additional_penalty(self):
        s = BondScorer()
        base = s.score({"t10_yield": 3.5, "t2_yield": 3.55})  # slightly inverted
        extra = s.score({"t10_yield": 3.5, "t2_yield": 3.55, "t3m_yield": 5.0})
        assert extra.score < base.score  # 3m10s inverted adds penalty


# ─────────────────────────────────────────────────────────────────────────────
# CryptoScorer
# ─────────────────────────────────────────────────────────────────────────────
class TestCryptoScorer:
    def test_non_crypto_zero(self, monkeypatch):
        s = CryptoScorer()
        monkeypatch.setattr(s, "_cache", _FakeCache())
        r = s.score({"symbol": "EURUSD"})
        assert r.score == 0.0
        assert r.metadata["reason"] == "not_crypto"

    def test_no_data(self, monkeypatch):
        s = CryptoScorer()
        monkeypatch.setattr(s, "_cache", _FakeCache())
        monkeypatch.setattr(s, "_get_funding_rate", lambda sym: None)
        monkeypatch.setattr(s, "_get_open_interest", lambda sym: None)
        r = s.score({"symbol": "BTCUSD"})
        assert r.score == 0.0
        assert r.metadata["reason"] == "no_data"

    def test_negative_funding_bullish(self, monkeypatch):
        s = CryptoScorer()
        monkeypatch.setattr(s, "_cache", _FakeCache())
        monkeypatch.setattr(s, "_get_funding_rate", lambda sym: {"lastFundingRate": -0.001})
        monkeypatch.setattr(s, "_get_open_interest", lambda sym: None)
        r = s.score({"symbol": "BTCUSD"})
        assert r.score > 0
        assert r.metadata["funding_rate_pct"] < 0

    def test_positive_funding_bearish(self, monkeypatch):
        s = CryptoScorer()
        monkeypatch.setattr(s, "_cache", _FakeCache())
        monkeypatch.setattr(s, "_get_funding_rate", lambda sym: {"lastFundingRate": 0.001})
        monkeypatch.setattr(s, "_get_open_interest", lambda sym: None)
        r = s.score({"symbol": "ETHUSD"})
        assert r.score < 0


# ─────────────────────────────────────────────────────────────────────────────
# EconomicScorer (FRED calls mocked)
# ─────────────────────────────────────────────────────────────────────────────
class TestEconomicScorer:
    def test_no_api_key(self, monkeypatch):
        s = EconomicScorer(api_key=None)
        monkeypatch.setattr(s, "_fred_fetch", lambda *a, **k: None)
        r = s.score({"fred_api_key": None})
        assert r.score == 0.0
        assert r.metadata.get("error") == "no_fred_api_key"

    def test_cpi_high_inflation_bearish(self, monkeypatch):
        s = EconomicScorer(api_key="X")
        monkeypatch.setattr(
            s, "_fred_fetch",
            lambda series_id, key: [{"value": "100.0"}, {"value": "90.0"}],
        )
        r = s.score({"fred_api_key": "X"})
        # high YoY inflation -> negative score
        assert r.score < 0

    def test_low_inflation_neutral_bullish(self, monkeypatch):
        s = EconomicScorer(api_key="X")
        monkeypatch.setattr(
            s, "_fred_fetch",
            lambda series_id, key: [{"value": "100.0"}, {"value": "99.5"}],
        )
        r = s.score({"fred_api_key": "X"})
        # very low inflation -> positive-ish score
        assert r.score > 0

    def test_all_fred_fail(self, monkeypatch):
        s = EconomicScorer(api_key="X")
        monkeypatch.setattr(s, "_fred_fetch", lambda series_id, key: None)
        r = s.score({"fred_api_key": "X"})
        assert r.score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# FusionEngine
# ─────────────────────────────────────────────────────────────────────────────
class _ConstScorer(BaseScorer):
    def __init__(self, w, score, conf, name="Const"):
        self.weight = w
        self._s = score
        self._c = conf
        self._name = name

    def score(self, ctx):
        return ScorerResult(score=self._s, confidence=self._c,
                            metadata={"n": self._name})


class TestFusionEngine:
    def test_empty_returns_neutral(self):
        fe = FusionEngine([])
        r = fe.evaluate({})
        assert isinstance(r, ScoredSignal)
        assert r.composite_score == 0.0
        assert r.bias == "neutral"

    def test_weight_normalization(self):
        fe = FusionEngine([
            _ConstScorer(0.5, 40.0, 0.9, "A"),
            _ConstScorer(0.5, -40.0, 0.9, "B"),
        ])
        r = fe.evaluate({})
        assert abs(r.composite_score) < 1e-6  # equal & opposite
        assert r.bias == "neutral"
        # weights normalized to sum to 1
        assert abs(sum(x.weight for x in fe._scorers) - 1.0) < 1e-6

    def test_buy_bias_threshold(self):
        fe = FusionEngine([_ConstScorer(1.0, 50.0, 0.9, "A")])
        r = fe.evaluate({})
        assert r.composite_score > 20.0
        assert r.bias == "buy"

    def test_sell_bias_threshold(self):
        fe = FusionEngine([_ConstScorer(1.0, -50.0, 0.9, "B")])
        r = fe.evaluate({})
        assert r.bias == "sell"

    def test_override_aggregator_set(self):
        fe = FusionEngine([_ConstScorer(1.0, 50.0, 0.95, "A")])
        r = fe.evaluate({})
        assert r.override_aggregator is True

    def test_scorer_exception_isolated(self):
        class _Boom(BaseScorer):
            weight = 1.0

            def score(self, ctx):
                raise RuntimeError("boom")

        fe = FusionEngine([_Boom()])
        r = fe.evaluate({})
        assert isinstance(r, ScoredSignal)
        assert len(r.details) == 1

    def test_add_scorer(self):
        fe = FusionEngine([])
        fe.add_scorer(_ConstScorer(1.0, 10.0, 0.5, "A"))
        assert len(fe._scorers) == 1


class _FakeCache:
    """Minimal TTLCache stand-in that always misses (forces the mock path)."""

    def get(self, key):
        return None

    def set(self, key, value, ttl=None):
        return None

    def clear(self):
        return None
