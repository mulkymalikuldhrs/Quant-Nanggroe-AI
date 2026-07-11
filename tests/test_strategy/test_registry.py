"""Tests for the StrategyMetaRegistry with walk-forward framework."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from quant_nanggroe.engine.strategy.registry import (
    StrategyMetaRegistry,
    StrategyMetadata,
    WalkForwardResult,
)


@pytest.fixture
def registry() -> StrategyMetaRegistry:
    reg = StrategyMetaRegistry()
    reg.register(
        name="Momentum",
        description="Time-series momentum",
        asset_classes=["crypto", "equity"],
        timeframe="1d",
        status="active",
    )
    reg.register(
        name="MeanReversion",
        description="Mean reversion strategy",
        asset_classes=["crypto"],
        timeframe="1h",
        status="active",
    )
    reg.register(
        name="BrokenStrategy",
        description="Poorly performing strategy",
        asset_classes=["equity"],
        timeframe="4h",
        status="development",
    )
    return reg


@pytest.fixture
def sample_wf_results() -> list[WalkForwardResult]:
    return [
        WalkForwardResult(
            window_index=0,
            train_start="2024-01-01",
            train_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-07-31",
            train_sharpe=2.0,
            test_sharpe=1.5,
            train_return=0.15,
            test_return=0.10,
            train_max_dd=-0.05,
            test_max_dd=-0.08,
            parameter_set={"lookback": 20},
        ),
        WalkForwardResult(
            window_index=1,
            train_start="2024-02-01",
            train_end="2024-07-31",
            test_start="2024-08-01",
            test_end="2024-08-31",
            train_sharpe=1.8,
            test_sharpe=1.6,
            train_return=0.12,
            test_return=0.11,
            train_max_dd=-0.04,
            test_max_dd=-0.06,
            parameter_set={"lookback": 20},
        ),
        WalkForwardResult(
            window_index=2,
            train_start="2024-03-01",
            train_end="2024-08-31",
            test_start="2024-09-01",
            test_end="2024-09-30",
            train_sharpe=2.2,
            test_sharpe=1.3,
            train_return=0.18,
            test_return=0.08,
            train_max_dd=-0.06,
            test_max_dd=-0.10,
            parameter_set={"lookback": 20},
        ),
    ]


class TestStrategyMetaRegistry:
    def test_register_and_get(self, registry: StrategyMetaRegistry) -> None:
        meta = registry.get("Momentum")
        assert meta is not None
        assert meta.name == "Momentum"
        assert meta.description == "Time-series momentum"
        assert meta.asset_classes == ["crypto", "equity"]
        assert meta.timeframe == "1d"
        assert meta.status == "active"
        assert meta.display_name == "Momentum"
        assert meta.created_at != ""
        assert meta.updated_at != ""

    def test_get_nonexistent(self, registry: StrategyMetaRegistry) -> None:
        assert registry.get("Nonsense") is None

    def test_list_all(self, registry: StrategyMetaRegistry) -> None:
        all_strats = registry.list()
        assert len(all_strats) == 3

    def test_list_by_status(self, registry: StrategyMetaRegistry) -> None:
        active = registry.list(status="active")
        assert len(active) == 2
        dev = registry.list(status="development")
        assert len(dev) == 1

    def test_list_no_match(self, registry: StrategyMetaRegistry) -> None:
        assert registry.list(status="disabled") == []

    def test_record_walk_forward(
        self, registry: StrategyMetaRegistry, sample_wf_results: list[WalkForwardResult]
    ) -> None:
        for r in sample_wf_results:
            registry.record_walk_forward("Momentum", r)
        meta = registry.get("Momentum")
        assert meta is not None
        assert len(meta.walk_forward_results) == 3
        assert len(meta.oos_sharpes) == 3
        assert len(meta.insample_sharpes) == 3
        assert meta.oos_sharpes == [1.5, 1.6, 1.3]

    def test_record_walk_forward_unregistered(self, registry: StrategyMetaRegistry, sample_wf_results: list[WalkForwardResult]) -> None:
        with pytest.raises(KeyError):
            registry.record_walk_forward("Unknown", sample_wf_results[0])

    def test_summary(self, registry: StrategyMetaRegistry, sample_wf_results: list[WalkForwardResult]) -> None:
        for r in sample_wf_results:
            registry.record_walk_forward("Momentum", r)
        summary = registry.summary("Momentum")
        assert summary["n_windows"] == 3
        assert summary["avg_train_sharpe"] == pytest.approx((2.0 + 1.8 + 2.2) / 3, abs=1e-3)
        assert summary["avg_test_sharpe"] == pytest.approx((1.5 + 1.6 + 1.3) / 3, abs=1e-3)
        assert summary["decay"] == pytest.approx(summary["avg_train_sharpe"] - summary["avg_test_sharpe"])

    def test_summary_empty(self, registry: StrategyMetaRegistry) -> None:
        summary = registry.summary("Momentum")
        assert summary["n_windows"] == 0

    def test_summary_nonexistent(self, registry: StrategyMetaRegistry) -> None:
        with pytest.raises(KeyError):
            registry.summary("Nonsense")

    def test_best_oos(
        self, registry: StrategyMetaRegistry, sample_wf_results: list[WalkForwardResult]
    ) -> None:
        for r in sample_wf_results:
            registry.record_walk_forward("Momentum", r)
        best = registry.best_oos(n=1)
        assert len(best) >= 1
        assert best[0]["name"] == "Momentum"

    def test_best_oos_multiple_strategies(self, registry: StrategyMetaRegistry) -> None:
        registry.record_walk_forward(
            "Momentum",
            WalkForwardResult(0, "a", "b", "c", "d", 2.0, 1.5, 0.1, 0.1, 0.0, 0.0),
        )
        registry.record_walk_forward(
            "Momentum",
            WalkForwardResult(1, "a", "b", "c", "d", 1.8, 1.4, 0.1, 0.1, 0.0, 0.0),
        )
        registry.record_walk_forward(
            "MeanReversion",
            WalkForwardResult(0, "a", "b", "c", "d", 1.0, 0.8, 0.1, 0.1, 0.0, 0.0),
        )
        best = registry.best_oos(n=2)
        assert len(best) == 2
        assert best[0]["name"] == "Momentum"
        assert best[1]["name"] == "MeanReversion"

    def test_best_oos_no_results(self, registry: StrategyMetaRegistry) -> None:
        assert registry.best_oos() == []

    def test_decayed_true(self, registry: StrategyMetaRegistry) -> None:
        registry.record_walk_forward(
            "Momentum",
            WalkForwardResult(0, "a", "b", "c", "d", 2.0, 0.5, 0.1, 0.05, 0.0, 0.0),
        )
        registry.record_walk_forward(
            "Momentum",
            WalkForwardResult(1, "a", "b", "c", "d", 2.0, 0.3, 0.1, 0.04, 0.0, 0.0),
        )
        assert registry.decayed("Momentum", threshold=0.5) is True

    def test_decayed_false(self, registry: StrategyMetaRegistry) -> None:
        registry.record_walk_forward(
            "Momentum",
            WalkForwardResult(0, "a", "b", "c", "d", 1.0, 0.9, 0.1, 0.08, 0.0, 0.0),
        )
        assert registry.decayed("Momentum", threshold=0.5) is False

    def test_decayed_no_results(self, registry: StrategyMetaRegistry) -> None:
        assert registry.decayed("Momentum") is False

    def test_decayed_nonexistent(self, registry: StrategyMetaRegistry) -> None:
        assert registry.decayed("Nonsense") is False

    def test_to_json_roundtrip(self, registry: StrategyMetaRegistry, sample_wf_results: list[WalkForwardResult]) -> None:
        for r in sample_wf_results:
            registry.record_walk_forward("Momentum", r)
        registry.record_walk_forward(
            "MeanReversion",
            WalkForwardResult(0, "a", "b", "c", "d", 1.0, 0.8, 0.1, 0.05, -0.03, -0.06),
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            registry.to_json(f.name)
        loaded = StrategyMetaRegistry.from_json(path)
        Path(path).unlink()
        assert loaded.get("Momentum") is not None
        assert loaded.get("MeanReversion") is not None
        assert len(loaded.get("Momentum").walk_forward_results) == 3
        assert len(loaded.get("MeanReversion").walk_forward_results) == 1
        mom_summary = loaded.summary("Momentum")
        assert mom_summary["n_windows"] == 3
        assert mom_summary["avg_train_sharpe"] == pytest.approx((2.0 + 1.8 + 2.2) / 3)
        mr = loaded.get("Momentum")
        assert mr.display_name == "Momentum"
        assert mr.timeframe == "1d"

    def test_empty_json_roundtrip(self) -> None:
        reg = StrategyMetaRegistry()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            reg.to_json(f.name)
        loaded = StrategyMetaRegistry.from_json(path)
        Path(path).unlink()
        assert loaded.list() == []

    def test_params_schema(self, registry: StrategyMetaRegistry) -> None:
        registry.register(
            name="Custom",
            params_schema={"lookback": int, "threshold": float},
            status="development",
        )
        meta = registry.get("Custom")
        assert meta is not None
        assert meta.params_schema == {"lookback": int, "threshold": float}

    def test_params_schema_roundtrip(self, registry: StrategyMetaRegistry) -> None:
        registry.register(
            name="Custom",
            params_schema={"lookback": int, "threshold": float, "name": str},
            status="active",
        )
        registry.record_walk_forward(
            "Custom",
            WalkForwardResult(0, "a", "b", "c", "d", 1.0, 0.8, 0.1, 0.05, 0.0, 0.0),
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            registry.to_json(f.name)
        loaded = StrategyMetaRegistry.from_json(path)
        Path(path).unlink()
        meta = loaded.get("Custom")
        assert meta is not None
        assert meta.params_schema["lookback"] is int
        assert meta.params_schema["threshold"] is float
        assert meta.params_schema["name"] is str
