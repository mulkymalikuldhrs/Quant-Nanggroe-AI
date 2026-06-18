"""Options Analyzer — Black-Scholes pricing, Greeks, IV, chain analysis.

Provides comprehensive options analysis including:
- Black-Scholes pricing (European)
- Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- Implied volatility calculation (Newton-Raphson)
- Options chain analysis
- Straddle/strangle/butterfly analysis

Ported from ai-hedge-fund/src/options/options_analyzer.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from math import exp, log, sqrt
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)


class OptionType(str, Enum):
    """Option types."""

    CALL = "CALL"
    PUT = "PUT"


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
    """Implied volatility calculation result."""

    iv: float = 0.0
    success: bool = False
    error: Optional[str] = None


class BlackScholes:
    """Black-Scholes option pricing model.

    Supports European options on non-dividend paying stocks.
    """

    def __init__(self, S: float, K: float, T: float, r: float, sigma: float) -> None:
        """Initialize Black-Scholes model.

        Args:
            S: Current underlying price.
            K: Strike price.
            T: Time to maturity (in years).
            r: Risk-free rate.
            sigma: Volatility (annualized).
        """
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma

        # Pre-compute d1, d2
        if T > 0 and sigma > 0:
            self.d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
            self.d2 = self.d1 - sigma * sqrt(T)
        else:
            self.d1 = 0.0
            self.d2 = 0.0

    def price(self, option_type: OptionType) -> float:
        """Calculate option price.

        Args:
            option_type: CALL or PUT.

        Returns:
            Option price.
        """
        if self.T <= 0:
            if option_type == OptionType.CALL:
                return max(0.0, self.S - self.K)
            else:
                return max(0.0, self.K - self.S)

        if option_type == OptionType.CALL:
            return self.S * norm.cdf(self.d1) - self.K * exp(-self.r * self.T) * norm.cdf(self.d2)
        else:
            return self.K * exp(-self.r * self.T) * norm.cdf(-self.d2) - self.S * norm.cdf(-self.d1)

    def greeks(self, option_type: OptionType) -> OptionGreeks:
        """Calculate option Greeks.

        Args:
            option_type: CALL or PUT.

        Returns:
            OptionGreeks with all Greek values.
        """
        sqrt_T = sqrt(self.T) if self.T > 0 else 0.0

        # Delta
        if option_type == OptionType.CALL:
            delta = norm.cdf(self.d1)
        else:
            delta = norm.cdf(self.d1) - 1

        # Gamma
        gamma = norm.pdf(self.d1) / (self.S * self.sigma * sqrt_T) if self.T > 0 else 0.0

        # Vega (per 1% vol change)
        vega = self.S * norm.pdf(self.d1) * sqrt_T / 100 if self.T > 0 else 0.0

        # Theta (per day)
        if self.T > 0:
            if option_type == OptionType.CALL:
                theta = (
                    -(self.S * norm.pdf(self.d1) * self.sigma / (2 * sqrt_T))
                    - self.r * self.K * exp(-self.r * self.T) * norm.cdf(self.d2)
                ) / 365
            else:
                theta = (
                    -(self.S * norm.pdf(self.d1) * self.sigma / (2 * sqrt_T))
                    + self.r * self.K * exp(-self.r * self.T) * norm.cdf(-self.d2)
                ) / 365
        else:
            theta = 0.0

        # Rho (per 1% rate change)
        if option_type == OptionType.CALL:
            rho = self.K * self.T * exp(-self.r * self.T) * norm.cdf(self.d2) / 100
        else:
            rho = -self.K * self.T * exp(-self.r * self.T) * norm.cdf(-self.d2) / 100

        return OptionGreeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)

    def implied_volatility(
        self,
        market_price: float,
        option_type: OptionType,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> ImpliedVolatilityResult:
        """Calculate implied volatility using Newton-Raphson.

        Args:
            market_price: Market price of the option.
            option_type: CALL or PUT.
            max_iterations: Maximum iterations.
            tolerance: Convergence tolerance.

        Returns:
            ImpliedVolatilityResult.
        """
        if market_price <= 0:
            return ImpliedVolatilityResult(0, False, "Invalid market price")

        # Check arbitrage bounds
        intrinsic = max(0, self.S - self.K * exp(-self.r * self.T)) if option_type == OptionType.CALL else max(0, self.K * exp(-self.r * self.T) - self.S)
        if market_price < intrinsic:
            return ImpliedVolatilityResult(0, False, "Price below intrinsic value")

        sigma = 0.5  # Initial guess

        for _ in range(max_iterations):
            bs = BlackScholes(self.S, self.K, self.T, self.r, sigma)
            price = bs.price(option_type)
            greeks = bs.greeks(option_type)

            diff = market_price - price

            if abs(diff) < tolerance:
                return ImpliedVolatilityResult(sigma * 100, True)

            # Newton-Raphson update
            vega_scaled = greeks.vega * 100  # Adjust for vega scaling
            if vega_scaled != 0:
                sigma = sigma + diff / vega_scaled

            sigma = max(0.01, min(sigma, 5.0))

        return ImpliedVolatilityResult(sigma * 100, False, "Did not converge")


class OptionsAnalyzer:
    """Comprehensive Options Analyzer.

    Features:
    - Black-Scholes pricing
    - Greeks calculation
    - Implied volatility calculation
    - Options chain analysis
    - Straddle/strangle/butterfly analysis
    """

    def __init__(self, risk_free_rate: float = 0.02) -> None:
        """Initialize options analyzer.

        Args:
            risk_free_rate: Annual risk-free rate.
        """
        self.risk_free_rate = risk_free_rate

    def price_option(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
        option_type: OptionType,
    ) -> Tuple[float, OptionGreeks]:
        """Price an option and calculate Greeks.

        Args:
            S: Underlying price.
            K: Strike price.
            T: Time to maturity (years).
            sigma: Annualized volatility.
            option_type: CALL or PUT.

        Returns:
            Tuple of (price, greeks).
        """
        bs = BlackScholes(S, K, T, self.risk_free_rate, sigma)
        return bs.price(option_type), bs.greeks(option_type)

    def calculate_implied_volatility(
        self,
        S: float,
        K: float,
        T: float,
        market_price: float,
        option_type: OptionType,
    ) -> ImpliedVolatilityResult:
        """Calculate implied volatility from market price.

        Args:
            S: Underlying price.
            K: Strike price.
            T: Time to maturity (years).
            market_price: Observed option price.
            option_type: CALL or PUT.

        Returns:
            ImpliedVolatilityResult.
        """
        bs = BlackScholes(S, K, T, self.risk_free_rate, 0.5)
        return bs.implied_volatility(market_price, option_type)

    def analyze_chain(
        self,
        S: float,
        T: float,
        sigma: float,
        strikes: List[float],
        option_type: OptionType,
    ) -> List[Dict]:
        """Analyze an options chain.

        Args:
            S: Current underlying price.
            T: Time to expiration (years).
            sigma: Volatility.
            strikes: List of strike prices.
            option_type: CALL or PUT.

        Returns:
            List of dicts with prices and Greeks per strike.
        """
        results = []
        for K in strikes:
            price, greeks = self.price_option(S, K, T, sigma, option_type)
            moneyness = (
                "ITM"
                if (option_type == OptionType.CALL and S > K) or (option_type == OptionType.PUT and S < K)
                else "OTM"
            )
            results.append({
                "strike": K,
                "price": price,
                "delta": greeks.delta,
                "gamma": greeks.gamma,
                "theta": greeks.theta,
                "vega": greeks.vega,
                "rho": greeks.rho,
                "moneyness": moneyness,
            })
        return results

    def analyze_straddle(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
    ) -> Dict:
        """Analyze long straddle strategy.

        Args:
            S: Underlying price.
            K: Strike price.
            T: Time to expiration (years).
            sigma: Volatility.

        Returns:
            Dict with straddle analysis.
        """
        call_price, call_greeks = self.price_option(S, K, T, sigma, OptionType.CALL)
        put_price, put_greeks = self.price_option(S, K, T, sigma, OptionType.PUT)
        total_premium = call_price + put_price

        return {
            "strategy": "Long Straddle",
            "call_premium": call_price,
            "put_premium": put_price,
            "total_premium": total_premium,
            "upper_breakeven": K + total_premium,
            "lower_breakeven": K - total_premium,
            "implied_move_pct": (total_premium / S) * 100 if S > 0 else 0,
            "delta_neutral": call_greeks.delta + put_greeks.delta,
        }

    def analyze_strangle(
        self,
        S: float,
        K_call: float,
        K_put: float,
        T: float,
        sigma: float,
    ) -> Dict:
        """Analyze long strangle strategy.

        Args:
            S: Underlying price.
            K_call: Call strike (above S).
            K_put: Put strike (below S).
            T: Time to expiration.
            sigma: Volatility.

        Returns:
            Dict with strangle analysis.
        """
        call_price, call_greeks = self.price_option(S, K_call, T, sigma, OptionType.CALL)
        put_price, put_greeks = self.price_option(S, K_put, T, sigma, OptionType.PUT)
        total_premium = call_price + put_price

        return {
            "strategy": "Long Strangle",
            "call_premium": call_price,
            "put_premium": put_price,
            "total_premium": total_premium,
            "upper_breakeven": K_call + total_premium,
            "lower_breakeven": K_put - total_premium,
            "implied_move_pct": (total_premium / S) * 100 if S > 0 else 0,
        }

    def analyze_butterfly(
        self,
        S: float,
        K_low: float,
        K_mid: float,
        K_high: float,
        T: float,
        sigma: float,
    ) -> Dict:
        """Analyze long butterfly spread.

        Args:
            S: Underlying price.
            K_low: Lower strike.
            K_mid: Middle strike.
            K_high: Higher strike.
            T: Time to expiration.
            sigma: Volatility.

        Returns:
            Dict with butterfly analysis.
        """
        # Long 1 low call, short 2 mid calls, long 1 high call
        low_call_price, _ = self.price_option(S, K_low, T, sigma, OptionType.CALL)
        mid_call_price, _ = self.price_option(S, K_mid, T, sigma, OptionType.CALL)
        high_call_price, _ = self.price_option(S, K_high, T, sigma, OptionType.CALL)

        net_debit = low_call_price - 2 * mid_call_price + high_call_price

        max_profit = (K_mid - K_low) - net_debit
        max_loss = net_debit

        return {
            "strategy": "Long Butterfly",
            "net_debit": net_debit,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "breakeven_lower": K_low + net_debit,
            "breakeven_upper": K_high - net_debit,
            "risk_reward_ratio": max_profit / abs(max_loss) if max_loss != 0 else 0,
        }
