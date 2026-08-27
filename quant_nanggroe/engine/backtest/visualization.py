"""Backtest visualization — matplotlib-optional plotting with graceful CSV fallback.

Ported from SahamEngineAI's ``_plotting.py`` pattern. Generates:
  - Equity curve + drawdown subplots (matplotlib PNG)
  - Parameter heatmap (matplotlib PNG)
  - CSV/JSON data export when matplotlib is unavailable or chart rendering fails

Usage::

    from quant_nanggroe.engine.backtest.visualization import plot_results

    path = plot_results(metrics, equity_curve, trades, output_dir="backtest/output")
    # path -> "backtest/output/backtest_results.png"
    #       or "backtest/output/backtest_data.csv" if matplotlib absent

    path = plot_heatmaps(heatmap_data, output_dir="backtest/output")
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import matplotlib as _mpl

    _mpl.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    _HAS_MATPLOTLIB = True
except ImportError:
    _HAS_MATPLOTLIB = False


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def plot_results(
    metrics: dict[str, Any],
    equity_curve: pd.Series,
    trades: list[Any] | None = None,
    output_dir: str = "backtest/output",
    filename: str = "backtest_results.png",
    **kwargs: Any,
) -> str | None:
    """Generate equity + drawdown chart (matplotlib) or export CSV.

    Args:
        metrics: Performance metrics dict (from ``PerformanceMetrics.calculate``).
        equity_curve: Series of equity values indexed by timestamp.
        trades: Optional list of TradeRecord for scatter markers.
        output_dir: Directory for output file (created if absent).
        filename: PNG filename (ignored when falling back to CSV).

    Returns:
        Absolute path to the output file, or ``None`` on total failure.

    Falls back to CSV export when matplotlib is not installed or chart
    rendering raises an exception (graceful degradation).
    """
    out = _ensure_dir(output_dir)

    if not _HAS_MATPLOTLIB:
        return _export_csv(metrics, out / "backtest_data.csv")

    try:
        fig, axes = _render_equity_chart(metrics, equity_curve, trades, **kwargs)
        filepath = out / filename
        fig.savefig(str(filepath), dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Backtest chart saved to %s", filepath)
        return str(filepath)
    except Exception:
        logger.warning("Matplotlib chart failed; exporting CSV fallback.", exc_info=True)
        return _export_csv(metrics, out / "backtest_data_fallback.csv")


def plot_heatmaps(
    heatmap_data: list[list[float]] | None = None,
    output_dir: str = "backtest/output",
    filename: str = "heatmap.png",
    **kwargs: Any,
) -> str | None:
    """Generate parameter heatmap (matplotlib) or export JSON.

    Args:
        heatmap_data: 2-D list of values to colour (rows = param1, cols = param2).
        output_dir: Directory for output file.
        filename: PNG filename (ignored on fallback).

    Returns:
        Absolute path to output file, or ``None``.
    """
    out = _ensure_dir(output_dir)

    if not _HAS_MATPLOTLIB:
        return _export_json({"heatmap": heatmap_data}, out / "heatmap_data.json")

    try:
        fig, ax = plt.subplots(figsize=(10, 8))
        data = heatmap_data or [[0]]
        im = ax.imshow(data, cmap="RdYlGn", aspect="auto")
        ax.set_title("Parameter Heatmap")
        fig.colorbar(im, ax=ax)
        plt.tight_layout()
        filepath = out / filename
        fig.savefig(str(filepath), dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Heatmap saved to %s", filepath)
        return str(filepath)
    except Exception:
        logger.warning("Heatmap chart failed; exporting JSON fallback.", exc_info=True)
        return _export_json({"heatmap": heatmap_data}, out / "heatmap_data_fallback.json")


# ── Matplotlib renderers ──────────────────────────────────────────────


def _render_equity_chart(
    metrics: dict[str, Any],
    equity_curve: pd.Series,
    trades: list[Any] | None = None,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """Render equity curve (top) + drawdown (bottom) subplots."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # ── Equity curve ──────────────────────────────────────────────────
    ax0 = axes[0]
    if equity_curve is not None and len(equity_curve) > 0:
        ax0.plot(equity_curve.index, equity_curve.values, linewidth=1.5, color="green")
        # Shade positive/negative regions
        final_val = equity_curve.iloc[-1] if len(equity_curve) > 0 else 0
        start_val = equity_curve.iloc[0] if len(equity_curve) > 0 else 1
        color = "green" if final_val >= start_val else "red"
        ax0.fill_between(equity_curve.index, equity_curve.values, start_val,
                         alpha=0.15, color=color)

        # Scatter trade entry markers if trades provided
        if trades:
            _plot_trade_markers(ax0, trades)

    # Title with key metrics
    title_parts = []
    for k in ("total_return", "sharpe_ratio", "max_drawdown"):
        v = metrics.get(k)
        if v is not None:
            if k == "max_drawdown":
                title_parts.append(f"Max DD: {float(v):.1%}" if isinstance(v, float) else f"Max DD: {v}")
            elif k == "sharpe_ratio":
                title_parts.append(f"Sharpe: {float(v):.2f}" if isinstance(v, float) else f"Sharpe: {v}")
            else:
                title_parts.append(f"Return: {float(v):.1%}" if isinstance(v, float) else f"Return: {v}")
    ax0.set_title("  |  ".join(title_parts) if title_parts else "Equity Curve")
    ax0.set_ylabel("Equity")
    ax0.grid(True, alpha=0.3)

    # ── Drawdown ──────────────────────────────────────────────────────
    ax1 = axes[1]
    if equity_curve is not None and len(equity_curve) > 1:
        peak = equity_curve.expanding().max()
        dd = (equity_curve - peak) / peak
        ax1.fill_between(dd.index, dd.values * 100, 0, alpha=0.4, color="red")
        ax1.set_title("Drawdown (%)")
        ax1.set_ylabel("Drawdown %")
        ax1.grid(True, alpha=0.3)

    # Format x-axis dates
    if equity_curve is not None and len(equity_curve) > 0:
        try:
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            fig.autofmt_xdate()
        except Exception:
            pass  # non-datetime index — skip formatting

    plt.tight_layout()
    return fig, axes


