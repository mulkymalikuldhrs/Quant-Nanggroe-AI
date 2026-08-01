"""Data Quality Framework — quality.py (Gap C8).

This module is the canonical entry point for the data quality framework.
It re-exports the SLA monitor + staleness detector implemented in
``monitor.py`` so callers can do::

    from quant_nanggroe.engine.data_quality.quality import DataQualityMonitor

Features proven here (all backed by ``monitor.py``):
  * Thread-safe provider health tracking (last success/failure, counts, errors)
  * Staleness detection: flag any provider whose last successful fetch is
    older than its per-provider threshold (default 600s / 10 min), including
    ``is_stale`` / ``age_seconds`` properties.
  * SLA monitor: ``get_health()`` returns overall_status (healthy/degraded/
    stale/offline) + per-provider breakdown (healthy/stale/degraded/failed).
  * Missing-value detection: ``check_data_integrity`` validates expected keys,
    nulls, and stale timestamps with a 0-100 quality score.
  * Missing-key warnings: ``record_success(data=...)`` logs when expected keys
    are absent (graceful degradation — never fails the pipeline).
"""
from quant_nanggroe.engine.data_quality.monitor import (
    DataQualityMonitor,
    ProviderState,
    get_monitor,
)

__all__ = ["DataQualityMonitor", "ProviderState", "get_monitor"]
