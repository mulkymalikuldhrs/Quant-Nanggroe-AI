"""Backtest adapter for YAML strategy system.

Converts StrategyConfig objects into backtest-compatible signal generators
that can be used with the BacktestEngine. Wires entry/exit rules to
indicator computations and supports multi-timeframe strategies.

Supported indicators:
- RSI (Relative Strength Index)
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands (with z-score / lower band deviation)
- ATR (Average True Range)
- ADX (Average Directional Index)
- Stochastic Oscillator
- Volume (raw and ratio to moving average)
- Price
- Factor (custom factor scores)

Usage::

    from quant_nanggroe.engine.strategy.backtest_adapter import StrategyBacktestAdapter

    adapter = StrategyBacktestAdapter(config)
    signals = adapter.generate_signals(price_df)
    result = backtest_engine.run(price_df, signals)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.schema import (
    EntryRule,
    ExitRule,
    OperatorType,
    RiskRules,
    StrategyConfig,
)
from quant_nanggroe.engine.strategy.parser import strategy_to_code

logger = logging.getLogger(__name__)


class StrategyBacktestAdapter:
    """Adapts a StrategyConfig for use with the BacktestEngine.

    Converts declarative strategy rules (entry/exit conditions) into
    pandas-based signal computations that produce position weight
    DataFrames compatible with the BacktestEngine.run() method.

    The adapter supports:
    - Indicator computation (RSI, SMA, EMA, MACD, Bollinger, ADX, etc.)
    - Volume ratio computation (volume / rolling average volume)
    - Multi-timeframe strategies (rules on different timeframes)
    - Position sizing from risk rules
    - Trailing stop and take profit exits
    - Price comparison indicators (price vs SMA, EMA crossover)

    Example:
        >>> adapter = StrategyBacktestAdapter(config)
        >>> signals_df = adapter.generate_signals(price_df)
        >>> # signals_df is a DataFrame of position weights (-1 to 1)
        >>> from quant_nanggroe.engine.backtest.engine import BacktestEngine
        >>> engine = BacktestEngine()
        >>> result = engine.run(prices_df, signals_df)
    """

    def __init__(self, config: StrategyConfig) -> None:
        """Initialize the backtest adapter.

        Args:
            config: StrategyConfig defining the strategy rules.
        """
        self._config = config
        self._indicator_cache: Dict[str, pd.Series] = {}

    @property
    def config(self) -> StrategyConfig:
        """The strategy configuration."""
        return self._config

    @property
    def universe(self) -> List[str]:
        """Trading universe symbols."""
        return self._config.universe.symbols

    @property
    def risk_rules(self) -> RiskRules:
        """Risk rules from the strategy config."""
        return self._config.risk_rules

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate position weight signals for the backtest engine.

        Computes entry and exit signals for each symbol in the universe,
        then applies a state machine to determine position weights.
        Uses close prices and estimated OHLCV when full data is unavailable.

        Args:
            df: Price data DataFrame with DatetimeIndex and columns
                for each symbol. Values are close prices. Can also
                contain MultiIndex columns with OHLCV data.

        Returns:
            DataFrame with same index/columns as input, values are
            position weights: -1.0 (short), 0.0 (flat), or positive
            for long position size (capped by max_position_pct).
        """
        symbols = self._config.universe.symbols
        available_symbols = [s for s in symbols if s in df.columns]

        if not available_symbols:
            # If no symbols match, use all available columns
            available_symbols = list(df.columns)

        result = pd.DataFrame(0.0, index=df.index, columns=available_symbols)

        for symbol in available_symbols:
            if symbol not in df.columns:
                continue

            # Build OHLCV-like data for indicator computation
            price_series = df[symbol]

            # Estimate OHLCV from close prices when full data not available
            symbol_df = pd.DataFrame({
                "close": price_series,
                "open": price_series.shift(1).fillna(price_series),
                "high": price_series.rolling(2, min_periods=1).max().fillna(price_series),
                "low": price_series.rolling(2, min_periods=1).min().fillna(price_series),
                "volume": self._estimate_volume(price_series),
            }, index=df.index)

            # Compute entry and exit signals
            entry_signal = self._compute_entry_signals(symbol_df)
            exit_signal = self._compute_exit_signals(symbol_df)

            # Apply state machine with price data for trailing stop/TP
            position = self._apply_state_machine(
                entry_signal, exit_signal, symbol_df
            )

            # Apply position sizing
            max_weight = self._config.risk_rules.max_position_pct / 100.0
            position = position * max_weight

            result[symbol] = position.values

        return result

    def generate_signals_with_prices(
        self,
        ohlcv_dict: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Generate signals with full OHLCV data for trailing stop/take profit.

        This is the full-featured signal generation that uses real volume
        data and proper OHLCV for indicator computation.

        Args:
            ohlcv_dict: Dict mapping symbol to OHLCV DataFrame with columns:
                        open, high, low, close, volume.

        Returns:
            DataFrame of position weights with DatetimeIndex and symbol columns.
        """
        symbols = self._config.universe.symbols
        available_symbols = [s for s in symbols if s in ohlcv_dict]

        if not available_symbols:
            available_symbols = list(ohlcv_dict.keys())[:1]  # At least one

        # Determine common index
        all_indices = [ohlcv_dict[s].index for s in available_symbols]
        if all_indices:
            common_index = all_indices[0]
            for idx in all_indices[1:]:
                common_index = common_index.intersection(idx)
        else:
            common_index = pd.DatetimeIndex([])

        result = pd.DataFrame(0.0, index=common_index, columns=available_symbols)

        for symbol in available_symbols:
            symbol_df = ohlcv_dict[symbol].reindex(common_index)

            # Compute entry and exit signals
            entry_signal = self._compute_entry_signals(symbol_df)
            exit_signal = self._compute_exit_signals(symbol_df)

            # Full state machine with trailing stop/take profit
            position = self._apply_state_machine_full(
                entry_signal, exit_signal, symbol_df
            )

            # Apply position sizing
            max_weight = self._config.risk_rules.max_position_pct / 100.0
            position = position * max_weight

            result[symbol] = position.values

        return result

    def _compute_entry_signals(self, df: pd.DataFrame) -> pd.Series:
        """Compute entry signals from all entry rules.

        All entry rules are evaluated with AND logic: a signal is generated
        only when ALL rules are satisfied.

        Args:
            df: OHLCV-like DataFrame for a single symbol.

        Returns:
            Boolean Series: True when all entry conditions are met.
        """
        if not self._config.entry_rules:
            return pd.Series(False, index=df.index)

        signals = pd.Series(True, index=df.index)

        for rule in self._config.entry_rules:
            indicator_values = self._compute_indicator(rule, df)
            rule_signal = self._evaluate_rule(
                indicator_values, rule.operator, rule.value
            )
            signals = signals & rule_signal

        return signals

    def _compute_exit_signals(self, df: pd.DataFrame) -> pd.Series:
        """Compute exit signals from all exit rules.

        Exit rules are evaluated with OR logic: a signal is generated
        when ANY exit condition is triggered.

        Args:
            df: OHLCV-like DataFrame for a single symbol.

        Returns:
            Boolean Series: True when any exit condition is triggered.
        """
        if not self._config.exit_rules:
            return pd.Series(False, index=df.index)

        signals = pd.Series(False, index=df.index)

        for rule in self._config.exit_rules:
            if rule.trailing_stop_pct is not None:
                # Trailing stop is handled in the state machine
                continue

            if rule.take_profit_pct is not None:
                # Take profit is handled in the state machine
                continue

            if rule.indicator and rule.operator:
                indicator_values = self._compute_indicator(rule, df)
                rule_signal = self._evaluate_rule(
                    indicator_values, rule.operator, rule.value
                )
                signals = signals | rule_signal

        return signals

    def _compute_indicator(
        self, rule: EntryRule | ExitRule, df: pd.DataFrame
    ) -> pd.Series:
        """Compute indicator values for a rule.

        Supports a wide range of indicators and comparison modes.

        Args:
            rule: Entry or exit rule with indicator specification.
            df: OHLCV-like DataFrame.

        Returns:
            Series of indicator values.
        """
        indicator = rule.indicator.lower()
        params = rule.params if hasattr(rule, "params") else {}
        period = int(params.get("period", 14))

        # Check cache
        cache_key = f"{indicator}_{period}_{rule.timeframe}_{tuple(sorted(params.items()))}"
        if cache_key in self._indicator_cache:
            return self._indicator_cache[cache_key]

        if indicator in ("sma", "simple_moving_average"):
            compare = params.get("compare", "")
            if compare == "price_above_sma":
                # Return price - SMA (positive when price > SMA)
                sma = df["close"].rolling(window=period).mean()
                values = df["close"] - sma
            else:
                values = df["close"].rolling(window=period).mean()

        elif indicator in ("ema", "exponential_moving_average"):
            compare_ema = params.get("compare_ema", None)
            if compare_ema:
                # EMA crossover: return EMA(short) - EMA(long)
                other_period = int(compare_ema)
                fast_ema = df["close"].ewm(span=period, adjust=False).mean()
                slow_ema = df["close"].ewm(span=other_period, adjust=False).mean()
                values = fast_ema - slow_ema
            else:
                values = df["close"].ewm(span=period, adjust=False).mean()

        elif indicator == "rsi":
            values = self._compute_rsi(df["close"], period)

        elif indicator == "macd":
            fast = int(params.get("fast_period", 12))
            slow = int(params.get("slow_period", 26))
            signal_period = int(params.get("signal_period", 9))
            fast_ema = df["close"].ewm(span=fast, adjust=False).mean()
            slow_ema = df["close"].ewm(span=slow, adjust=False).mean()
            macd_line = fast_ema - slow_ema
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            # Return MACD - signal (positive when MACD above signal)
            values = macd_line - signal_line

        elif indicator == "volume":
            # Volume ratio: current volume / rolling average volume
            vol_period = int(params.get("period", 20))
            if "volume" in df.columns and df["volume"].sum() > 0:
                vol = df["volume"].astype(float)
                avg_vol = vol.rolling(window=vol_period, min_periods=1).mean()
                values = vol / avg_vol.replace(0, 1)
            else:
                # No volume data available — return series of 1.0 (neutral)
                # This means volume-based rules will not trigger entry/exit
                values = pd.Series(1.0, index=df.index)
                logger.debug("No volume data available, volume indicator returns 1.0 (neutral)")

        elif indicator == "price":
            compare = params.get("compare", "")
            sma_period = params.get("sma_period", None)
            if compare == "sma" and sma_period:
                # Price vs SMA: return price - SMA (positive when price > SMA)
                sma = df["close"].rolling(window=int(sma_period)).mean()
                values = df["close"] - sma
            else:
                values = df["close"]

        elif indicator == "atr":
            values = self._compute_atr(df, period)

        elif indicator == "adx":
            values = self._compute_adx(df, period)

        elif indicator == "bollinger":
            bb_period = int(params.get("period", 20))
            std_dev = float(params.get("std_dev", 2.0))
            bb_sma = df["close"].rolling(window=bb_period).mean()
            bb_std = df["close"].rolling(window=bb_period).std()
            # Return z-score: (price - SMA) / std
            # Negative values mean price is below lower band
            values = (df["close"] - bb_sma) / (bb_std + 1e-10)
            # z-score of -2 means price is at lower Bollinger Band

        elif indicator == "stochastic":
            k_period = int(params.get("k_period", 14))
            low_min = df["low"].rolling(window=k_period).min()
            high_max = df["high"].rolling(window=k_period).max()
            values = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-10)

        elif indicator == "factor":
            # Factor-based indicator: compute custom factor scores
            factor_type = params.get("factor_type", "")
            lookback = int(params.get("lookback", 21))
            values = self._compute_factor(df, factor_type, lookback)

        else:
            # Try to use as a column name or return close
            if indicator in df.columns:
                values = df[indicator]
            else:
                logger.warning(f"Unknown indicator '{indicator}', using close price")
                values = df["close"]

        self._indicator_cache[cache_key] = values
        return values

    @staticmethod
    def _compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Compute Relative Strength Index.

        Uses Wilder's smoothing method for proper RSI calculation.

        Args:
            prices: Price series.
            period: RSI period.

        Returns:
            RSI values (0-100).
        """
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute Average True Range.

        Args:
            df: OHLCV DataFrame.
            period: ATR period.

        Returns:
            ATR values.
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    @staticmethod
    def _compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute Average Directional Index (ADX).

        Measures trend strength regardless of direction.
        ADX > 25 indicates a strong trend.

        Args:
            df: OHLCV DataFrame.
            period: ADX period.

        Returns:
            ADX values.
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = pd.Series(0.0, index=df.index)
        minus_dm = pd.Series(0.0, index=df.index)

        # +DM: up_move > down_move AND up_move > 0
        plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move
        # -DM: down_move > up_move AND down_move > 0
        minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move

        # Smoothed values
        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / (atr + 1e-10)
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / (atr + 1e-10)

        # DX and ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=period, adjust=False).mean()

        return adx

    @staticmethod
    def _compute_factor(
        df: pd.DataFrame,
        factor_type: str,
        lookback: int = 21,
    ) -> pd.Series:
        """Compute custom factor scores for factor-based strategies.

        Args:
            df: OHLCV DataFrame.
            factor_type: Type of factor to compute.
            lookback: Lookback period for factor computation.

        Returns:
            Factor score Series (typically -1 to 1).
        """
        close = df["close"]

        if factor_type == "momentum_score":
            # Price momentum: normalized return over lookback
            ret = close.pct_change(lookback)
            # Normalize to roughly -1 to 1 range using rolling z-score
            rolling_mean = ret.rolling(window=lookback * 2, min_periods=lookback).mean()
            rolling_std = ret.rolling(window=lookback * 2, min_periods=lookback).std()
            values = (ret - rolling_mean) / (rolling_std + 1e-10)
            # Clip to [-3, 3] and rescale to [-1, 1]
            values = values.clip(-3, 3) / 3.0

        elif factor_type == "value_score":
            # Proxy: inverse of price relative to moving average (cheaper = higher value score)
            sma = close.rolling(window=lookback).mean()
            values = -(close - sma) / (sma + 1e-10)
            # Normalize
            rolling_std = values.rolling(window=lookback * 2, min_periods=lookback).std()
            values = values / (rolling_std + 1e-10)
            values = values.clip(-3, 3) / 3.0

        elif factor_type == "quality_score":
            # Proxy: smoothness of returns (lower volatility = higher quality)
            ret = close.pct_change()
            vol = ret.rolling(window=lookback).std()
            # Inverse volatility scaled
            inv_vol = 1.0 / (vol + 1e-10)
            rolling_mean = inv_vol.rolling(window=lookback * 2, min_periods=lookback).mean()
            rolling_std = inv_vol.rolling(window=lookback * 2, min_periods=lookback).std()
            values = (inv_vol - rolling_mean) / (rolling_std + 1e-10)
            values = values.clip(-3, 3) / 3.0

        else:
            # Unknown factor type: return neutral (0)
            logger.warning(f"Unknown factor type '{factor_type}', returning 0.0")
            values = pd.Series(0.0, index=df.index)

        return values

    @staticmethod
    def _estimate_volume(price_series: pd.Series) -> pd.Series:
        """Estimate volume from price data when actual volume is unavailable.

        Uses a proxy based on dollar volume (price * 1000) to allow
        volume ratio calculations. This is a rough estimate — real
        volume data should be used via generate_signals_with_prices().

        Args:
            price_series: Close price series.

        Returns:
            Estimated volume Series.
        """
        # Simple proxy: use absolute price change * price as volume estimate
        # This gives a non-zero series that correlates with actual trading activity
        price_change = price_series.diff().abs()
        est_volume = price_change * price_series * 1000
        # Fill initial NaN and zero values
        est_volume = est_volume.fillna(price_series.mean() * 100)
        est_volume = est_volume.replace(0, price_series.mean() * 100)
        return est_volume

    @staticmethod
    def _evaluate_rule(
        values: pd.Series,
        operator: OperatorType,
        threshold: float,
    ) -> pd.Series:
        """Evaluate a comparison rule against indicator values.

        Args:
            values: Indicator values.
            operator: Comparison operator.
            threshold: Threshold value.

        Returns:
            Boolean Series where the rule is satisfied.
        """
        if operator == OperatorType.GT:
            return values > threshold
        elif operator == OperatorType.GTE:
            return values >= threshold
        elif operator == OperatorType.LT:
            return values < threshold
        elif operator == OperatorType.LTE:
            return values <= threshold
        elif operator == OperatorType.EQ:
            return (values - threshold).abs() < 1e-10
        elif operator == OperatorType.NEQ:
            return (values - threshold).abs() >= 1e-10
        elif operator == OperatorType.CROSS_ABOVE:
            return (values.shift(1) < threshold) & (values >= threshold)
        elif operator == OperatorType.CROSS_BELOW:
            return (values.shift(1) > threshold) & (values <= threshold)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return pd.Series(False, index=values.index)

    def _apply_state_machine(
        self,
        entry: pd.Series,
        exit_signal: pd.Series,
        df: pd.DataFrame,
    ) -> pd.Series:
        """Apply a position state machine to entry/exit signals.

        Implements trailing stop, take profit, and stop loss logic
        in addition to indicator-based exit signals.

        Args:
            entry: Boolean Series of entry signals.
            exit_signal: Boolean Series of indicator-based exit signals.
            df: OHLCV DataFrame with close prices.

        Returns:
            Series of position weights (0.0 or 1.0).
        """
        position = pd.Series(0.0, index=entry.index)
        in_position = False
        entry_price: Optional[float] = None
        highest_since_entry: Optional[float] = None

        # Extract exit parameters
        trailing_stop_pct = None
        take_profit_pct = None
        for rule in self._config.exit_rules:
            if rule.trailing_stop_pct is not None:
                trailing_stop_pct = rule.trailing_stop_pct / 100.0
            if rule.take_profit_pct is not None:
                take_profit_pct = rule.take_profit_pct / 100.0

        stop_loss_pct = self._config.risk_rules.stop_loss_pct / 100.0

        for i in range(len(df)):
            close_price = float(df["close"].iloc[i])

            if not in_position and bool(entry.iloc[i]):
                position.iloc[i] = 1.0
                in_position = True
                entry_price = close_price
                highest_since_entry = close_price
            elif in_position:
                should_exit = bool(exit_signal.iloc[i])

                # Update highest price since entry
                if highest_since_entry is not None:
                    highest_since_entry = max(highest_since_entry, close_price)

                # Check trailing stop (from highest point)
                if trailing_stop_pct is not None and highest_since_entry is not None:
                    trailing_stop_price = highest_since_entry * (1 - trailing_stop_pct)
                    if close_price <= trailing_stop_price:
                        should_exit = True

                # Check take profit
                if take_profit_pct is not None and entry_price is not None:
                    tp_price = entry_price * (1 + take_profit_pct)
                    if close_price >= tp_price:
                        should_exit = True

                # Check stop loss from risk rules
                if entry_price is not None and close_price <= entry_price * (1 - stop_loss_pct):
                    should_exit = True

                if should_exit:
                    position.iloc[i] = 0.0
                    in_position = False
                    entry_price = None
                    highest_since_entry = None
                else:
                    position.iloc[i] = 1.0
            else:
                position.iloc[i] = 0.0

        return position

    def _apply_state_machine_full(
        self,
        entry: pd.Series,
        exit_signal: pd.Series,
        df: pd.DataFrame,
    ) -> pd.Series:
        """Full state machine with trailing stop and take profit.

        This is identical to _apply_state_machine but provided for
        backward compatibility with generate_signals_with_prices().

        Args:
            entry: Boolean entry signals.
            exit_signal: Boolean indicator-based exit signals.
            df: OHLCV DataFrame with close prices.

        Returns:
            Position weight Series.
        """
        return self._apply_state_machine(entry, exit_signal, df)

    def to_backtest_config(self) -> Dict[str, Any]:
        """Convert strategy config to BacktestConfig-compatible parameters.

        Returns:
            Dict of BacktestConfig parameters derived from the strategy.
        """
        return {
            "initial_capital": 1_000_000.0,
            "commission_rate": 0.001,
            "slippage_bps": 5.0,
            "max_positions": max(len(self._config.universe.symbols), 1),
            "risk_per_trade": self._config.risk_rules.stop_loss_pct / 100.0,
            "short_enabled": False,
        }

    def get_generated_code(self) -> str:
        """Get the generated Python code for this strategy.

        Returns:
            Python code string implementing the strategy.
        """
        return strategy_to_code(self._config)

    def clear_cache(self) -> None:
        """Clear the indicator computation cache."""
        self._indicator_cache.clear()
