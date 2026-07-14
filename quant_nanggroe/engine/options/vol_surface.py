"""
Volatility Surface & SABR Model
=================================
Implementasi SABR (Stochastic Alpha Beta Rho) vol smile model
untuk interest rates & equity options.

Referensi: pysabr (ynouri/pysabr), vollib, optlib.

SABR: dF = σ * F^β * dW1, dσ = α * σ * dW2, dW1 * dW2 = ρ * dt
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

logger = logging.getLogger(__name__)


# ── SABR Model ─────────────────────────────────────────────────────────────


class SABRModel:
    """SABR stochastic volatility model for implied volatility smiles.

    Parameter set (α, β, ρ, ν):
        α — initial volatility (vol of vol base)
        β — shape parameter (0 = stochastic normal, 1 = stochastic lognormal)
        ρ — correlation between forward and vol (skew)
        ν — vol of vol (smile curvature)
    """

    def __init__(
        self,
        alpha: float = 0.05,
        beta: float = 0.7,
        rho: float = 0.0,
        nu: float = 0.4,
    ):
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.nu = nu

    def implied_vol(
        self,
        forward: float,
        strike: float,
        T: float,
    ) -> float:
        """Compute SABR implied volatility for a given strike and expiry.

        Uses Hagan's 2002 asymptotic expansion formula.
        """
        K = strike
        F = forward
        if abs(F - K) < 1e-10:
            return self._atm_vol(F, T)

        logFK = np.log(F / K)
        z = self.nu / self.alpha * (F * K) ** ((1 - self.beta) / 2) * logFK
        x_z = np.log((np.sqrt(1 - 2 * self.rho * z + z**2) + z - self.rho) / (1 - self.rho))
        # ponytail: z/x_z → 1 as K→F (Hagan 2002). Do NOT clamp x_z — clamping a
        # negative log to a tiny positive collapses the denominator → OTM blowup.

        # Hagan 2002 lognormal expansion
        pre_fac = (F * K) ** ((1 - self.beta) / 2) * (
            1 + (1 - self.beta)**2 / 24 * logFK**2
            + (1 - self.beta)**4 / 1920 * logFK**4
        )
        correction = (
            (1 - self.beta)**2 / 24 * self.alpha**2 / (F * K)**(1 - self.beta)
            + 1 / 4 * self.rho * self.beta * self.nu * self.alpha / (F * K)**((1 - self.beta) / 2)
            + (2 - 3 * self.rho**2) / 24 * self.nu**2
        )
        denom = pre_fac * x_z
        if abs(denom) < 1e-12:
            return self._atm_vol(F, T)
        vol = self.alpha * (z / x_z) * (1 + correction * T) / denom
        # ponytail: Hagan expansion goes slightly negative for extreme strikes;
        # a negative IV is invalid for downstream pricing → floor at small positive.
        return float(max(vol, 1e-4))

    def _atm_vol(self, F: float, T: float) -> float:
        """ATM vol when F == K."""
        term = ((1 - self.beta)**2 / 24 * self.alpha**2 / F**(2 - 2 * self.beta)
                + 0.25 * self.rho * self.beta * self.nu * self.alpha / F**(1 - self.beta)
                + (2 - 3 * self.rho**2) / 24 * self.nu**2) * T
        return float(self.alpha / F**(1 - self.beta) * (1 + term))

    def calibrate(
        self,
        strikes: np.ndarray,
        vols: np.ndarray,
        forward: float,
        T: float,
    ) -> dict[str, float]:
        """Calibrate SABR parameters to market vol smile.

        Uses heuristic grid search — ponytail: no MLE, just moment matching.
        """
        # β fixed at 0.7 (common for equity/index options)
        # Calibrate ρ from skew, ν from smile curvature, α from ATM vol
        atm_idx = np.argmin(np.abs(strikes - forward))
        atm_vol = float(vols[atm_idx])
        self.alpha = atm_vol * forward**(1 - self.beta)

        # Compute skew (ρ) from 25-delta call/put
        if len(strikes) >= 3 and atm_idx > 0 and atm_idx < len(strikes) - 1:
            left_vol = float(vols[atm_idx - 1])
            right_vol = float(vols[atm_idx + 1])
            skew = (right_vol - left_vol) / (strikes[atm_idx + 1] - strikes[atm_idx - 1] + 1e-8)
            self.rho = max(-1.0, min(1.0, -skew * 10))  # heuristic

        # ν from smile curvature
        if len(strikes) >= 5:
            far_left = float(vols[max(0, atm_idx - 2)])
            far_right = float(vols[min(len(vols) - 1, atm_idx + 2)])
            curvature = (far_left + far_right) / 2 - atm_vol
            self.nu = max(0.01, min(2.0, curvature * 20))  # heuristic

        return {"alpha": self.alpha, "beta": self.beta, "rho": self.rho, "nu": self.nu}

    def compute_surface(
        self,
        forward: float,
        expiries: list[float],
        strikes: list[float],
    ) -> np.ndarray:
        """Compute full vol surface: (len(expiries), len(strikes)) matrix."""
        surface = np.zeros((len(expiries), len(strikes)))
        for i, T in enumerate(expiries):
            for j, K in enumerate(strikes):
                surface[i, j] = self.implied_vol(forward, K, T)
        return surface


# ── Vol Surface ────────────────────────────────────────────────────────────


@dataclass
class VolPoint:
    """Single point on vol surface."""
    strike: float
    expiry: float        # years
    implied_vol: float
    delta: float = 0.0
    vega: float = 0.0


@dataclass
class VolSurface:
    """Volatility surface — strikes x expiries matrix with interpolation."""

    strikes: np.ndarray
    expiries: np.ndarray
    vols: np.ndarray      # (len(expiries), len(strikes))

    def get_vol(self, strike: float, expiry: float) -> float:
        """Interpolate vol at arbitrary strike/expiry using bilinear interpolation."""
        # ponytail: simple bilinear, no spline
        if strike <= self.strikes[0]:
            return float(self._interp_expiry(expiry, 0))
        if strike >= self.strikes[-1]:
            return float(self._interp_expiry(expiry, -1))

        j = int(np.searchsorted(self.strikes, strike)) - 1
        j = max(0, min(j, len(self.strikes) - 2))

        # Interpolate expiries at each bounding strike
        v0 = self._interp_expiry(expiry, j)
        v1 = self._interp_expiry(expiry, j + 1)

        k_frac = (strike - self.strikes[j]) / (self.strikes[j + 1] - self.strikes[j] + 1e-8)
        return float(v0 + k_frac * (v1 - v0))

    def _interp_expiry(self, expiry: float, strike_idx: int) -> float:
        """Linear interpolate across expiries at a fixed strike."""
        vols_at_strike = self.vols[:, strike_idx]
        if expiry <= self.expiries[0]:
            return float(vols_at_strike[0])
        if expiry >= self.expiries[-1]:
            return float(vols_at_strike[-1])

        i = int(np.searchsorted(self.expiries, expiry)) - 1
        i = max(0, min(i, len(self.expiries) - 2))
        t_frac = (expiry - self.expiries[i]) / (self.expiries[i + 1] - self.expiries[i] + 1e-8)
        return float(vols_at_strike[i] + t_frac * (vols_at_strike[i + 1] - vols_at_strike[i]))


# ── Forward Price Calculator ───────────────────────────────────────────────


def forward_price(spot: float, rate: float, div_yield: float, T: float) -> float:
    """Compute forward price: F = S * exp((r - q) * T)."""
    return spot * np.exp((rate - div_yield) * T)


# ── Black Implied Vol (via vollib-style Brent) ────────────────────────────


def black_implied_vol(
    forward: float,
    strike: float,
    T: float,
    price: float,
    is_call: bool = True,
) -> float:
    """Invert Black-76 formula for implied vol using Brent's method.

    Referensi: vollib (vollib/py_vollib).
    """
    if price <= 0:
        return 0.0

    def _black_price(sigma: float) -> float:
        if sigma <= 0:
            return 0.0
        d1 = (np.log(forward / strike) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T) + 1e-10)
        d2 = d1 - sigma * np.sqrt(T)
        if is_call:
            return forward * norm.cdf(d1) - strike * norm.cdf(d2)
        else:
            return strike * norm.cdf(-d2) - forward * norm.cdf(-d1)

    try:
        iv = brentq(lambda s: _black_price(s) - price, 1e-6, 5.0, xtol=1e-8, maxiter=100)
        return float(iv)
    except (ValueError, RuntimeError):
        # Fallback: Newton-Raphson
        sigma = 0.3
        for _ in range(50):
            p = _black_price(sigma)
            diff = p - price
            if abs(diff) < 1e-8:
                break
            vega = forward * norm.pdf(_d1 := (np.log(forward / strike) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T) + 1e-10)) * np.sqrt(T)  # noqa: E501
            if abs(vega) < 1e-12:
                break
            sigma -= diff / vega
            sigma = max(sigma, 1e-6)
        return float(sigma)
