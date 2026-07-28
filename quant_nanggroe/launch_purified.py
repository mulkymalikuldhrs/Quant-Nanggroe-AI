#!/usr/bin/env python3
"""
QNA Purified Engine Launcher
Starts the purified trading engine + API server + dashboard
"""
import os
import sys
import logging
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 0. PYTHONPATH setup — CRITICAL
# ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent  # repo root, not quant_nanggroe/
sys.path.insert(0, str(REPO_ROOT / "quant_nanggroe"))

# ──────────────────────────────────────────────────────────────
# 1. MT5 availability check
# ──────────────────────────────────────────────────────────────
MT5_AVAILABLE = False
mt5 = None
try:
    import MetaTrader5 as mt5
    if mt5.initialize():
        info = mt5.account_info()
        if info:
            print(f"✅ MT5 CONNECTED — Account: {info.login}, Balance: ${info.balance:,.2f}")
            MT5_AVAILABLE = True
        else:
            print("⚠️  MT5 initialized but no account info")
    else:
        print(f"❌ MT5 initialize() failed: {mt5.last_error()}")
except ImportError:
    print("⚠️  MetaTrader5 not installed — running in PAPER mode")
except Exception as e:
    print(f"⚠️  MT5 error: {e}")

# ──────────────────────────────────────────────────────────────
# 2. Logging setup
# ──────────────────────────────────────────────────────────────
LOG_DIR = REPO_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "purified.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("QNA-Launcher")

# ──────────────────────────────────────────────────────────────
# 3. FastAPI app with purified routes
# ──────────────────────────────────────────────────────────────
def create_app():
    """Create FastAPI app with purified routes enabled"""
    from fastapi import FastAPI
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    
    app = FastAPI(title="QNA Purified Engine", version="0.1.0")
    
    # Mount dashboard
    dashboard_path = REPO_ROOT / "dashboard.html"
    if dashboard_path.exists():
        app.mount("/dashboard", StaticFiles(directory=str(REPO_ROOT), html=True), name="dashboard")
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "mt5": MT5_AVAILABLE}
    
    # Try to import the real QNA app (has all routes)
    try:
        from quant_nanggroe.api.app import app as qna_app
        # Merge routes from QNA app into this one
        for route in qna_app.routes:
            if route.path.startswith("/api"):
                app.router.routes.append(route)
        log.info("✅ Full QNA API merged (purified + existing routes)")
    except Exception as e:
        log.warning(f"Could not load full QNA app, using minimal: {e}")
        # Minimal app with just purified routes
        from quant_nanggroe.api.routes import trading
        app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
        log.info("✅ Minimal purified routes loaded")
    
    return app


# ──────────────────────────────────────────────────────────────
# 4. Main entry
# ──────────────────────────────────────────────────────────────
def main():
    import uvicorn
    from uvicorn.config import Config
    
    # Get port from env or default
    port = int(os.environ.get("QNA_API_PORT", "8000"))
    host = os.environ.get("QNA_API_HOST", "0.0.0.0")
    
    log.info("=" * 60)
    log.info("QNA PURIFIED ENGINE LAUNCHER")
    log.info("=" * 60)
    log.info(f"Repo: {REPO_ROOT}")
    log.info(f"MT5: {'LIVE' if MT5_AVAILABLE else 'PAPER'}")
    log.info(f"API: http://{host}:{port}")
    log.info(f"Dashboard: http://{host}:{port}/dashboard")
    log.info(f"Docs: http://{host}:{port}/docs")
    log.info(f"Logs: {LOG_FILE}")
    log.info("=" * 60)
    
    app = create_app()
    
    # Run with uvicorn
    config = Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    
    try:
        server.run()
    except KeyboardInterrupt:
        log.info("Shutdown requested")
    finally:
        if mt5 and MT5_AVAILABLE:
            mt5.shutdown()
        log.info("QNA Purified Engine stopped")


if __name__ == "__main__":
    main()