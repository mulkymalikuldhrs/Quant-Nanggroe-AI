from typing import Any, Optional


class PortfolioMetrics:
    def __init__(self):
        self._ffn = None
        try:
            import ffn

            self._ffn = ffn
        except ImportError:
            pass

    def calc_sharpe(self, returns: Any, risk_free: float = 0.02) -> Optional[float]:
        if self._ffn:
            return self._ffn.calc_sharpe(returns, rf=risk_free)
        return None

    def calc_max_drawdown(self, prices: Any) -> Optional[float]:
        if self._ffn:
            return self._ffn.calc_max_drawdown(prices)
        return None
