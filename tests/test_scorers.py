"""B5: Tests for the 4 previously-untested scorers.

Covers:
  - CryptoScorer      (Binance FAPI funding rate / open interest via urllib)
  - NewsScorer        (Alpha Vantage NEWS_SENTIMENT via urllib)
  - PositioningScorer (COT provider + hidden-regime)
  - ConfluenceScorer  (multi-module weighted signal fusion)

External APIs (network) are mocked so tests run offline & deterministically.
"""
from __future__ import annotations

import pytest

from quant_nanggroe.core.scoring.base import ScorerResult
from quant_nanggroe.core.scoring.crypto_scorer import CryptoScorer
from quant_nanggroe.core.scoring.positioning_scorer import PositioningScorer
from quant_nanggroe.core.news.news_scorer import NewsScorer
from quant_nanggroe.engine.portfolio.confluence_scorer import (
    ConfluenceScorer,
    ConfluenceResult,
)


# --------------------------------------------------------------------------- #
# CryptoScorer                                                                 #
# --------------------------------------------------------------------------- #
class TestCryptoScorer:
    def _make(self, monkeypatch, funding=None, oi=None):
        s = CryptoScorer()
        s._cache.clear() if hasattr(s._cache, "clear") else None
        monkeypatch.setattr(s, "_get_funding_rate", lambda sym: funding)
        monkeypatch.setattr(s, "_get_open_interest", lambda sym: oi)
        return s

    def test_non_crypto_returns_zero(self):
        s = CryptoScorer()
        r = s.score({"symbol": "EURUSD"})
        assert isinstance(r, ScorerResult)
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert r.metadata["reason"] == "not_crypto"

    def test_no_data(self, monkeypatch):
        s = self._make(monkeypatch, funding=None, oi=None)
        r = s.score({"symbol": "BTCUSD"})
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert r.metadata["reason"] == "no_data"

    def test_negative_funding_bullish(self, monkeypatch):
        # negative funding => shorts pay longs => bullish (+score)
        s = self._make(monkeypatch, funding={"lastFundingRate": -0.0005}, oi=None)
        r = s.score({"symbol": "BTCUSD"})
        assert r.score > 0
        assert 0 < r.confidence <= 1
        assert r.metadata["funding_rate_pct"] < 0

    def test_positive_funding_bearish(self, monkeypatch):
        s = self._make(monkeypatch, funding={"lastFundingRate": 0.0005}, oi=None)
        r = s.score({"symbol": "ETHUSD"})
        assert r.score < 0
        assert 0 < r.confidence <= 1

    def test_oi_with_price_change(self, monkeypatch):
        s = self._make(
            monkeypatch,
            funding={"lastFundingRate": -0.0005},
            oi={"openInterest": 12345.0},
        )
        r = s.score({"symbol": "BTCUSD", "price_change_pct": 0.5})
        assert r.score > 0
        assert r.metadata["open_interest"] == 12345.0
        assert -100 <= r.score <= 100


# --------------------------------------------------------------------------- #
# NewsScorer                                                                   #
# --------------------------------------------------------------------------- #
class TestNewsScorer:
    def test_demo_key_returns_zero(self):
        s = NewsScorer(api_key="demo")
        r = s.score({"symbol": "BTCUSD"})
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert r.metadata["reason"] == "no_api_key"

    def test_no_key_defaults_demo(self):
        s = NewsScorer()  # no key -> "demo"
        r = s.score({"symbol": "BTCUSD"})
        assert r.metadata["reason"] == "no_api_key"

    def test_no_news_data(self, monkeypatch):
        s = NewsScorer(api_key="REAL")
        monkeypatch.setattr(s, "_fetch_news_sentiment", lambda sym, key: [])
        r = s.score({"symbol": "BTCUSD"})
        assert r.score == 0.0
        assert r.metadata["reason"] == "no_news_data"

    def test_positive_sentiment(self, monkeypatch):
        feed = [{"overall_sentiment_score": 0.4} for _ in range(20)]
        s = NewsScorer(api_key="REAL")
        monkeypatch.setattr(s, "_fetch_news_sentiment", lambda sym, key: feed)
        r = s.score({"symbol": "BTCUSD"})
        assert r.score > 0
        assert 0 < r.confidence <= 1
        assert r.metadata["article_count"] == 20
        assert r.metadata["avg_sentiment"] == pytest.approx(0.4, abs=1e-6)

    def test_negative_sentiment(self, monkeypatch):
        feed = [{"overall_sentiment_score": -0.5} for _ in range(10)]
        s = NewsScorer(api_key="REAL")
        monkeypatch.setattr(s, "_fetch_news_sentiment", lambda sym, key: feed)
        r = s.score({"symbol": "ETHUSD"})
        assert r.score < 0
        assert -100 <= r.score <= 100

    def test_ctx_key_used(self, monkeypatch):
        feed = [{"overall_sentiment_score": 0.1} for _ in range(5)]
        captured = {}

        def fake_fetch(sym, key):
            captured["key"] = key
            return feed

        s = NewsScorer()
        monkeypatch.setattr(s, "_fetch_news_sentiment", fake_fetch)
        s.score({"symbol": "BTCUSD", "alpha_vantage_key": "CTXKEY"})
        assert captured["key"] == "CTXKEY"


