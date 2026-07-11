"""
Options Analyzer Module — Black-Scholes pricing, Greeks, implied volatility.

Provides BlackScholes, OptionGreeks, ImpliedVolatilityResult, OptionsAnalyzer.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from scipy import stats

logger = logging.getLogger(__name__)


class OptionType(str, Enum):
    """Option type enum."""
    CALL = "call"
    PUT = "put"


@dataclass
class OptionGreeks:
    """Option Greeks."""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0


@dataclass
class ImpliedVolatilityResult:
    """Result of implied volatility calculation."""
    iv: float
    method: str = "newton-raphson"
    iterations: int = 0
    converged: bool = True


class BlackScholes:
    """Black-Scholes option pricing model."""

    def __init__(self, S: float, K: float, T: float, r: float, sigma: float):
        """
        Args:
            S: Current asset price
            K: Strike price
            T: Time to expiration (years)
            r: Risk-free interest rate (decimal)
            sigma: Volatility (decimal)
        """
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma

    def price(self, option_type: OptionType) -> float:
        """Calculate option price using Black-Scholes formula."""
        if self.T <= 0:
            return max(0, (self.S - self.K) if option_type == OptionType.CALL
                       else (self.K - self.S))

        d1 = self._d1()
        d2 = self._d2()

        if option_type == OptionType.CALL:
            return (self.S * stats.norm.cdf(d1)
                    - self.K * math.exp(-self.r * self.T) * stats.norm.cdf(d2))
        else:
            return (self.K * math.exp(-self.r * self.T) * stats.norm.cdf(-d2)
                    - self.S * stats.norm.cdf(-d1))

    def greeks(self) -> OptionGreeks:
        """Calculate all option Greeks."""
        d1 = self._d1()
        d2 = self._d2()
        phi_d1 = stats.norm.pdf(d1)

        greeks = OptionGreeks()
        greeks.delta = stats.norm.cdf(d1)
        greeks.gamma = phi_d1 / (self.S * self.sigma * math.sqrt(self.T))
        greeks.theta = (-self.S * phi_d1 * self.sigma / (2 * math.sqrt(self.T))
                        - self.r * self.K * math.exp(-self.r * self.T) * stats.norm.cdf(d2))
        greeks.vega = self.S * phi_d1 * math.sqrt(self.T)
        greeks.rho = self.K * self.T * math.exp(-self.r * self.T) * stats.norm.cdf(d2)
        return greeks

    def _d1(self) -> float:
        return ((math.log(self.S / self.K)
                 + (self.r + 0.5 * self.sigma ** 2) * self.T)
                / (self.sigma * math.sqrt(self.T)))

    def _d2(self) -> float:
        return self._d1() - self.sigma * math.sqrt(self.T)


class OptionsAnalyzer:
    """Options analysis toolkit."""

    def __init__(self):
        self.models: Dict[str, BlackScholes] = {}

    def calculate_iv(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        market_price: float,
        option_type: OptionType = OptionType.CALL,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> ImpliedVolatilityResult:
        """Calculate implied volatility using Newton-Raphson."""
        sigma = 0.3
        for i in range(max_iter):
            bs = BlackScholes(S, K, T, r, sigma)
            price = bs.price(option_type)
            diff = price - market_price
            if abs(diff) < tol:
                return ImpliedVolatilityResult(
                    iv=sigma, iterations=i, converged=True
                )
            vega = bs.greeks().vega
            if abs(vega) < 1e-10:
                break
            sigma -= diff / vega
            if sigma <= 0:
                sigma = 0.01
                break
        return ImpliedVolatilityResult(
            iv=sigma, iterations=max_iter, converged=False
        )

    def analyze(self, S: float, K: float, T: float, r: float, sigma: float) -> Dict[str, Any]:
        """Full option analysis."""
        bs = BlackScholes(S, K, T, r, sigma)
        return {
            "call_price": bs.price(OptionType.CALL),
            "put_price": bs.price(OptionType.PUT),
            "greeks": bs.greeks(),
        }
