"""Tests for ML Signal Generator Module."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.ml.signal_generator import (
    MLSignal,
    MLSignalGenerator,
    SignalDirection,
    SimpleGradientBoostingModel,
    SimpleRandomForestModel,
)
from quant_nanggroe.engine.ml.feature_engineer import (
    FeatureConfig,
    FeatureEngineer,
)
from quant_nanggroe.engine.ml.model_manager import (
    ModelInfo,
    ModelManager,
    ModelStatus,
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
        # Normalized features should have near-zero mean
        numeric_cols = features.select_dtypes(include=[np.number]).columns
        means = features[numeric_cols].mean()
        assert all(abs(m) < 1.0 for m in means.dropna())


# ── Simple ML Model Tests ─────────────────────────────────────────────


class TestSimpleRandomForestModel:
    def test_train_predict(self):
        model = SimpleRandomForestModel(n_estimators=10, max_depth=3)
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.choice([-1, 0, 1], size=100))

        metrics = model.train(X, y)
        assert model.is_trained
        assert "n_trees" in metrics

        preds = model.predict(X)
        assert len(preds) == len(X)

    def test_feature_importance(self):
        model = SimpleRandomForestModel(n_estimators=10, max_depth=3)
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.choice([-1, 0, 1], size=100))
        model.train(X, y)
        importance = model.feature_importance()
        assert isinstance(importance, dict)
        assert len(importance) == 5

    def test_predict_untrained(self):
        model = SimpleRandomForestModel()
        X = pd.DataFrame(np.random.randn(10, 5))
        with pytest.raises(RuntimeError):
            model.predict(X)


class TestSimpleGradientBoostingModel:
    def test_train_predict(self):
        model = SimpleGradientBoostingModel(n_estimators=20, learning_rate=0.1)
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))

        metrics = model.train(X, y)
        assert model.is_trained
        assert "n_trees" in metrics

        preds = model.predict(X)
        assert len(preds) == len(X)

    def test_feature_importance(self):
        model = SimpleGradientBoostingModel(n_estimators=20)
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))
        model.train(X, y)
        importance = model.feature_importance()
        assert isinstance(importance, dict)


# ── ML Signal Generator Tests ──────────────────────────────────────────


class TestMLSignalGenerator:
    def test_init(self):
        gen = MLSignalGenerator()
        assert gen.feature_engineer is not None
        assert gen.model_manager is not None

    def test_add_model(self):
        gen = MLSignalGenerator()
        gen.add_model("gbm")
        assert "gbm" in gen.model_manager.list_models()

    def test_train_and_signal(self):
        gen = MLSignalGenerator()
        gen.add_model("rf", SimpleRandomForestModel(n_estimators=10, max_depth=3))
        gen.add_model("gbm", SimpleGradientBoostingModel(n_estimators=10))

        df = _make_ohlcv(300)
        results = gen.train(df, target_period=5, min_samples=50)
        assert isinstance(results, dict)
        assert len(results) > 0

        signal = gen.generate_signal(df)
        assert isinstance(signal, MLSignal)
        assert signal.direction in [d for d in SignalDirection]

    def test_generate_signal_no_models(self):
        gen = MLSignalGenerator()
        df = _make_ohlcv(200)
        signal = gen.generate_signal(df)
        assert signal.direction == SignalDirection.HOLD
        assert signal.confidence == 0.0


# ── Model Manager Tests ────────────────────────────────────────────────


class TestModelManager:
    def test_register_model(self):
        mm = ModelManager()
        model = SimpleGradientBoostingModel()
        info = mm.register_model("test_model", model)
        assert info.name == "test_model"
        assert info.status == ModelStatus.REGISTERED

    def test_train_model(self):
        mm = ModelManager()
        model = SimpleGradientBoostingModel(n_estimators=10)
        mm.register_model("test_model", model)

        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))

        result = mm.train_model("test_model", X, y)
        assert result.success
        assert result.model_name == "test_model"

    def test_train_nonexistent(self):
        mm = ModelManager()
        X = pd.DataFrame(np.random.randn(100, 5))
        y = pd.Series(np.random.randn(100))
        result = mm.train_model("nonexistent", X, y)
        assert not result.success

    def test_predict(self):
        mm = ModelManager()
        model = SimpleGradientBoostingModel(n_estimators=10)
        mm.register_model("test_model", model)

        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))
        mm.train_model("test_model", X, y)

        result = mm.predict("test_model", X.tail(5))
        assert result.model_name == "test_model"
        assert len(result.predictions) == 5

    def test_predict_untrained(self):
        mm = ModelManager()
        model = SimpleGradientBoostingModel()
        mm.register_model("test_model", model)
        X = pd.DataFrame(np.random.randn(10, 5))
        result = mm.predict("test_model", X)
        assert result.error is not None

    def test_list_models(self):
        mm = ModelManager()
        mm.register_model("m1", SimpleGradientBoostingModel())
        mm.register_model("m2", SimpleRandomForestModel())
        assert sorted(mm.list_models()) == ["m1", "m2"]

    def test_health_check(self):
        mm = ModelManager()
        model = SimpleGradientBoostingModel(n_estimators=10)
        mm.register_model("test_model", model)

        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))
        mm.train_model("test_model", X, y)

        health = mm.health_check("test_model")
        assert health["healthy"] is True
        assert health["status"] == "trained"

    def test_deprecate_model(self):
        mm = ModelManager()
        mm.register_model("test_model", SimpleGradientBoostingModel())
        assert mm.deprecate_model("test_model")
        info = mm.get_model_info("test_model")
        assert info.status == ModelStatus.DEPRECATED

    def test_training_history(self):
        mm = ModelManager()
        model = SimpleGradientBoostingModel(n_estimators=10)
        mm.register_model("test_model", model)

        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(np.random.randn(100))
        mm.train_model("test_model", X, y)

        history = mm.get_training_history()
        assert len(history) == 1
        assert history[0].model_name == "test_model"
