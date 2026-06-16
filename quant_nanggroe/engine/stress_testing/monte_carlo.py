import numpy as np
from dataclasses import dataclass, field

@dataclass
class MonteCarloResult:
    simulations: np.ndarray
    mean_final: float
    std_final: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    percentiles: dict[int, float]

class MonteCarloEngine:
    def __init__(self, n_simulations: int = 50000, horizon: int = 252, random_seed: int = 42):
        self.n = n_simulations
        self.horizon = horizon
        self.rng = np.random.default_rng(random_seed)

    def simulate(self, returns: np.ndarray, weights: np.ndarray) -> MonteCarloResult:
        mu = returns.mean() * self.horizon
        sigma = returns.std() * np.sqrt(self.horizon)
        cov = np.cov(returns.T) * self.horizon if returns.ndim > 1 else np.array([[sigma**2]])
        L = np.linalg.cholesky(cov) if returns.ndim > 1 else np.array([[sigma]])
        sims = np.zeros((self.n, self.horizon))
        for i in range(self.n):
            epsilon = self.rng.normal(size=(self.horizon, cov.shape[0]))
            daily_returns = epsilon @ L.T
            if returns.ndim > 1:
                port_returns = daily_returns @ weights
            else:
                port_returns = daily_returns.flatten()
            cum_return = np.exp(np.cumsum(port_returns))[-1] - 1
            sims[i] = port_returns
        final_values = np.exp(np.cumsum(sims, axis=1))[:, -1] - 1
        return MonteCarloResult(
            simulations=sims,
            mean_final=float(np.mean(final_values)),
            std_final=float(np.std(final_values)),
            var_95=float(np.percentile(final_values, 5)),
            var_99=float(np.percentile(final_values, 1)),
            cvar_95=float(np.mean(final_values[final_values <= np.percentile(final_values, 5)])),
            cvar_99=float(np.mean(final_values[final_values <= np.percentile(final_values, 1)])),
            percentiles={p: float(np.percentile(final_values, p)) for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]}
        )
