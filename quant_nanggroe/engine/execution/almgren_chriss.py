import numpy as np
from scipy.optimize import minimize
from dataclasses import dataclass

@dataclass
class ExecutionSchedule:
    times: list[float]
    shares: list[float]
    prices: list[float]
    total_cost: float
    implementation_shortfall: float

class AlmgrenChrissModel:
    def __init__(self, volatility: float = 0.3, spread: float = 0.001, risk_aversion: float = 0.1, daily_volume: float = 1e6):
        self.sigma = volatility
        self.spread = spread
        self.lam = risk_aversion
        self.V = daily_volume

    def optimize(self, order_size: float, horizon: int = 60, n_slices: int = 10) -> ExecutionSchedule:
        eta = 0.142
        gamma = 0.012
        kappa = np.sqrt(self.lam * self.sigma**2 / (2 * eta * gamma))
        times = np.linspace(0, horizon, n_slices)
        T = horizon
        tau = T / n_slices

        def x(t):
            return order_size * np.sinh(kappa * (T - t)) / np.sinh(kappa * T)

        schedule = []
        for i, t in enumerate(times):
            remaining = x(t)
            if i < len(times) - 1:
                shares_n = x(t) - x(t + tau)
            else:
                shares_n = remaining
            impact = eta * self.sigma * (shares_n / (self.V * tau / 252 / 390))**0.5
            price_impact = shares_n * impact
            schedule.append({"time": t, "shares": max(0, shares_n), "price_impact": price_impact})

        total_shares = sum(s["shares"] for s in schedule)
        if total_shares > 0:
            schedule = [{**s, "shares": s["shares"] * order_size / total_shares} for s in schedule]

        total_cost = sum(s["price_impact"] for s in schedule)
        return ExecutionSchedule(
            times=[s["time"] for s in schedule],
            shares=[s["shares"] for s in schedule],
            prices=[s.get("price_impact", 0) for s in schedule],
            total_cost=total_cost,
            implementation_shortfall=total_cost / order_size if order_size > 0 else 0,
        )

    def trajectory(self, order_size: float, horizon: int) -> np.ndarray:
        schedule = self.optimize(order_size, horizon)
        return np.array([sum(schedule.shares[:i+1]) for i in range(len(schedule.shares))])
