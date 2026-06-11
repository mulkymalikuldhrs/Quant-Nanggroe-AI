"""FastAPI Application — Main API server
=======================================
Lifespan events, router inclusion, CORS, auth middleware, health check endpoint.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from quant_nanggroe.config import get_settings

logger = logging.getLogger(__name__)


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

    logger.info("startup_complete", extra={"app": settings.app_name, "env": "development"})

    # ── P0-1 SAFETY: Auth warning ──────────────────────────────────
    if not settings.require_auth:
        logger.warning(
            "⚠️  SECURITY WARNING: Authentication is DISABLED (QNAI_REQUIRE_AUTH=false). "
            "Trading endpoints are accessible without API keys. "
            "NEVER use this in production!"
        )

    # ── P0-3 SAFETY: Trading mode banner ───────────────────────────
    try:
        from quant_nanggroe.config.trading_mode import TradingModeConfig
        TradingModeConfig()  # Triggers startup banner
    except Exception:
        pass

    yield

    # ── Shutdown ────────────────────────────────────────────────────
    logger.info("shutdown_complete")


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

    # ── CORS Middleware (P0-1 SAFETY: Restrictive defaults) ─────────
    # Read allowed origins from settings. If none configured,
    # CORS is effectively disabled (no origins = no cross-origin requests).
    # This is the SAFEST default — operators must explicitly allow origins.
    cors_origins = settings.cors_origins_list
    if not cors_origins:
        # No origins configured — most restrictive: allow no cross-origin
        # We use a sentinel that won't match any real origin
        logger.warning(
            "CORS: No allowed origins configured (QNAI_CORS_ALLOWED_ORIGINS is empty). "
            "No cross-origin requests will be permitted. "
            "Configure QNAI_CORS_ALLOWED_ORIGINS for frontend access."
        )
        cors_origins = []  # Empty list = no CORS allowed

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True if cors_origins else False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["X-API-Key", "Content-Type", "Authorization"],
    )

    # ── Include Routers ─────────────────────────────────────────────
    from quant_nanggroe.api.routes import market, trading, agents, backtest, portfolio, ws

    app.include_router(market.router, prefix="/api/market", tags=["Market"])
    app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
    app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
    app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])
    app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
    app.include_router(ws.router, prefix="/api/ws", tags=["WebSocket"])

    # ── Health Check ────────────────────────────────────────────────
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "quant-nanggroe-ai"}

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

    return app
