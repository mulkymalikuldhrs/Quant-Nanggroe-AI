
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


class ChartFactory:
    @staticmethod
    def candlestick(ohlcv: list[dict], title: str = "Price") -> dict:
        if not HAS_PLOTLY:
            return {"error": "plotly not installed"}
        fig = go.Figure(data=[go.Candlestick(
            x=[r.get("timestamp") for r in ohlcv],
            open=[r.get("open") for r in ohlcv],
            high=[r.get("high") for r in ohlcv],
            low=[r.get("low") for r in ohlcv],
            close=[r.get("close") for r in ohlcv],
        )])
        fig.update_layout(title=title)
        return fig

    @staticmethod
    def line(x: list, y: list, title: str = "Line") -> dict:
        if not HAS_PLOTLY:
            return {"error": "plotly not installed"}
        fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="lines")])
        fig.update_layout(title=title)
        return fig

    @staticmethod
    def heatmap(z: list[list[float]], x: list, y: list, title: str = "Heatmap") -> dict:
        if not HAS_PLOTLY:
            return {"error": "plotly not installed"}
        fig = go.Figure(data=[go.Heatmap(z=z, x=x, y=y)])
        fig.update_layout(title=title)
        return fig

    @staticmethod
    def histogram(data: list[float], nbins: int = 50, title: str = "Distribution") -> dict:
        if not HAS_PLOTLY:
            return {"error": "plotly not installed"}
        fig = go.Figure(data=[go.Histogram(x=data, nbinsx=nbins)])
        fig.update_layout(title=title)
        return fig

    @staticmethod
    def scatter(x: list, y: list, title: str = "Scatter") -> dict:
        if not HAS_PLOTLY:
            return {"error": "plotly not installed"}
        fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="markers")])
        fig.update_layout(title=title)
        return fig