def _plot_trade_markers(ax: Any, trades: list[Any]) -> None:
    """Add green/red scatter markers for winning/losing trades on the equity axis."""
    buy_x, buy_y = [], []
    sell_x, sell_y = [], []
    for t in trades:
        ts = getattr(t, "timestamp", getattr(t, "entry_time", None))
        pnl = getattr(t, "pnl", 0)
        if ts is None or pnl is None:
            continue
        try:
            ts = pd.Timestamp(ts)
        except Exception:
            continue
        if pnl > 0:
            buy_x.append(ts)
            buy_y.append(pnl)
        else:
            sell_x.append(ts)
            sell_y.append(pnl)
    if buy_x:
        ax.scatter(buy_x, buy_y, marker="^", color="green", s=20, alpha=0.6, label="Win")
    if sell_x:
        ax.scatter(sell_x, sell_y, marker="v", color="red", s=20, alpha=0.6, label="Loss")
    if buy_x or sell_x:
        ax.legend(loc="upper left", fontsize=8)


# ── Fallback exporters ────────────────────────────────────────────────


def _export_csv(metrics: dict[str, Any], path: Path) -> str:
    """Export key metrics as CSV (graceful fallback)."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, val in _extract_metrics(metrics).items():
            writer.writerow([key, val])
    logger.info("Backtest metrics CSV saved to %s", path)
    return str(path)


def _export_json(data: Any, path: Path) -> str:
    """Export any data as JSON (graceful fallback)."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Backtest JSON saved to %s", path)
    return str(path)


def _extract_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Pull key scalar metrics from the result dict for CSV export."""
    result: dict[str, Any] = {}
    for attr in (
        "total_return",
        "annual_return",
        "cagr",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "max_drawdown",
        "win_rate",
        "profit_factor",
        "total_trades",
        "avg_trade",
        "volatility",
        "var_95",
        "cvar_95",
    ):
        val = metrics.get(attr)
        if val is not None:
            result[attr] = val
    return result


# ── Convenience helpers ───────────────────────────────────────────────


def set_bokeh_output(*args: Any, **kwargs: Any) -> None:
    """No-op: QNA uses matplotlib, not Bokeh."""
    return None


__all__ = [
    "plot_results",
    "plot_heatmaps",
    "set_bokeh_output",
    "_HAS_MATPLOTLIB",
]
