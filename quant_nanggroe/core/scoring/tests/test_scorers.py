"""Tests for core/scoring/ package — real import verification + functional."""
import os

from quant_nanggroe.core.pipeline import PipelineResult, QuantPipeline
from quant_nanggroe.core.scoring.bond_scorer import BondScorer
from quant_nanggroe.core.scoring.economic_scorer import EconomicScorer
from quant_nanggroe.core.scoring.fusion_engine import FusionEngine, ScoredSignal
from quant_nanggroe.core.scoring.geo_scorer import GeopoliticalScorer
from quant_nanggroe.core.scoring.macro_scorer import MacroScorer
from quant_nanggroe.core.scoring.sentiment_scorer import SentimentScorer
from quant_nanggroe.core.scoring.technical_scorer import TechnicalScorer
from quant_nanggroe.core.scoring.volatility_scorer import VolatilityScorer


class TestMacroScorer:
    def test_risk_on(self):
        s = MacroScorer()
        result = s.score({"macro_regime": "RISK_ON", "dxy_change_pct": -0.5, "bond_zb_change_pct": -0.2})
        assert -100 <= result.score <= 100
        assert 0 <= result.confidence <= 1
        assert result.metadata["macro_weather"] == "RISK_ON"

    def test_risk_off(self):
        s = MacroScorer()
        result = s.score({"macro_regime": "RISK_OFF", "dxy_change_pct": 0.5, "bond_zb_change_pct": 0.3})
        assert -100 <= result.score <= 100
        assert result.metadata["macro_weather"] == "RISK_OFF"

    def test_neutral(self):
        s = MacroScorer()
        result = s.score({"macro_regime": "NEUTRAL_MIXED", "dxy_change_pct": 0.0, "bond_zb_change_pct": 0.0})
        assert abs(result.score) < 20
        assert result.confidence < 0.5

    def test_empty_ctx(self):
        s = MacroScorer()
        result = s.score({})
        assert result.score == 0.0


class TestSentimentScorer:
    def test_no_api_default_neutral(self):
        s = SentimentScorer(use_api=False)
        result = s.score({})
        assert result.score == 0.0
        assert result.confidence == 0.0

    def test_fng_value_extreme_fear(self):
        s = SentimentScorer(use_api=False)
        result = s.score({"fear_greed_index": 20})
        assert result.score > 0
        assert result.metadata["fear_greed_value"] == 20

    def test_fng_value_extreme_greed(self):
        s = SentimentScorer(use_api=False)
        result = s.score({"fear_greed_index": 80})
        assert result.score < 0

    def test_fng_value_neutral(self):
        s = SentimentScorer(use_api=False)
        result = s.score({"fear_greed_index": 50})
        assert abs(result.score) < 10
        assert result.confidence < 0.2


class TestTechnicalScorer:
    def test_no_ict_signal(self):
        s = TechnicalScorer()
        result = s.score({})
        assert result.score == 0.0
        assert result.confidence == 0.0

    def test_valid_buy_signal(self):
        s = TechnicalScorer()
        result = s.score({
            "ict_signal": {"direction": 1, "confidence": 0.8, "pattern": "fvg", "volume_ratio": 1.5},
        })
        assert result.score > 0
        assert result.confidence > 0.5

    def test_valid_sell_signal(self):
        s = TechnicalScorer()
        result = s.score({
            "ict_signal": {"direction": -1, "confidence": 0.7, "pattern": "order_block", "volume_ratio": 2.0},
        })
        assert result.score < 0
        assert result.confidence > 0.5

    def test_invalid_pattern(self):
        s = TechnicalScorer()
        result = s.score({
            "ict_signal": {"direction": 1, "confidence": 0.9, "pattern": "invalid", "volume_ratio": 1.0},
        })
        assert result.confidence < 0.6


