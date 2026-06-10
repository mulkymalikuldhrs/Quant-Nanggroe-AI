"""Technical factors — RSI, MACD, Bollinger Bands as alpha factors."""

from __future__ import annotations

from quant_nanggroe_ai.engine.math_lib import MathEngine


def compute_rsi_factor(closes: list[float], period: int = 14) -> float | None:
    """Compute latest RSI value as a factor."""
    rsi_values = MathEngine.rsi(closes, period)
    return rsi_values[-1] if rsi_values else None


def compute_macd_factor(closes: list[float]) -> dict[str, float | None]:
    """Compute latest MACD values as factors."""
    macd_result = MathEngine.macd(closes)
    return {
        "macd_line": macd_result["macd"][-1],
        "signal_line": macd_result["signal"][-1],
        "histogram": macd_result["histogram"][-1],
    }


def compute_bollinger_factor(closes: list[float], period: int = 20) -> dict[str, float | None]:
    """Compute latest Bollinger Band values as factors."""
    bb = MathEngine.bollinger_bands(closes, period)
    return {
        "upper": bb["upper"][-1],
        "middle": bb["middle"][-1],
        "lower": bb["lower"][-1],
        "percent_b": bb["percent_b"][-1],
    }
