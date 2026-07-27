"""Performance analytics: metrics computation and alpha decay."""

# Package init

__all__ = [
    'metrics',
    'alpha_decay',
]

from . import metrics
from .alpha_decay import AlphaDecayDetector, AlphaDecayMonitor, DecayResult, DecayStatus
from .metrics import PerformanceMetrics, compute_metrics, rolling_sharpe
