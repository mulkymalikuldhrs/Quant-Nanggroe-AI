"""FastAPI application for Quant Nanggroe AI."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Quant Nanggroe AI",
    description="Agentic Trading Intelligence OS API",
    version="0.2.0",
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