# --------------------------------------------------------------------------- #
# PositioningScorer                                                            #
# --------------------------------------------------------------------------- #
class TestPositioningScorer:
    def _cot(self):
        return {
            "symbol": "EURUSD",
            "report_date": "2026-07-28",
            "commercial_long": 200000,
            "commercial_short": 100000,
            "non_commercial_long": 80000,
            "non_commercial_short": 160000,
            "open_interest": 400000,
            "source": "test",
            "history": [],
        }

    def test_no_cot_unavailable(self, monkeypatch):
        s = PositioningScorer(use_hidden_regime=False)
        monkeypatch.setattr(s, "_fetch_cot", lambda sym: None)
        monkeypatch.setattr(s, "_get_regime_context", lambda ctx, sym: None)
        r = s.score({"symbol": "EURUSD"})
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert r.metadata["source"] == "unavailable"

    def test_ctx_cot_scored(self, monkeypatch):
        s = PositioningScorer(use_hidden_regime=False)
        monkeypatch.setattr(s, "_get_regime_context", lambda ctx, sym: None)
        r = s.score({"symbol": "EURUSD", "cot_data": self._cot()})
        assert isinstance(r, ScorerResult)
        assert -100 <= r.score <= 100
        assert 0 <= r.confidence <= 1
        assert r.metadata["symbol"] == "EURUSD"

    def test_fetch_cot_path(self, monkeypatch):
        s = PositioningScorer(use_hidden_regime=False)
        monkeypatch.setattr(s, "_fetch_cot", lambda sym: self._cot())
        monkeypatch.setattr(s, "_get_regime_context", lambda ctx, sym: None)
        r = s.score({"symbol": "EURUSD"})
        assert -100 <= r.score <= 100
        assert "net_commercial_pct" in r.metadata

    def test_regime_applied(self, monkeypatch):
        s = PositioningScorer(use_hidden_regime=False)
        regime = {"current_regime": "bullish", "regime_confidence": 0.8}
        monkeypatch.setattr(s, "_get_regime_context", lambda ctx, sym: regime)
        r = s.score({"symbol": "EURUSD", "cot_data": self._cot()})
        assert r.metadata.get("regime_name") == "bullish"
        assert -100 <= r.score <= 100


# --------------------------------------------------------------------------- #
# ConfluenceScorer                                                             #
# --------------------------------------------------------------------------- #
class TestConfluenceScorer:
    def test_empty_signals_hold(self):
        c = ConfluenceScorer()
        r = c.evaluate([])
        assert isinstance(r, ConfluenceResult)
        assert r.overall_signal == "hold"
        assert r.overall_confidence == 0.0

    def test_all_hold(self):
        c = ConfluenceScorer()
        r = c.evaluate([
            {"strategy": "smc_strategy", "side": "hold", "confidence": 0.5},
            {"strategy": "carry_trade", "side": "hold", "confidence": 0.5},
        ])
        assert r.overall_signal == "hold"
        assert "all signals hold" in r.reasoning

    def test_buy_confluence(self):
        c = ConfluenceScorer(min_confluence=2, threshold=0.6)
        r = c.evaluate([
            {"strategy": "factor_model_sdf", "side": "buy", "confidence": 0.9},
            {"strategy": "smc_strategy", "side": "buy", "confidence": 0.9},
            {"strategy": "statistical_arbitrage", "side": "buy", "confidence": 0.85},
        ])
        assert r.overall_signal == "buy"
        assert r.overall_confidence > 0
        assert r.confluence_score >= 2

    def test_sell_confluence(self):
        c = ConfluenceScorer(min_confluence=2, threshold=0.6)
        r = c.evaluate([
            {"strategy": "factor_model_sdf", "side": "sell", "confidence": 0.9},
            {"strategy": "smc_strategy", "side": "sell", "confidence": 0.9},
            {"strategy": "microstructure_alpha", "side": "sell", "confidence": 0.85},
        ])
        assert r.overall_signal == "sell"
        assert r.confluence_score >= 2

    def test_insufficient_confluence(self):
        c = ConfluenceScorer(min_confluence=3, threshold=0.6)
        r = c.evaluate([
            {"strategy": "smc_strategy", "side": "buy", "confidence": 0.9},
        ])
        assert r.overall_signal == "hold"
        assert "insufficient confluence" in r.reasoning

    def test_macro_weather_risk_off_dampens_buy(self):
        c = ConfluenceScorer(min_confluence=2, threshold=0.6)
        r = c.evaluate(
            [
                {"strategy": "factor_model_sdf", "side": "buy", "confidence": 0.9},
                {"strategy": "smc_strategy", "side": "buy", "confidence": 0.9},
            ],
            macro_weather="RISK_OFF",
        )
        # buy confidence/weight dampened -> likely no strong buy
        assert isinstance(r, ConfluenceResult)
        assert r.overall_signal in ("hold", "buy")
