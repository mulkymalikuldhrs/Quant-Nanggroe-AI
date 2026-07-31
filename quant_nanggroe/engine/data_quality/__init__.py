"""Data Quality Framework — staleness detection and health monitoring.

Gap C8 from the 100/100/100 roadmap: Data Quality Framework.
Provides real-time staleness tracking for all TTLCache-backed providers
in providers/tradebobby/ plus other data sources.
"""
from quant_nanggroe.engine.data_quality.monitor import (
    DataQualityMonitor,
    ProviderState,
    get_monitor,
)

__all__ = [
    "DataQualityMonitor",
    "ProviderState",
    "get_monitor",
]
