"""FastAPI application for Quant Nanggroe AI."""

from __future__ import annotations

import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from quant_nanggroe.config.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    # ── Startup ───────────────────────────────────────────────────────────
    setup_logging(level="INFO", format_type="json")
    logger.info("quant-nanggroe-ai API starting up")

    # Graceful shutdown on SIGTERM / SIGINT
    def _shutdown(signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — shutting down gracefully", sig_name)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    yield  # application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("quant-nanggroe-ai API shutting down")


app = FastAPI(
    title="Quant Nanggroe AI",
    description="Agentic Trading Intelligence OS API",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "name": "Quant Nanggroe AI",
        "version": "0.2.0",
        "status": "operational",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/v1/agents")
async def list_agents():
    return {
        "agents": [
            {"name": "researcher", "role": "research", "status": "ready"},
            {"name": "trader", "role": "trading", "status": "ready"},
            {"name": "strategist", "role": "strategy", "status": "ready"},
            {"name": "risk", "role": "risk_management", "status": "ready"},
            {"name": "portfolio", "role": "portfolio", "status": "ready"},
            {"name": "execution", "role": "execution", "status": "ready"},
            {"name": "macro", "role": "macro_analysis", "status": "ready"},
            {"name": "crypto", "role": "crypto_analysis", "status": "ready"},
            {"name": "forex", "role": "forex_analysis", "status": "ready"},
        ]
    }
