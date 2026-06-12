"""Prometheus Metrics — Observability for Quant Nanggroe AI
=========================================================
Defines counters, histograms, and gauges for request tracking,
order placement, risk checks, and active positions.
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ── Metrics Definitions ───────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "http_request_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ORDERS_PLACED = Counter(
    "orders_placed_total",
    "Total number of trading orders placed",
    ["symbol", "side", "exchange"],
)

RISK_CHECKS = Counter(
    "risk_checks_total",
    "Total number of risk checks performed",
    ["result"],  # result: "pass" | "reject" | "warn"
)

ACTIVE_POSITIONS = Gauge(
    "active_positions",
    "Current number of open positions",
    ["exchange"],
)


# ── FastAPI Middleware ─────────────────────────────────────────────────

async def prometheus_middleware(request: Request, call_next: Callable) -> Response:
    """ASGI middleware that records request count and latency."""
    start = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start
    endpoint = request.url.path
    method = request.method
    status = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    return response


# ── /metrics Endpoint Helper ───────────────────────────────────────────

def metrics_response() -> Response:
    """Return a FastAPI Response with the latest Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
