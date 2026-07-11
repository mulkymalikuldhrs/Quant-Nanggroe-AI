"""
Monte Carlo Stress Testing
Runs up to 100,000 simulations for portfolio stress testing.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class MonteCarloResult:
    n_simulations: int
    n_days: int
    final_prices: np.ndarray
    final_returns: np.ndarray
    mean_final: float
    std_final: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    max_drawdown: float
    probability_positive: float
    percentiles: Dict[str, float]
    simulation_paths: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class MonteCarloSimulator:
    """
    Monte Carlo simulator for portfolio stress testing.

    Supports:
    - Geometric Brownian Motion (GBM)
    - Jump diffusion (Merton model)
    - Regime-switching simulations
    - Correlated multi-asset simulations
    - Custom volatility surfaces
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.seed = self.config.get("seed", 42)
        self.rng = np.random.default_rng(self.seed)

    def simulate_gbm(self, prices: pd.Series, n_simulations: int = 10000,
                      n_days: int = 252, keep_paths: int = 1000) -> MonteCarloResult:
        """Geometric Brownian Motion simulation"""
        log_returns = np.log(prices / prices.shift(1)).dropna()
        mu = log_returns.mean()
        sigma = log_returns.std()
        last_price = prices.iloc[-1]

        dt = 1.0
        all_paths = np.zeros((n_simulations, n_days))
        all_paths[:, 0] = last_price

        for i in range(n_simulations):
            for t in range(1, n_days):
                epsilon = self.rng.normal(0, 1)
                all_paths[i, t] = all_paths[i, t-1] * np.exp(
                    (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * epsilon
                )

        return self._compute_results(all_paths, n_simulations, keep_paths, "GBM")

    def simulate_jump_diffusion(self, prices: pd.Series, n_simulations: int = 10000,
                                  n_days: int = 252, jump_intensity: float = 0.1,
                                  jump_mean: float = -0.02, jump_std: float = 0.03,
                                  keep_paths: int = 1000) -> MonteCarloResult:
        """Merton jump diffusion model"""
        log_returns = np.log(prices / prices.shift(1)).dropna()
        mu = log_returns.mean()
        sigma = log_returns.std()
        last_price = prices.iloc[-1]

        dt = 1.0
        all_paths = np.zeros((n_simulations, n_days))
        all_paths[:, 0] = last_price
        lambda_j = jump_intensity

        for i in range(n_simulations):
            for t in range(1, n_days):
                n_jumps = self.rng.poisson(lambda_j * dt)
                jump_sum = np.sum(self.rng.normal(jump_mean, jump_std, n_jumps))
                epsilon = self.rng.normal(0, 1)
                all_paths[i, t] = all_paths[i, t-1] * np.exp(
                    (mu - 0.5 * sigma**2 - lambda_j * jump_mean) * dt
                    + sigma * np.sqrt(dt) * epsilon + jump_sum
                )

        return self._compute_results(all_paths, n_simulations, keep_paths, "JumpDiffusion")

    def simulate_regime_switching(self, prices: pd.Series,
                                    regimes: np.ndarray,
                                    regime_stats: Dict[str, Dict],
                                    n_simulations: int = 10000,
                                    n_days: int = 252,
                                    keep_paths: int = 1000) -> MonteCarloResult:
        """Regime-switching Monte Carlo simulation"""
        last_price = prices.iloc[-1]
        all_paths = np.zeros((n_simulations, n_days))
        all_paths[:, 0] = last_price
        dt = 1.0

        regime_labels = list(regime_stats.keys())
        transition_probs = self._estimate_transitions(regimes, regime_labels)

        for i in range(n_simulations):
            current_regime = self.rng.choice(regime_labels)
            for t in range(1, n_days):
                stats = regime_stats[current_regime]
                mu, sigma = stats["mu"], stats["sigma"]

                epsilon = self.rng.normal(0, 1)
                all_paths[i, t] = all_paths[i, t-1] * np.exp(
                    (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * epsilon
                )

                if self.rng.random() < transition_probs.get(current_regime, 0.01):
                    current_regime = self.rng.choice(regime_labels)

        return self._compute_results(all_paths, n_simulations, keep_paths, "RegimeSwitching")

    def simulate_correlated(self, price_data: Dict[str, pd.Series],
                              n_simulations: int = 10000, n_days: int = 252,
                              keep_paths: int = 100) -> Dict[str, MonteCarloResult]:
        """Correlated multi-asset simulation"""
        assets = list(price_data.keys())
        n_assets = len(assets)

        returns_matrix = []
        for asset, prices in price_data.items():
            log_ret = np.log(prices / prices.shift(1)).dropna()
            returns_matrix.append(log_ret.values)

        returns_matrix = np.array(returns_matrix)
        corr = np.corrcoef(returns_matrix)

        try:
            L = np.linalg.cholesky(corr)
        except np.linalg.LinAlgError:
            corr += np.eye(n_assets) * 0.01
            L = np.linalg.cholesky(corr)

        last_prices = np.array([price_data[a].iloc[-1] for a in assets])
        mus = np.array([np.mean(r) for r in returns_matrix])
        sigmas = np.array([np.std(r) for r in returns_matrix])

        results = {}
        all_asset_paths = np.zeros((n_assets, n_simulations, n_days))

        for i in range(n_simulations):
            eps = self.rng.normal(0, 1, (n_days, n_assets))
            correlated_eps = eps @ L.T

            for a in range(n_assets):
                path = np.zeros(n_days)
                path[0] = last_prices[a]
                for t in range(1, n_days):
                    path[t] = path[t-1] * np.exp(
                        (mus[a] - 0.5 * sigmas[a]**2) + sigmas[a] * correlated_eps[t-1, a]
                    )
                all_asset_paths[a, i, :] = path

        for a, asset in enumerate(assets):
            results[asset] = self._compute_results(
                all_asset_paths[a], n_simulations, keep_paths, f"Correlated({asset})"
            )

        return results

    def _compute_results(self, all_paths: np.ndarray, n_simulations: int,
                           keep_paths: int, method: str) -> MonteCarloResult:
        """Compute statistics from simulation paths"""
        n_days = all_paths.shape[1]
        final_prices = all_paths[:, -1]
        final_returns = (final_prices / all_paths[:, 0]) - 1

        sorted_returns = np.sort(final_returns)
        n = len(sorted_returns)

        result = MonteCarloResult(
            n_simulations=n_simulations,
            n_days=n_days,
            final_prices=final_prices,
            final_returns=final_returns,
            mean_final=float(np.mean(final_prices)),
            std_final=float(np.std(final_prices)),
            var_95=float(np.percentile(final_returns, 5)),
            var_99=float(np.percentile(final_returns, 1)),
            cvar_95=float(np.mean(sorted_returns[:max(1, int(0.05 * n))])),
            cvar_99=float(np.mean(sorted_returns[:max(1, int(0.01 * n))])),
            max_drawdown=float(self._compute_max_drawdown(all_paths)),
            probability_positive=float(np.mean(final_returns > 0)),
            percentiles={
                "p1": float(np.percentile(final_returns, 1)),
                "p5": float(np.percentile(final_returns, 5)),
                "p25": float(np.percentile(final_returns, 25)),
                "p50": float(np.percentile(final_returns, 50)),
                "p75": float(np.percentile(final_returns, 75)),
                "p95": float(np.percentile(final_returns, 95)),
                "p99": float(np.percentile(final_returns, 99)),
            },
            simulation_paths=all_paths[:min(keep_paths, n_simulations)],
            metadata={"method": method, "n_simulations": n_simulations},
        )
        return result

    def _compute_max_drawdown(self, paths: np.ndarray) -> float:
        """Compute maximum drawdown across all paths"""
        peaks = np.maximum.accumulate(paths, axis=1)
        drawdowns = (paths - peaks) / peaks
        return float(np.min(drawdowns))

    def _estimate_transitions(self, regimes: np.ndarray, labels: List[str]) -> Dict[str, float]:
        """Estimate regime transition probabilities"""
        probs = {}
        n = len(regimes)
        for label in labels:
            same_regime = np.sum((regimes[:-1] == label) & (regimes[1:] == label))
            total = np.sum(regimes[:-1] == label)
            probs[label] = 1.0 - (same_regime / max(total, 1))
        return probs
