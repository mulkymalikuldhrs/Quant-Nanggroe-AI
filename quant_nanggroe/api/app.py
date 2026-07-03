"""FastAPI Application — Main API server
=======================================
Lifespan events, router inclusion, CORS, auth middleware, health check endpoint.
Prometheus metrics, rate limiting, and proper CORS configuration.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from quant_nanggroe.api.middleware import RateLimitMiddleware, AuthMiddleware, SecurityHeadersMiddleware
from quant_nanggroe.security.auth import JWTAuth, APIKeyAuth, UserRole
from quant_nanggroe.config import get_settings

logger = logging.getLogger(__name__)

# ── Prometheus Metrics ────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "qnai_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "qnai_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown events."""
    settings = get_settings()

    # ── Startup ─────────────────────────────────────────────────────
    # Initialize shared engine singletons eagerly so import errors
    # surface immediately rather than on the first request.
    try:
        from quant_nanggroe.services import init_all_services
        init_all_services(app)
        logger.info("startup_services_initialized")
    except Exception as exc:
        logger.warning(
            "startup_services_unavailable",
            extra={"error": str(exc), "msg": "Services not available — running without persistence"},
        )

    logger.info("qnai_starting", extra={"app": settings.app_name, "env": "development"})

    yield

    # ── Shutdown ────────────────────────────────────────────────────
    logger.info("qnai_shutdown_initiated")

    # 1. Close exchange connections
    try:
        if hasattr(app.state, 'exchange_manager') and app.state.exchange_manager:
            for name, exchange in app.state.exchange_manager.exchanges.items():
                try:
                    await exchange.close()
                except Exception as e:
                    logger.warning("exchange_close_error: name=%s, error=%s", name, e)
            logger.info("exchanges_closed")
    except Exception as e:
        logger.warning("exchange_manager_shutdown_error: %s", e)

    # 2. Close WebSocket connections
    try:
        if hasattr(app.state, 'active_websockets'):
            for ws in list(app.state.active_websockets):
                try:
                    await ws.close()
                except Exception:
                    pass
            logger.info("websockets_closed")
    except Exception as e:
        logger.warning("websocket_close_error: %s", e)

    # 3. Flush audit logs to disk
    try:
        from quant_nanggroe.engine.audit import AuditLogger
        audit = AuditLogger()
        audit.flush()
        logger.info("audit_flushed_on_shutdown")
    except Exception as e:
        logger.warning("audit_flush_error: %s", e)

    # 4. Drain in-flight tasks
    try:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info("draining_tasks: count=%d", len(tasks))
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.warning("task_drain_error: %s", e)

    logger.info("qnai_shutdown_complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Agentic Trading Intelligence OS",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Prometheus Tracking Middleware ───────────────────────────────
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        """Track request count and latency for every HTTP request."""
        method = request.method
        # Use route path if available, otherwise raw path
        path = request.url.path

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        status = response.status_code
        REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

        return response

    # ── CORS Middleware ──────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

    # ── Security Headers Middleware ──────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Auth Middleware ──────────────────────────────────────────────
    jwt_auth = JWTAuth(
        secret_key=settings.jwt_secret,
        default_ttl=3600,
    )
    api_key_auth = APIKeyAuth()

    # Register a default admin API key from settings or env
    default_key = os.environ.get("QNAI_API_KEY", "")
    if default_key:
        api_key_auth.add_key(default_key, "admin", UserRole.ADMIN)

    app.state.auth = jwt_auth
    app.state.api_key_auth = api_key_auth

    app.add_middleware(
        AuthMiddleware,
        auth=jwt_auth,
        api_key_auth=api_key_auth,
    )

    # ── Rate Limit Middleware ────────────────────────────────────────
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

    # ── Include Routers ─────────────────────────────────────────────
    from quant_nanggroe.api.routes import market, trading, agents, backtest, portfolio, ws, memory, ecosystem
    from quant_nanggroe.api.routes import colony, monitor

    app.include_router(market.router, prefix="/api/market", tags=["Market"])
    app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
    app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
    app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])
    app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
    app.include_router(ws.router, prefix="/api/ws", tags=["WebSocket"])
    app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])
    app.include_router(ecosystem.router, prefix="/api", tags=["Ecosystem"])
    app.include_router(colony.router, prefix="/api", tags=["Colony"])
    app.include_router(monitor.router, prefix="/api/monitor", tags=["Monitor"])

    # ── Health Check ────────────────────────────────────────────────
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "quant-nanggroe-ai"}

    # ── Prometheus Metrics ──────────────────────────────────────────
    @app.get("/metrics")
    async def metrics():
        """Expose Prometheus metrics."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ── Global Exception Handler ────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            extra={
                "method": request.method,
                "path": str(request.url),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    # ── Signal Handlers ─────────────────────────────────────────────
    _setup_signal_handlers(app)

    return app


def _setup_signal_handlers(app: FastAPI) -> None:
    """Register SIGTERM/SIGINT handlers for graceful shutdown."""
    import asyncio

    def _handle_shutdown_signal(signum: int, frame: Any) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("received_signal: signal=%s", sig_name)
        try:
            # Schedule the shutdown in the running event loop
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:
            # No running loop — force exit as last resort
            logger.warning("no_running_loop_for_shutdown: forcing_exit")
            os._exit(0)

    try:
        signal.signal(signal.SIGTERM, _handle_shutdown_signal)
        signal.signal(signal.SIGINT, _handle_shutdown_signal)
        logger.debug("signal_handlers_registered")
    except (OSError, ValueError):
        # Signals can only be registered in the main thread
        logger.debug("signal_handlers_skipped: not_in_main_thread")
