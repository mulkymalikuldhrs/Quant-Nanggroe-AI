"""Bayesian Hyperopt Engine tests."""
from __future__ import annotations

from quant_nanggroe.engine.backtest.hyperopt import BayesianOptimizer


class TestBayesianOptimizer:
    def test_finds_maximum(self):
        def objective(params):
            # simple parabola: max at x=5
            x = params["x"]
            return -(x - 5) ** 2

        opt = BayesianOptimizer(
            param_space={"x": (0, 10)}, n_trials=20, n_startup=5)
        result = opt.optimize(objective, maximize=True)
        assert abs(result["best_params"]["x"] - 5.0) < 2.0
        assert result["best_score"] > -1.0

    def test_finds_minimum_when_minimize(self):
        def objective(params):
            x = params["x"]
            return (x - 3) ** 2 + 1

        opt = BayesianOptimizer(
            param_space={"x": (0, 10)}, n_trials=15, n_startup=4)
        result = opt.optimize(objective, maximize=False)
        assert abs(result["best_params"]["x"] - 3.0) < 2.0

    def test_multi_param(self):
        def objective(params):
            x = params["a"]
            y = params["b"]
            return -(x - 2) ** 2 - (y - 7) ** 2

        opt = BayesianOptimizer(
            param_space={"a": (0, 10), "b": (0, 10)},
            n_trials=25, n_startup=6,
        )
        result = opt.optimize(objective, maximize=True)
        assert abs(result["best_params"]["a"] - 2.0) < 3.0
        assert abs(result["best_params"]["b"] - 7.0) < 3.0
