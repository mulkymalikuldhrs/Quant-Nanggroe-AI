"""
Chart Factory — Unified chart creation for QNA dashboard.
Uses Plotly for interactive charts with matplotlib as fallback.
"""
import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    logger.warning("Plotly not available, using text-based charts")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class ChartFactory:
    """Factory for creating standardized charts"""

    def __init__(self, theme: str = "dark", width: int = 1200, height: int = 600):
        self.theme = theme
        self.width = width
        self.height = height
        self._colors = {
            "dark": {
                "bg": "#1a1a2e",
                "text": "#e0e0e0",
                "primary": "#00d2ff",
                "secondary": "#ff6b6b",
                "success": "#00e676",
                "warning": "#ff9100",
                "grid": "#2a2a4e",
            }
        }

    def _color(self, name: str) -> str:
        return self._colors.get(self.theme, self._colors["dark"]).get(name, "#fff")

    def ohlcv_chart(self, df: pd.DataFrame, title: str = "Price Chart") -> Any:
        """Create OHLCV candlestick chart"""
        if HAS_PLOTLY:
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3],
            )
            fig.add_trace(go.Candlestick(
                x=df.index, open=df.get('open', df.get('Open')),
                high=df.get('high', df.get('High')),
                low=df.get('low', df.get('Low')),
                close=df.get('close', df.get('Close')),
                name="OHLCV",
            ), row=1, col=1)
            volume = df.get('volume', df.get('Volume'))
            if volume is not None:
                fig.add_trace(go.Bar(x=df.index, y=volume, name="Volume"), row=2, col=1)
            fig.update_layout(
                title=title, template="plotly_dark" if self.theme == "dark" else "plotly_white",
                width=self.width, height=self.height,
                xaxis_rangeslider_visible=False,
            )
            return fig
        return {"type": "ohlcv", "title": title, "data_points": len(df)}

    def line_chart(self, data: Dict[str, pd.Series], title: str = "",
                    x_label: str = "", y_label: str = "") -> Any:
        """Create multi-line chart"""
        if HAS_PLOTLY:
            fig = go.Figure()
            for name, series in data.items():
                fig.add_trace(go.Scatter(
                    x=series.index, y=series.values, mode='lines', name=name
                ))
            fig.update_layout(
                title=title, template="plotly_dark" if self.theme == "dark" else "plotly_white",
                xaxis_title=x_label, yaxis_title=y_label,
                width=self.width, height=self.height,
            )
            return fig
        return {"type": "line", "title": title, "series": list(data.keys())}

    def bar_chart(self, categories: List[str], values: List[float],
                   title: str = "", color: str = None) -> Any:
        """Create bar chart"""
        if HAS_PLOTLY:
            fig = go.Figure([go.Bar(x=categories, y=values, marker_color=color or self._color("primary"))])
            fig.update_layout(
                title=title, template="plotly_dark" if self.theme == "dark" else "plotly_white",
                width=self.width, height=self.height,
            )
            return fig
        return {"type": "bar", "title": title, "categories": len(categories)}

    def heatmap(self, matrix: np.ndarray, x_labels: List[str],
                 y_labels: List[str], title: str = "") -> Any:
        """Create heatmap (e.g., correlation matrix)"""
        if HAS_PLOTLY:
            fig = go.Figure(data=go.Heatmap(
                z=matrix, x=x_labels, y=y_labels, colorscale="RdBu_r",
            ))
            fig.update_layout(
                title=title, template="plotly_dark" if self.theme == "dark" else "plotly_white",
                width=self.width, height=self.height,
            )
            return fig
        return {"type": "heatmap", "title": title, "shape": matrix.shape}

    def equity_curve(self, returns: pd.Series, title: str = "Equity Curve") -> Any:
        """Create equity curve from returns"""
        equity = (1 + returns).cumprod()
        return self.line_chart({"Equity": equity}, title=title, y_label="Portfolio Value")

    def drawdown_chart(self, returns: pd.Series, title: str = "Drawdown") -> Any:
        """Create drawdown chart"""
        equity = (1 + returns).cumprod()
        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max
        return self.line_chart({"Drawdown": drawdown}, title=title, y_label="Drawdown %")

    def distribution_chart(self, returns: pd.Series, title: str = "Return Distribution") -> Any:
        """Create return distribution histogram"""
        if HAS_PLOTLY:
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=returns, nbinsx=50, name="Returns"))
            fig.add_vline(x=np.mean(returns), line_dash="dash", line_color="red",
                          annotation_text=f"Mean: {np.mean(returns):.4f}")
            fig.update_layout(
                title=title, template="plotly_dark" if self.theme == "dark" else "plotly_white",
                width=self.width, height=self.height,
            )
            return fig
        return {"type": "histogram", "title": title, "n": len(returns)}
