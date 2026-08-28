"""Tests for ML Signal Generator Module.

Tests the actual engine.models.signal_generator module (not the phantom
engine.ml.signal_generator that was removed in a prior refactor).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.ml.feature_engineer import (
    FeatureConfig,
    FeatureEngineer,
)
from quant_nanggroe.engine.ml.model_manager import (
    ModelManager,
    ModelStatus,
)
from quant_nanggroe.engine.models.signal_generator import (
    SignalGenerator,
    TradingSignal,
)


def _make_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """Generate mock OHLCV data for ML tests."""
    np.random.seed(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    base = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame(
        {
            "open": base + np.random.rand(n) * 0.5,
            "high": base + np.random.rand(n) * 2.0,
            "low": base - np.random.rand(n) * 2.0,
            "close": base,
            "volume": np.random.randint(1_000_000, 10_000_000, n).astype(float),
        },
        index=dates,
    )


# ── Feature Engineer Tests ─────────────────────────────────────────────


class TestFeatureEngineer:
    def test_engineer_features(self):
        fe = FeatureEngineer()
        df = _make_ohlcv(200)
        features = fe.engineer_features(df)
        assert isinstance(features, pd.DataFrame)
        assert len(features) == len(df)
        assert features.shape[1] > 0

    def test_technical_features(self):
        fe = FeatureEngineer(FeatureConfig(include_technical=True, include_volume=False, include_statistical=False))
        df = _make_ohlcv(200)
        features = fe.engineer_features(df)
        assert "rsi_14" in features.columns
        assert "macd" in features.columns

    def test_volume_features(self):
        fe = FeatureEngineer(FeatureConfig(include_technical=False, include_volume=True, include_statistical=False))
        df = _make_ohlcv(200)
        features = fe.engineer_features(df)
        assert "volume_ratio" in features.columns

    def test_statistical_features(self):
        fe = FeatureEngineer(FeatureConfig(include_technical=False, include_volume=False, include_statistical=True))
        df = _make_ohlcv(200)
        features = fe.engineer_features(df)
        assert any("volatility" in c for c in features.columns)

    def test_create_target(self):
        fe = FeatureEngineer()
        df = _make_ohlcv(200)
        target = fe.create_target(df, forward_periods=5, threshold=0.02)
        assert isinstance(target, pd.Series)
        assert target.name == "target"
        assert set(target.dropna().unique()).issubset({-1, 0, 1})

    def test_custom_transform(self):
        fe = FeatureEngineer()
        fe.add_transform("custom_close_ratio", lambda df: df["close"] / df["close"].shift(1))
        df = _make_ohlcv(200)
        features = fe.engineer_features(df)
        assert "custom_close_ratio" in features.columns

    def test_feature_selection_variance(self):
        fe = FeatureEngineer()
        df = _make_ohlcv(200)
        features = fe.engineer_features(df)
        selected = fe.select_features(features, top_k=10, method="variance")
        assert selected.shape[1] <= 10

    def test_normalize(self):
        fe = FeatureEngineer(FeatureConfig(normalize=True))
        df = _make_ohlcv(200)
        features = fe.engineer_features(df)
        numeric_cols = features.select_dtypes(include=[np.number]).columns
        means = features[numeric_cols].mean()
        # Normalized features should have reasonable means (not exact zero due to NaN handling)
        assert all(abs(m) < 10.0 for m in means.dropna())


# ── Signal Generator Tests ──────────────────────────────────────────────


class TestSignalGenerator:
    def test_init(self):
        gen = SignalGenerator()
        assert gen._min_confidence >= 0.0

    def test_add_model(self):
        gen = SignalGenerator()

        class DummyModel:
            is_trained = False
            name = "dummy"

            def predict(self, X):
                return []

        gen.add_model(DummyModel())
        assert len(gen._models) == 1

    def test_generate_signals_empty(self):
        gen = SignalGenerator()
        signals = gen.generate_signals({})
        assert signals == []

    def test_trading_signal_fields(self):
        signal = TradingSignal(
            symbol="XAUUSD",
            direction=1,
            strength=0.8,
            confidence=0.75,
            suggested_size=0.01,
            models_agree=True,
            metadata={"source": "test"},
        )
        assert signal.symbol == "XAUUSD"
        assert signal.direction == 1
        assert signal.strength == 0.8
        assert signal.confidence == 0.75
        assert signal.models_agree is True
        assert signal.metadata["source"] == "test"


# ── Model Manager Tests ────────────────────────────────────────────────


class TestModelManager:
    def test_register_model(self):
        mm = ModelManager()

        class DummyModel:
            def predict(self, X):
                return np.zeros(len(X))

        model = DummyModel()
        info = mm.register_model("test_model", model)
        assert info.name == "test_model"
        assert info.status == ModelStatus.REGISTERED

    def test_list_models(self):
        mm = ModelManager()

        class DummyModel:
            def predict(self, X):
                return np.zeros(len(X))

        mm.register_model("m1", DummyModel())
        mm.register_model("m2", DummyModel())
        assert sorted(mm.list_models()) == ["m1", "m2"]

    def test_health_check(self):
        mm = ModelManager()

        class DummyModel:
            def predict(self, X):
                return np.zeros(len(X))

        mm.register_model("test_model", DummyModel())
        health = mm.health_check("test_model")
        assert "healthy" in health
