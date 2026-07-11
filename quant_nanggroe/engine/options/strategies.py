"""
Option Strategies Module
=========================
Multi-leg option strategy pricing, payoff, and risk analysis.

Referensi: optlib (dbrojas/optlib), vollib, finance-python.

Supported strategies:
- Single: Call, Put
- Vertical: Bull Call Spread, Bear Put Spread, etc.
- Multi-leg: Straddle, Strangle, Butterfly, Condor, Iron Condor
- Custom spreads
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class OptionSide(str, Enum):
    CALL = "call"
    PUT = "put"


class PositionType(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Leg:
    """Single leg of an option strategy."""
    side: OptionSide
    position: PositionType
    strike: float
    expiration: float       # years
    quantity: int = 1

    # Filled at evaluation
    premium: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0


@dataclass
class StrategyResult:
    """Evaluated option strategy."""
    name: str
    legs: list[Leg]
    net_premium: float = 0.0
    max_profit: float = float("inf")
    max_loss: float = float("-inf")
    break_even: list[float] = None
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    payoff_at_expiry: Optional[list[tuple[float, float]]] = None

    def __post_init__(self):
        if self.break_even is None:
            self.break_even = []

    def summary(self) -> str:
        return (
            f"{self.name}: Premium={self.net_premium:.4f} "
            f"Max P/L={self.max_profit:.4f}/{self.max_loss:.4f} "
            f"BE={self.break_even} | "
            f"Δ={self.total_delta:.4f} Γ={self.total_gamma:.4f} Θ={self.total_theta:.4f} "
            f"ν={self.total_vega:.4f}"
        )


# ── Black-Scholes Pricer (embedded, lightweight) ─────────────────────────


def _bs_price(F: float, K: float, T: float, sigma: float, r: float, side: OptionSide) -> float:
    """Black-76 option price (forward-based)."""
    if T <= 0:
        return max(0, (F - K) if side == OptionSide.CALL else (K - F))
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T) + 1e-10)
    d2 = d1 - sigma * np.sqrt(T)
    from scipy.stats import norm
    disc = np.exp(-r * T)
    if side == OptionSide.CALL:
        return float(disc * (F * norm.cdf(d1) - K * norm.cdf(d2)))
    else:
        return float(disc * (K * norm.cdf(-d2) - F * norm.cdf(-d1)))


def _bs_greeks(F: float, K: float, T: float, sigma: float, r: float, side: OptionSide) -> tuple[float, float, float, float]:  # noqa: E501
    """Return (delta, gamma, theta, vega) for a single option."""
    from scipy.stats import norm
    if T <= 0:
        return 0.0, 0.0, 0.0, 0.0
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T) + 1e-10)
    d2 = d1 - sigma * np.sqrt(T)
    phi = norm.pdf(d1)
    disc = np.exp(-r * T)

    mult = 1 if side == OptionSide.CALL else -1
    delta = float(disc * mult * norm.cdf(mult * d1))
    gamma = float(disc * phi / (F * sigma * np.sqrt(T) + 1e-10))
    theta = float(-disc * F * phi * sigma / (2 * np.sqrt(T)) - r * K * disc * norm.cdf(d2) * (1 if side == OptionSide.CALL else -1))  # noqa: E501
    vega = float(disc * F * phi * np.sqrt(T))
    return delta, gamma, theta, vega


# ── Strategy Builder ─────────────────────────────────────────────────────


class OptionStrategy:
    """Build and evaluate multi-leg option strategies.

    Args:
        spot: Current underlying price
        rate: Risk-free rate (decimal)
        T: Time to expiry (years) — default for single-expiry strategies
    """

    def __init__(self, spot: float, rate: float = 0.05, T: float = 1.0):
        self.spot = spot
        self.rate = rate
        self.T = T
        self.legs: list[Leg] = []

    def add_leg(self, leg: Leg) -> OptionStrategy:
        self.legs.append(leg)
        return self

    # ── Named Strategies ──────────────────────────────────────────────

    def straddle(self, strike: float, T: float | None = None) -> StrategyResult:
        """Long Straddle: buy call + buy put at same strike."""
        t = T or self.T
        return self._evaluate("Long Straddle", [
            Leg(OptionSide.CALL, PositionType.LONG, strike, t),
            Leg(OptionSide.PUT, PositionType.LONG, strike, t),
        ])

    def strangle(self, call_strike: float, put_strike: float, T: float | None = None) -> StrategyResult:
        """Long Strangle: OTM call + OTM put."""
        t = T or self.T
        return self._evaluate("Long Strangle", [
            Leg(OptionSide.CALL, PositionType.LONG, call_strike, t),
            Leg(OptionSide.PUT, PositionType.LONG, put_strike, t),
        ])

    def bull_call_spread(self, lower: float, upper: float, T: float | None = None) -> StrategyResult:
        """Bull Call Spread: long lower call + short upper call."""
        t = T or self.T
        return self._evaluate("Bull Call Spread", [
            Leg(OptionSide.CALL, PositionType.LONG, lower, t),
            Leg(OptionSide.CALL, PositionType.SHORT, upper, t),
        ])

    def bear_put_spread(self, lower: float, upper: float, T: float | None = None) -> StrategyResult:
        """Bear Put Spread: long higher put + short lower put."""
        t = T or self.T
        return self._evaluate("Bear Put Spread", [
            Leg(OptionSide.PUT, PositionType.LONG, upper, t),
            Leg(OptionSide.PUT, PositionType.SHORT, lower, t),
        ])

    def butterfly(self, lower: float, middle: float, upper: float, T: float | None = None) -> StrategyResult:
        """Long Butterfly: buy lower call, sell 2x middle calls, buy upper call."""
        t = T or self.T
        return self._evaluate("Butterfly", [
            Leg(OptionSide.CALL, PositionType.LONG, lower, t),
            Leg(OptionSide.CALL, PositionType.SHORT, middle, t, quantity=2),
            Leg(OptionSide.CALL, PositionType.LONG, upper, t),
        ])

    def iron_condor(
        self, put_lower: float, put_upper: float, call_lower: float, call_upper: float,
        T: float | None = None,
    ) -> StrategyResult:
        """Iron Condor: sell put spread + sell call spread."""
        t = T or self.T
        return self._evaluate("Iron Condor", [
            Leg(OptionSide.PUT, PositionType.LONG, put_lower, t),
            Leg(OptionSide.PUT, PositionType.SHORT, put_upper, t),
            Leg(OptionSide.CALL, PositionType.SHORT, call_lower, t),
            Leg(OptionSide.CALL, PositionType.LONG, call_upper, t),
        ])

    def covered_call(self, strike: float, T: float | None = None) -> StrategyResult:
        """Covered Call: long stock + short call."""
        t = T or self.T
        # Add stock position as synthetic leg
        return self._evaluate("Covered Call", [
            Leg(OptionSide.CALL, PositionType.SHORT, strike, t),
        ])

    # ── Evaluation ────────────────────────────────────────────────────

    def _evaluate(self, name: str, legs: list[Leg], sigma: float = 0.3) -> StrategyResult:
        """Evaluate strategy — compute premiums, greeks, max P/L, break-evens."""
        evaluated = []
        net_premium = 0.0

        for leg in legs:
            F = self.spot  # ponytail: assuming no div
            p = _bs_price(F, leg.strike, leg.expiration, sigma, self.rate, leg.side)
            d, g, t, v = _bs_greeks(F, leg.strike, leg.expiration, sigma, self.rate, leg.side)

            q = leg.quantity * (1 if leg.position == PositionType.LONG else -1)
            premium = p * q
            net_premium += premium

            evaluated.append(Leg(
                side=leg.side, position=leg.position, strike=leg.strike,
                expiration=leg.expiration, quantity=leg.quantity,
                premium=premium, delta=d * q, gamma=g * q, theta=t * q, vega=v * q,
            ))

        # Aggregate greeks
        total_delta = sum(lg.delta for lg in evaluated)
        total_gamma = sum(lg.gamma for lg in evaluated)
        total_theta = sum(lg.theta for lg in evaluated)
        total_vega = sum(lg.vega for lg in evaluated)

        # Max profit/loss and break-even at expiry
        sorted(set(lg.strike for lg in legs))
        price_range = np.linspace(self.spot * 0.5, self.spot * 1.5, 200)
        payoffs = []

        for sp in price_range:
            payoff = 0.0
            for leg in evaluated:
                q = leg.quantity * (1 if leg.position == PositionType.LONG else -1)
                if leg.side == OptionSide.CALL:
                    iv = max(0, sp - leg.strike)
                else:
                    iv = max(0, leg.strike - sp)
                payoff += iv * q
            payoff -= net_premium  # subtract premium paid
            payoffs.append(payoff)

        payoffs = np.array(payoffs)
        max_profit = float(np.max(payoffs))
        max_loss = float(np.min(payoffs))

        # Break-evens: sign changes
        be = []
        for i in range(len(price_range) - 1):
            if payoffs[i] * payoffs[i + 1] <= 0:
                try:
                    be.append(float(np.interp(0, [payoffs[i], payoffs[i + 1]], [price_range[i], price_range[i + 1]])))
                except Exception:
                    pass
        # Filter unique
        be = list(set(round(b, 4) for b in be))

        # Payoff table (subset for display)
        n_points = min(20, len(price_range))
        idx = np.linspace(0, len(price_range) - 1, n_points, dtype=int)
        payoff_table = [(float(price_range[i]), float(payoffs[i])) for i in idx]

        return StrategyResult(
            name=name, legs=evaluated, net_premium=net_premium,
            max_profit=max_profit, max_loss=max_loss,
            break_even=be, total_delta=total_delta, total_gamma=total_gamma,
            total_theta=total_theta, total_vega=total_vega,
            payoff_at_expiry=payoff_table,
        )


def analyze_strategy(
    name: str,
    spot: float,
    legs: list[dict],
    rate: float = 0.05,
    sigma: float = 0.3,
) -> StrategyResult:
    """Quick strategy analysis from dict legs.

    Each leg: {"side": "call"/"put", "position": "long"/"short",
               "strike": float, "expiration": float (years), "quantity": int}
    """
    builder = OptionStrategy(spot, rate)
    for leg_dict in legs:
        leg = Leg(
            side=OptionSide(leg_dict["side"]),
            position=PositionType(leg_dict["position"]),
            strike=leg_dict["strike"],
            expiration=leg_dict.get("expiration", 1.0),
            quantity=leg_dict.get("quantity", 1),
        )
        builder.add_leg(leg)
    # Compute strategy name from legs
    all_sides = "+".join(f"{lg['position']}_{lg['side']}" for lg in legs)
    return builder._evaluate(f"{name or all_sides}", builder.legs, sigma)
