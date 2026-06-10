"""
FastAPI Application — Main API server
=======================================
Lifespan events (DB connection, Redis), router inclusion,
CORS, auth middleware, health check endpoint.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from quant_nanggroe_ai.config import get_settings
from quant_nanggroe_ai.logging import setup_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown events."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level, json_output=settings.is_production)

    # ── Startup ─────────────────────────────────────────────────────
    # Initialize shared engine singletons eagerly so import errors
    # surface immediately rather than on the first request.
    from quant_nanggroe_ai.services import init_all_services

    init_all_services(app)

    # Wire the app into the graph module so nodes can access shared singletons
    from quant_nanggroe_ai.agents.graph import set_app

    set_app(app)

    # Initialize database (graceful degradation if unavailable)
    try:
        from quant_nanggroe_ai.data.database import init_db

        await init_db()
        logger.info("startup_database_connected")
    except Exception as exc:
        logger.warning(
            "startup_database_unavailable",
            error=str(exc),
            msg="Database not available — running without persistence",
        )

    # Initialize Redis cache (graceful degradation if unavailable)
    try:
        from quant_nanggroe_ai.data.cache import init_redis

        await init_redis(url=settings.redis.url)
        logger.info("startup_redis_connected")
    except Exception as exc:
        logger.warning(
            "startup_redis_unavailable",
            error=str(exc),
            msg="Redis not available — running without cache",
        )

    logger.info("startup_complete", app=settings.app_name, env=settings.app_env)

    yield

    # ── Shutdown ────────────────────────────────────────────────────
    try:
        from quant_nanggroe_ai.data.cache import close_redis

        await close_redis()
        logger.info("shutdown_redis_closed")
    except Exception as exc:
        logger.error("shutdown_redis_close_failed", error=str(exc))

    try:
        from quant_nanggroe_ai.data.database import close_db

        await close_db()
        logger.info("shutdown_database_closed")
    except Exception as exc:
        logger.error("shutdown_database_close_failed", error=str(exc))

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

    # ── CORS Middleware ──────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else ["https://qna.example.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Auth Middleware ─────────────────────────────────────────────
    from quant_nanggroe_ai.api.auth import AuthMiddleware

    auth_excluded_paths = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/status",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
    ]
    app.add_middleware(
        AuthMiddleware,
        excluded_paths=auth_excluded_paths,
        auth_provider=getattr(settings, "auth_provider", "local"),
    )

    # ── Include Routers ─────────────────────────────────────────────
    from quant_nanggroe_ai.api.routes import market, trading, agents, backtest, portfolio, ws, auth

    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
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
            method=request.method,
            path=str(request.url),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    return app
