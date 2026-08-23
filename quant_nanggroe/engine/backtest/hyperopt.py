"""Bayesian Hyperopt Engine — smarter than grid search.

Uses sklearn's GaussianProcessRegressor as a surrogate model to
intelligently explore the parameter space instead of brute-forcing
every combination. Fewer evaluations, better results.

Usage:
    from quant_nanggroe.engine.backtest.hyperopt import BayesianOptimizer

    optimizer = BayesianOptimizer(
        param_space={"period": (10, 50), "threshold": (40, 80)},
        n_trials=30,
    )
    best = optimizer.optimize(evaluate_fn)
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Tuple

import numpy as np

logger = logging.getLogger("QNA.Hyperopt")


class BayesianOptimizer:
    """Bayesian optimization for strategy parameter tuning.

    Uses a Gaussian Process to model the objective function and
    select the next most promising parameters to evaluate.
    """

    def __init__(
        self,
        param_space: Dict[str, Tuple[float, float]],
        n_trials: int = 25,
        n_startup: int = 8,
        early_stop_patience: int = 10,
    ):
        """
        Args:
            param_space: {param_name: (min_val, max_val)} — continuous ranges
            n_trials: total number of evaluations
            n_startup: random exploration before GP kicks in
            early_stop_patience: stop if no improvement in N trials
        """
        self.param_space = param_space
        self.param_names = list(param_space.keys())
        self.bounds = np.array([param_space[k] for k in self.param_names])
        self.n_trials = n_trials
        self.n_startup = max(n_startup, 2)
        self.patience = early_stop_patience

    def _to_vector(self, params: Dict[str, float]) -> np.ndarray:
        return np.array([params[name] for name in self.param_names])

    def _from_vector(self, vec: np.ndarray) -> Dict[str, float]:
        return {name: round(float(v), 4)
                for name, v in zip(self.param_names, vec)}

    def optimize(
        self,
        objective_fn: Callable[[Dict[str, float]], float],
        maximize: bool = True,
    ) -> Dict[str, Any]:
        """Run Bayesian optimization.

        Args:
            objective_fn: takes params dict → returns score (higher=better if maximize)
            maximize: if False, minimizes the objective

        Returns:
            {"best_params": dict, "best_score": float,
             "all_evaluations": [...], "n_trials": int}
        """
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import Matern
        try:
            from scipy.stats import norm
        except ImportError:
            # fallback to random search if scipy missing
            return self._random_search(objective_fn, maximize)

        X_observed: List[np.ndarray] = []
        y_observed: List[float] = []
        all_results: List[Dict] = []
        sign = 1.0 if maximize else -1.0

        best_score = -np.inf
        best_params: Dict = {}
        no_improve_count = 0

        for trial in range(self.n_trials):
            if trial < self.n_startup or len(X_observed) < 2:
                # Random exploration during startup phase
                candidate = self._random_point()
            else:
                # Fit GP and find next point via Expected Improvement
                X_arr = np.array(X_observed)
                y_arr = np.array(y_observed) * sign  # always maximizing internally

                gp = GaussianProcessRegressor(
                    kernel=Matern(nu=2.5),
                    alpha=1e-6,
                    normalize_y=True,
                    random_state=trial,
                )
                gp.fit(X_arr, y_arr)

                # Sample candidates and pick best by Expected Improvement
                candidates = np.random.uniform(
                    self.bounds[:, 0], self.bounds[:, 1], size=(200, len(self.param_names))
                )
                mu, sigma = gp.predict(candidates, return_std=True)
                y_best = y_arr.max()

                # Expected Improvement
                z = (mu - y_best) / (sigma + 1e-9)
                from scipy.stats import norm as _norm
                ei = (mu - y_best) * _norm.cdf(z) + sigma * _norm.pdf(z)

                best_idx = int(np.argmax(ei))
                candidate = candidates[best_idx]

            params = self._from_vector(candidate)
            score = objective_fn(params)
            signed_score = score * sign

            X_observed.append(candidate)
            y_observed.append(signed_score)
            all_results.append({"params": params, "score": score})

            if signed_score > best_score:
                best_score = signed_score
                best_params = params
                no_improve_count = 0
            else:
                no_improve_count += 1
                if no_improve_count >= self.patience:
                    logger.info("Early stopping at trial %d (%d without improvement)",
                                trial + 1, no_improve_count)
                    break

        return {
            "best_params": best_params,
            "best_score": round(best_score * sign, 6),
            "all_evaluations": all_results,
            "n_trials": len(all_results),
        }

    def _random_point(self) -> np.ndarray:
        return np.random.uniform(
            self.bounds[:, 0], self.bounds[:, 1]
        )

    @staticmethod
    def _norm_cdf(x):
        import math
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    @staticmethod
    def _norm_pdf(x):
        return np.exp(-0.5 * x ** 2) / np.sqrt(2 * np.pi)

    def _random_search(self, objective_fn, maximize) -> Dict:
        best_score = -np.inf if maximize else np.inf
        best_params: Dict = {}
        results = []
        for _ in range(self.n_trials):
            p = self._from_vector(self._random_point())
            s = objective_fn(p)
            results.append({"params": p, "score": s})
            if (maximize and s > best_score) or (not maximize and s < best_score):
                best_score = s
                best_params = p
        return {"best_params": best_params, "best_score": best_score,
                "all_evaluations": results, "n_trials": self.n_trials}