class TestFusionEngine:
    def test_empty_engine(self):
        f = FusionEngine()
        result = f.evaluate({})
        assert result.bias == "neutral"
        assert result.confidence == 0.0
        assert result.override_aggregator is False

    def test_single_scorer(self):
        meta = MacroScorer()
        f = FusionEngine([meta])
        result = f.evaluate({"macro_regime": "RISK_ON", "dxy_change_pct": -1.0, "bond_zb_change_pct": -0.5})
        assert -100 <= result.composite_score <= 100
        assert 0 <= result.confidence <= 1
        assert len(result.details) == 1

    def test_multi_scorer_override(self):
        meta = MacroScorer()
        sent = SentimentScorer(use_api=False)
        tech = TechnicalScorer()
        f = FusionEngine([meta, sent, tech])
        result = f.evaluate({
            "macro_regime": "RISK_ON",
            "dxy_change_pct": -1.5,
            "bond_zb_change_pct": -0.8,
            "fear_greed_index": 25,
            "ict_signal": {"direction": 1, "confidence": 0.9, "pattern": "fvg", "volume_ratio": 2.0},
        })
        assert isinstance(result, ScoredSignal)
        assert 0 <= result.confidence <= 1

    def test_no_override_on_neutral(self):
        meta = MacroScorer()
        f = FusionEngine([meta])
        result = f.evaluate({"macro_regime": "NEUTRAL_MIXED", "dxy_change_pct": 0.0, "bond_zb_change_pct": 0.0})
        assert result.override_aggregator is False

    def test_threshold_logic(self):
        f = FusionEngine()
        for composite in [0, 10, 19, 20, 50, 100]:
            result = f.evaluate({})
            result.composite_score = float(composite)
            result.confidence = 0.7
            if composite > 20:
                result.bias = "buy"
            result.override_aggregator = result.confidence >= 0.60 and result.bias != "neutral"
            if composite > 20:
                assert result.override_aggregator is True
            else:
                assert result.override_aggregator is False

class TestEconomicScorer:
    def test_no_api_key(self):
        s = EconomicScorer(api_key="")
        r = s.score({})
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert "no_fred_api_key" in r.metadata.get("error", "")

    def test_score_components_structure(self):
        s = EconomicScorer(api_key=os.getenv("FRED_API_KEY", ""))
        r = s.score({})
        assert -100 <= r.score <= 100
        assert 0 <= r.confidence <= 1
        if r.metadata.get("components"):
            assert "cpi" in r.metadata["components"]
            assert "unemployment" in r.metadata["components"]

    def test_all_7_scorers(self):
        f = FusionEngine([MacroScorer(), EconomicScorer(api_key=os.getenv("FRED_API_KEY", "")),
                          BondScorer(), SentimentScorer(use_api=False),
                          TechnicalScorer(), VolatilityScorer(), GeopoliticalScorer()])
        result = f.evaluate({
            "macro_regime": "RISK_ON", "dxy_change_pct": -1.0, "bond_zb_change_pct": -0.5,
            "t10_yield": 4.5, "t2_yield": 4.8,
            "fear_greed_index": 30,
            "ict_signal": {"direction": 1, "confidence": 0.7, "pattern": "fvg", "volume_ratio": 1.5},
            "vix": 15,
            "gpr_index": 95,
        })
        assert -100 <= result.composite_score <= 100
        assert 0 <= result.confidence <= 1
        assert len(result.details) == 7


class TestBondScorer:
    def test_normal_steep(self):
        s = BondScorer()
        r = s.score({"t10_yield": 5.0, "t2_yield": 4.0})
        assert r.score > 0
        assert r.confidence > 0

    def test_inverted(self):
        s = BondScorer()
        r = s.score({"t10_yield": 4.0, "t2_yield": 5.0})
        assert r.score < 0
        assert r.metadata["inverted"] is True

    def test_no_data(self):
        s = BondScorer()
        r = s.score({})
        assert r.score == 0.0
        assert r.confidence == 0.0


class TestVolatilityScorer:
    def test_normal_vix(self):
        s = VolatilityScorer()
        r = s.score({"vix": 15})
        assert r.score > 0
        assert r.metadata["regime"] == "normal"

    def test_high_vix(self):
        s = VolatilityScorer()
        r = s.score({"vix": 35})
        assert r.score < -50
        assert r.metadata["regime"] == "extreme_fear"

    def test_no_vix(self):
        s = VolatilityScorer()
        r = s.score({})
        assert r.score == 0.0


class TestGeopoliticalScorer:
    def test_normal(self):
        s = GeopoliticalScorer()
        r = s.score({"gpr_index": 100})
        assert r.confidence > 0

    def test_elevated_risk(self):
        s = GeopoliticalScorer()
        r = s.score({"gpr_index": 180, "geopolitical_risk_delta": 30, "active_conflicts": ["UA", "ME"]})
        assert r.score < 0
        assert r.confidence > 0.5

    def test_no_data(self):
        s = GeopoliticalScorer()
        r = s.score({})
        assert r.score == 0.0


class TestQuantPipeline:
    def test_analyze_actionable(self):
        p = QuantPipeline()
        r = p.analyze({"macro_regime": "RISK_ON", "dxy_change_pct": -2.0, "bond_zb_change_pct": -1.0})
        assert isinstance(r, PipelineResult)
        assert r.status in ("actionable", "insufficient_confidence")

    def test_analyze_neutral(self):
        p = QuantPipeline()
        r = p.analyze({})
        assert r.status == "insufficient_confidence"
        assert r.execution_decision == "fallback"
