"""Volatility Arbitrage Strategy.

Implements production-quality volatility arbitrage using:
1. Realized vs implied volatility spread trading
2. GARCH(1,1) volatility forecasting
3. Variance risk premium estimation
4. Dynamic delta hedging simulation

Academic References:
    - Bollerslev, T. (1986). "Generalized Autoregressive Conditional Heteroskedasticity."
      Journal of Econometrics, 31(3), 307-327.
    - Carr, P. & Wu, L. (2009). "Variance Risk Premiums." Review of Financial Studies,
      22(3), 1311-1341.
    - Demeterfi, K., Derman, E., Kamal, M., & Zou, J. (1999). "More Than You Ever
      Wanted to Know About Volatility Swaps." Goldman Sachs Quantitative Strategies
      Research Notes.
    - Hull, J.C. (2018). Options, Futures, and Other Derivatives. 10th ed. Pearson.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class GARCH11:
    """GARCH(1,1) volatility model.

    sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2

    Parameters are estimated via maximum likelihood estimation.

    Reference:
        Bollerslev, T. (1986). Journal of Econometrics, 31(3), 307-327.
    """

    def __init__(self):
        self.omega: float = 0.0
        self.alpha: float = 0.0
        self.beta: float = 0.0
        self.long_run_var: float = 0.0
        self._fitted: bool = False

    def fit(self, returns: np.ndarray) -> "GARCH11":
        """Fit GARCH(1,1) parameters via MLE.

        Args:
            returns: Array of log returns.

        Returns:
            Self with fitted parameters.
        """
        if len(returns) < 20:
            self._fitted = False
            return self

        T = len(returns)
        var = np.var(returns)

        # Initial parameter guesses
        initial_params = [var * 0.1, 0.1, 0.85]

        # Constraints: omega > 0, alpha >= 0, beta >= 0, alpha + beta < 1
        bounds = [(1e-8, None), (1e-8, 0.999), (1e-8, 0.999)]

        def neg_log_likelihood(params: List[float]) -> float:
            omega, alpha, beta = params
            if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1:
                return 1e10

            sigma2 = np.zeros(T)
            sigma2[0] = var

            for t in range(1, T):
                sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]
                if sigma2[t] <= 0:
                    return 1e10

            # Gaussian log-likelihood
            ll = -0.5 * np.sum(np.log(2 * np.pi * sigma2) + returns ** 2 / sigma2)
            return -ll

        try:
            from scipy import optimize
            result = optimize.minimize(
                neg_log_likelihood,
                initial_params,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 500},
            )
            if result.success:
                self.omega, self.alpha, self.beta = result.x
                self.long_run_var = self.omega / (1 - self.alpha - self.beta + 1e-10)
                self._fitted = True
            else:
                # Fallback: use simple variance
                self.omega = var * 0.05
                self.alpha = 0.1
                self.beta = 0.85
                self.long_run_var = var
                self._fitted = True
        except Exception:
            self.omega = var * 0.05
            self.alpha = 0.1
            self.beta = 0.85
            self.long_run_var = var
            self._fitted = True

        return self

    def forecast(self, returns: np.ndarray, horizon: int = 1) -> np.ndarray:
        """Forecast volatility over a given horizon.

        For GARCH(1,1), multi-step ahead forecast:
            sigma_{T+h}^2 = long_run_var + (alpha + beta)^h * (sigma_T^2 - long_run_var)

        Args:
            returns: Historical returns array.
            horizon: Number of steps ahead to forecast.

        Returns:
            Array of forecasted variances for each step.
        """
        if not self._fitted:
            return np.full(horizon, np.var(returns))

        T = len(returns)
        sigma2_last = self.omega + self.alpha * returns[-1] ** 2 + self.beta * np.var(returns)

        # Compute conditional variance for last observation
        sigma2 = np.var(returns)
        for t in range(max(0, T - 50), T):
            sigma2 = self.omega + self.alpha * returns[t - 1] ** 2 + self.beta * sigma2
        sigma2_last = sigma2

        forecasts = np.zeros(horizon)
        for h in range(horizon):
            if h == 0:
                forecasts[h] = sigma2_last
            else:
                forecasts[h] = (
                    self.long_run_var
                    + (self.alpha + self.beta) ** h * (sigma2_last - self.long_run_var)
                )

        return forecasts

    @property
    def half_life(self) -> float:
        """Half-life of volatility shocks.

        half_life = -ln(2) / ln(alpha + beta)
        """
        if not self._fitted:
            return np.inf
        persistence = self.alpha + self.beta
        if persistence >= 1 or persistence <= 0:
            return np.inf
        return -np.log(2) / np.log(persistence)


class VolatilityArbitrageStrategy(BaseStrategy):
    """Volatility arbitrage strategy.

    Trades the spread between realized and implied volatility:
    - When implied vol > forecasted realized vol: sell vol (short variance)
    - When implied vol < forecasted realized vol: buy vol (long variance)

    Uses GARCH(1,1) for realized vol forecasting and a proxy for implied vol.

    Parameters:
        lookback: Window for realized vol calculation (default 21).
        garch_horizon: GARCH forecast horizon in days (default 5).
        entry_spread: Min spread between IV and forecasted RV to enter (default 0.05).
        exit_spread: Spread level to exit (default 0.01).
        stop_loss_pct: Stop loss fraction (default 0.08).
        implied_vol_column: Column name for implied vol data (default "implied_vol").
        annualize_factor: Annualization factor (252 for daily, 365 for crypto) (default 252).
        symbol: Trading symbol (default "ASSET").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VolatilityArbitrage", params=params)
        self.lookback: int = self.params.get("lookback", 21)
        self.garch_horizon: int = self.params.get("garch_horizon", 5)
        self.entry_spread: float = self.params.get("entry_spread", 0.05)
        self.exit_spread: float = self.params.get("exit_spread", 0.01)
        self.stop_loss_pct: float = self.params.get("stop_loss_pct", 0.08)
        self.implied_vol_column: str = self.params.get("implied_vol_column", "implied_vol")
        self.annualize_factor: int = self.params.get("annualize_factor", 252)
        self.symbol: str = self.params.get("symbol", "ASSET")
        self._garch = GARCH11()

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return max(self.lookback + 30, 60)

    def compute_realized_vol(self, data: pd.DataFrame) -> float:
        """Compute realized volatility (annualized).

        Uses close-to-close returns for the lookback window.

        Args:
            data: DataFrame with 'close' column.

        Returns:
            Annualized realized volatility.
        """
        close = data["close"]
        returns = close.pct_change().dropna()
        if len(returns) < self.lookback:
            return 0.0

        recent_returns = returns.iloc[-self.lookback:]
        daily_var = float(np.var(recent_returns, ddof=1))
        annualized_vol = np.sqrt(daily_var * self.annualize_factor)
        return annualized_vol

    def compute_garch_forecast(self, data: pd.DataFrame) -> float:
        """Compute GARCH(1,1) volatility forecast.

        Fits a GARCH(1,1) model to returns and forecasts volatility
        over the specified horizon.

        Args:
            data: DataFrame with 'close' column.

        Returns:
            Annualized GARCH forecasted volatility.
        """
        close = data["close"]
        returns = close.pct_change().dropna()
        if len(returns) < 30:
            return self.compute_realized_vol(data)

        log_returns = np.log(1 + returns.values)
        self._garch.fit(log_returns)
        forecasts = self._garch.forecast(log_returns, horizon=self.garch_horizon)

        # Average forecast over horizon, annualized
        avg_forecast_var = float(np.mean(forecasts))
        return np.sqrt(avg_forecast_var * self.annualize_factor)

    def compute_implied_vol(self, data: pd.DataFrame) -> float:
        """Get implied volatility from data or estimate from options proxy.

        If 'implied_vol' column exists, uses it directly.
        Otherwise, estimates IV from recent price range (Parkinson estimator).

        Reference:
            Parkinson, M. (1980). "The Extreme Value Method for Estimating the
            Variance of the Rate of Return." Journal of Business, 53(1), 61-65.

        Args:
            data: DataFrame with OHLC data.

        Returns:
            Annualized implied volatility estimate.
        """
        if self.implied_vol_column in data.columns:
            iv = float(data[self.implied_vol_column].iloc[-1])
            if not np.isnan(iv) and iv > 0:
                return iv

        # Parkinson volatility estimator from high-low range
        if "high" in data.columns and "low" in data.columns:
            high = data["high"].iloc[-self.lookback:]
            low = data["low"].iloc[-self.lookback:]

            if len(high) > 5:
                # Parkinson estimator: sigma^2 = (1/(4*n*ln2)) * sum(ln(H_i/L_i))^2
                log_hl = np.log(high.values / low.values)
                parkinson_var = np.sum(log_hl ** 2) / (4 * len(log_hl) * np.log(2))
                return np.sqrt(parkinson_var * self.annualize_factor)

        # Fallback: use realized vol as proxy
        return self.compute_realized_vol(data)

    def compute_variance_risk_premium(
        self, implied_vol: float, realized_vol: float
    ) -> float:
        """Estimate variance risk premium.

        VRP = IV^2 - RV^2  (in variance terms)

        A positive VRP means the market is pricing in more risk than realized,
        creating a sell-vol opportunity.

        Reference:
            Carr & Wu (2009). Review of Financial Studies, 22(3), 1311-1341.

        Args:
            implied_vol: Annualized implied volatility.
            realized_vol: Annualized realized (or forecasted) volatility.

        Returns:
            Variance risk premium (positive = IV overpriced).
        """
        return implied_vol ** 2 - realized_vol ** 2

    def simulate_delta_hedge(
        self, data: pd.DataFrame, position: str, vol_entry: float
    ) -> Dict:
        """Simulate dynamic delta hedging P&L.

        Simplified delta hedging simulation for a variance swap position.
        Uses Black-Scholes delta approximation.

        Args:
            data: OHLCV DataFrame.
            position: 'short_vol' or 'long_vol'.
            vol_entry: Volatility at entry.

        Returns:
            Dict with hedging simulation results.
        """
        close = data["close"]
        returns = close.pct_change().dropna()

        if len(returns) < 5:
            return {"pnl": 0.0, "hedge_cost": 0.0}

        # Simplified P&L: daily gamma P&L minus hedge cost
        dt = 1.0 / self.annualize_factor
        pnl = 0.0
        hedge_cost = 0.0

        for i in range(1, len(returns)):
            realized_var = float(returns.iloc[i]) ** 2
            implied_var = (vol_entry ** 2) * dt

            if position == "short_vol":
                # Short vol: earn variance risk premium
                daily_pnl = implied_var - realized_var
            else:
                # Long vol: pay variance risk premium
                daily_pnl = realized_var - implied_var

            pnl += daily_pnl
            hedge_cost += abs(returns.iloc[i]) * 0.001  # Transaction cost proxy

        return {"pnl": float(pnl), "hedge_cost": float(hedge_cost)}

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate volatility arbitrage signal.

        Logic:
        1. Compute GARCH forecasted vol and implied vol
        2. Calculate the spread (IV - forecasted_RV)
        3. Enter short vol if spread > entry_threshold (IV is overpriced)
        4. Enter long vol if spread < -entry_threshold (IV is underpriced)
        5. Exit when spread narrows to exit_threshold

        Args:
            data: DataFrame with price data.

        Returns:
            Signal if vol spread condition met, None otherwise.
        """
        if not self.validate_data(data):
            return None

        # Compute volatilities
        realized_vol = self.compute_realized_vol(data)
        garch_vol = self.compute_garch_forecast(data)
        implied_vol = self.compute_implied_vol(data)

        if realized_vol <= 0 or garch_vol <= 0:
            return None

        # Use GARCH forecast as our best estimate of future realized vol
        vol_spread = implied_vol - garch_vol
        vrp = self.compute_variance_risk_premium(implied_vol, garch_vol)

        current_price = float(data["close"].iloc[-1])

        # --- Entry signals ---
        # Short vol: IV is too high relative to forecasted realized vol
        if vol_spread > self.entry_spread:
            confidence = min(vol_spread / (self.entry_spread + 0.01), 1.0)

            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.SELL,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(current_price * (1 + self.stop_loss_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Vol arb SELL VOL: IV={implied_vol:.4f} > GARCH={garch_vol:.4f}, "
                    f"spread={vol_spread:.4f}, VRP={vrp:.6f}"
                ),
                evidence={
                    "implied_vol": round(implied_vol, 6),
                    "realized_vol": round(realized_vol, 6),
                    "garch_vol": round(garch_vol, 6),
                    "vol_spread": round(vol_spread, 6),
                    "vrp": round(vrp, 8),
                    "garch_half_life": round(self._garch.half_life, 1),
                },
                factors=["volatility_arbitrage", "garch", "variance_risk_premium"],
            )

        # Long vol: IV is too low relative to forecasted realized vol
        if vol_spread < -self.entry_spread:
            confidence = min(abs(vol_spread) / (self.entry_spread + 0.01), 1.0)

            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(current_price * (1 - self.stop_loss_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Vol arb BUY VOL: IV={implied_vol:.4f} < GARCH={garch_vol:.4f}, "
                    f"spread={vol_spread:.4f}, VRP={vrp:.6f}"
                ),
                evidence={
                    "implied_vol": round(implied_vol, 6),
                    "realized_vol": round(realized_vol, 6),
                    "garch_vol": round(garch_vol, 6),
                    "vol_spread": round(vol_spread, 6),
                    "vrp": round(vrp, 8),
                    "garch_half_life": round(self._garch.half_life, 1),
                },
                factors=["volatility_arbitrage", "garch", "variance_risk_premium"],
            )

        # --- Exit signals ---
        if abs(vol_spread) < self.exit_spread:
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.EXIT_ALL,
                confidence=0.6,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Vol arb EXIT: spread={vol_spread:.4f} narrowed below {self.exit_spread}",
                evidence={
                    "vol_spread": round(vol_spread, 6),
                    "implied_vol": round(implied_vol, 6),
                    "garch_vol": round(garch_vol, 6),
                },
                factors=["volatility_arbitrage"],
            )

        return None
