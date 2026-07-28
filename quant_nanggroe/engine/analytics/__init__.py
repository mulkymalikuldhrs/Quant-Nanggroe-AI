"""Performance analytics: metrics computation and alpha decay."""

# Package init

__all__ = [
    'metrics',

]

from . import metrics
from .metrics import PerformanceMetrics, compute_metrics, rolling_sharpe
