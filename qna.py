#!/usr/bin/env python3
"""

   This is the SINGLE source of truth for all entry points.
   All other entry points (main.py, cli.py, daemon_manager.py,
   qna_prod.py, standalone.py, worker.py) have been archived.
   Use `qna.py <mode>` for everything.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ── Ensure project root is on sys.path (BEFORE any project imports) ─
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env BEFORE any module import reads env vars (QNA_LIVE_TRADING, JWT, etc.) ──
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(str(PROJECT_ROOT / ".env"), override=False)
except ImportError:
    pass  # dotenv not installed; rely on explicit env vars only.

# ── Environment sanitize (strip Hermes venv leak) ──────────────
_hermes_paths = [p for p in os.environ.get("PYTHONPATH", "").split(";") if "hermes" in p.lower()]
if _hermes_paths:
    clean = [p for p in os.environ.get("PYTHONPATH", "").split(";") if "hermes" not in p.lower()]
    os.environ["PYTHONPATH"] = ";".join(clean)
    sys.path = [p for p in sys.path if "hermes" not in p.lower()]
__version__ = "8.1.4"
QNA_VERSION = __version__

# ── PID management for daemon mode ─────────────────────────────────
PID_DIR = PROJECT_ROOT / "data" / "daemons"
PID_FILE = PID_DIR / "qna_daemon.pid"

# ── Logging ─────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("QNAI_LOG_LEVEL", os.environ.get("QNA_LOG_LEVEL", "INFO")).upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("QNA")


# ── Banner ──────────────────────────────────────────────────────────

BANNER = """
"""


#  AGENT CONFIGURATION — Single source of truth
#  (main.py and daemon_manager.py delegate here via load_agent_config)

DEFAULT_AGENTS: Dict[str, Dict[str, Any]] = {
    # ── Verified existing agent modules only ───────────
    "researcher": {
        "module": "quant_nanggroe.agents.researcher",
        "class": "ResearcherAgent",
        "priority": 2,
        "auto_start": True,
        "description": "🔬 Market research & analysis",
    },
    "trader": {
        "module": "quant_nanggroe.agents.trader",
        "class": "TraderAgent",
        "priority": 2,
        "auto_start": True,
        "description": "📈 Trade execution & decision making",
    },
    "strategist": {
        "module": "quant_nanggroe.agents.strategist",
        "class": "StrategistAgent",
        "priority": 2,
        "auto_start": True,
        "description": "📊 Strategy generation & optimization",
    },
}


def load_agent_config() -> Dict[str, Dict[str, Any]]:
    """Load agent configuration, merging defaults with user overrides."""
    config_path = PROJECT_ROOT / "config" / "agents.json"
    agents = dict(DEFAULT_AGENTS)

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            agents.update(user_config)
            logger.info("Loaded agent config from %s", config_path)
        except Exception as e:
            logger.warning("Failed to load agent config: %s", e)

    return agents


#  MODE: CLI

def run_cli(args: argparse.Namespace) -> int:
    """[DEPRECATED] Run interactive CLI shell. Use unified mode instead."""
    print(BANNER)
    print("🎯 Entering CLI mode. Type 'help' for commands, 'exit' to quit.")
    print()

    agents = load_agent_config()

    while True:
        try:
            cmd = input("QNA > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                break
            if cmd.lower() == "help":
                _print_cli_help()
                continue
            if cmd.lower() == "status":
                print(f"  Version: {__version__}")
                print(f"  Agents: {len(agents)} configured")
                print("  Modes: unified | api | daemon | hedge | status | cli [deprecated] | web [deprecated]")
                continue
            if cmd.lower() == "agents":
                for name, cfg in agents.items():
                    icon = cfg.get("description", "🤖")[:2]
                    print(f"  {icon} {name} (priority {cfg['priority']})")
                continue
            print(f"  Unknown command: {cmd}. Type 'help' for options.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            break

    return 0


def _print_cli_help() -> None:
    """Print CLI usage help."""
    print("""
  Commands:
    help              Show this help
    status            Show system status
    agents            List configured agents
    exit / quit       Exit CLI

  To run in other modes:
    python qna.py unified   Auto-detect & orchestrate (default)
    python qna.py api       Start API server
    python qna.py daemon    Start daemon mode
    python qna.py hedge     Hedge Fund aggregator
    python qna.py status    System health check
    python qna.py cli       [DEPRECATED] Interactive CLI
    python qna.py web       [DEPRECATED] [BROKEN — web_interface/ missing] Legacy web UI
""")


#  MODE: API Server

def run_api(args: argparse.Namespace) -> int:
    """Start the FastAPI server."""
    port = args.port or 8000
    host = args.host or "0.0.0.0"

    print(BANNER)
    print(f"🚀 Starting API server on {host}:{port}...")
    print()

    try:
        import uvicorn

        from quant_nanggroe.api.app import create_app

        app = create_app()
        logger.info("API server starting on %s:%s", host, port)

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=LOG_LEVEL.lower(),
            reload=args.reload,
        )
    except ImportError as e:
        logger.error("Failed to start API server: %s", e)
        logger.error("Install required packages: pip install uvicorn fastapi")
        return 1
    except Exception as e:
        logger.error("API server error: %s", e)
        return 1

    return 0


#  MODE: Daemon

class DaemonRunner:
    """Background daemon that manages agent lifecycle."""

    def __init__(self, agents: Dict[str, Dict[str, Any]]):
        self.agents = agents
        self.running: Dict[str, Any] = {}
        self._shutdown = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self._signal_handler)
            except (OSError, ValueError):
                pass

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info("Received signal %s, initiating shutdown...", signum)
        self._shutdown = True

    def start(self) -> None:
        """Start all agents and enter monitor loop."""
        logger.info("Starting %d agents...", len(self.agents))

        # Start agents in priority order
        sorted_agents = sorted(
            self.agents.items(),
            key=lambda x: x[1].get("priority", 5),
        )

        for agent_id, config in sorted_agents:
            if config.get("auto_start", True):
                if self._start_agent(agent_id, config):
                    logger.info("  [OK] %s", agent_id)
                else:
                    logger.warning("  [FAIL] %s", agent_id)

        logger.info("All agents started. Entering monitor loop...")

        # Monitor loop
        while not self._shutdown:
            time.sleep(30)
            self._check_health()

    def _start_agent(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """Start a single agent."""
        try:
            module_path = config["module"]
            class_name = config.get("class", "")
            instance_name = config.get("instance", agent_id)

            module = __import__(module_path, fromlist=[instance_name])
            agent_instance = getattr(module, instance_name, None)

            if agent_instance is None and class_name:
                agent_class = getattr(module, class_name, None)
                if agent_class:
                    # Agents require an LLM instance — create one from settings
                    # Fallback chain: settings -> 9router (free local gateway)
                    import inspect
                    sig = inspect.signature(agent_class)
                    if "llm" in sig.parameters:
                        from quant_nanggroe.agents.base import create_llm
                        llm = None
                        # Try settings-based LLM first
                        try:
                            from quant_nanggroe.config.settings import get_settings
                            _s = get_settings()
                            llm = create_llm(
                                provider=config.get("llm_provider", _s.default_llm_provider),
                                model=config.get("llm_model", _s.default_llm_model),
                                temperature=config.get("llm_temperature", _s.default_llm_temperature),
                            )
                        except Exception:
                            pass
                        # Fallback: 9router local gateway (free, always available)
                        if llm is None:
                            llm = create_llm(
                                provider="openrouter",
                                model="deepseek/deepseek-chat-v3-0324",
                                base_url="http://localhost:20128/v1",
                                api_key="9router",
                                temperature=0.0,
                            )
                        agent_instance = agent_class(llm=llm)
                    else:
                        agent_instance = agent_class()

            if agent_instance is not None:
                self.running[agent_id] = {
                    "instance": agent_instance,
                    "config": config,
                    "start_time": datetime.now(),
                    "status": "running",
                }
                return True

            logger.warning("Agent %s: module loaded but no instance found", agent_id)
            return False

        except ImportError as e:
            logger.debug("Agent %s not available: %s", agent_id, e)
            return False
        except Exception as e:
            logger.warning("Failed to start agent %s: %s", agent_id, e)
            return False

    def _check_health(self) -> None:
        """Check health of all running agents."""
        for agent_id in list(self.running.keys()):
            try:
                agent = self.running[agent_id]["instance"]
                if hasattr(agent, "status") and agent.status in ("error", "crashed"):
                    logger.warning("Agent %s unhealthy, restarting...", agent_id)
                    self._restart_agent(agent_id)
            except Exception:
                pass

    def _restart_agent(self, agent_id: str) -> None:
        """Restart a failed agent."""
        if agent_id in self.running:
            config = self.running[agent_id]["config"]
            self.stop_agent(agent_id)
            time.sleep(1)
            self._start_agent(agent_id, config)

    def stop_agent(self, agent_id: str) -> None:
        """Stop a specific agent."""
        if agent_id in self.running:
            try:
                agent = self.running[agent_id]["instance"]
                if hasattr(agent, "stop"):
                    agent.stop()
                elif hasattr(agent, "status"):
                    agent.status = "stopped"
            except Exception as e:
                logger.warning("Error stopping agent %s: %s", agent_id, e)
            del self.running[agent_id]

    def stop_all(self) -> None:
        """Stop all running agents."""
        for agent_id in list(self.running.keys()):
            self.stop_agent(agent_id)
        logger.info("All agents stopped.")


def _write_pid() -> None:
    """Write current PID to PID file."""
    PID_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _read_pid() -> Optional[int]:
    """Read PID from PID file."""
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def stop_daemon() -> int:
    """Stop the running daemon process."""
    pid = _read_pid()
    if pid is None:
        print("❌ No daemon PID file found. Is the daemon running?")
        print("   Try: python qna.py status")
        return 1
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"✅ Daemon (PID {pid}) stopped.")
        if PID_FILE.exists():
            PID_FILE.unlink()
    except ProcessLookupError:
        print(f"⚠️  Daemon (PID {pid}) not found. Removing stale PID file.")
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        print(f"❌ Failed to stop daemon: {e}")
        return 1
    return 0


def run_daemon(args: argparse.Namespace) -> int:
    """Run daemon mode with agent lifecycle management."""
    print(BANNER)
    _write_pid()
    agents = load_agent_config()

    # ── Start CandleScheduler (real-time candle-close watcher) ──
    _scheduler = None
    try:
        from quant_nanggroe.engine.candle_scheduler import start_candle_scheduler
        _scheduler = start_candle_scheduler()
        logger.info("CandleScheduler started (real-time multi-TF candle-close watcher)")
    except Exception as e:
        logger.warning("CandleScheduler failed, falling back to PipelineScheduler: %s", e)
        try:
            from quant_nanggroe.engine.scheduler import start_default_scheduler
            interval = int(os.environ.get("QNA_SCHEDULER_INTERVAL", "15"))
            _scheduler = start_default_scheduler(interval_minutes=interval)
            logger.info("PipelineScheduler fallback started (interval=%d min)", interval)
        except Exception as e2:
            logger.error("CRITICAL: Both schedulers failed — daemon will run but NO TRADING will occur: %s / %s", e, e2)
            logger.error("Check MT5 connection and try: python qna.py status")

    # ── Start Auto-Retrain loop (parameter freshness, fail-closed) ──
    _retrainer = None
    try:
        from quant_nanggroe.engine.agentic import get_autonomous_pipeline
        from quant_nanggroe.engine.auto_retrain import get_auto_retrainer

        class _PipelineFetcher:
            """Lazy pipeline handle — resolves on first fetch, not at boot.
            Runs the async _fetch_data via asyncio.run() in the retrain thread
            (which has no running loop of its own)."""
            def __init__(self):
                self._pipe = None
            def _resolve(self):
                if self._pipe is None:
                    p = get_autonomous_pipeline()
                    p.load_strategies()
                    self._pipe = p
                return self._pipe
            def __call__(self, symbol, timeframe):
                import asyncio as _aio
                coro = self._resolve()._fetch_data(symbol, timeframe=timeframe)
                try:
                    loop = _aio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop is not None and loop.is_running():
                    # We're inside an async context — use run_coroutine_threadsafe
                    future = _aio.run_coroutine_threadsafe(coro, loop)
                    return future.result(timeout=30)
                else:
                    return _aio.run(coro)

        _symbols = list(getattr(_scheduler, "symbols", None) or ["EURUSD"])
        _retrainer = get_auto_retrainer(fetcher=_PipelineFetcher(), symbols=_symbols)
        if _retrainer.start():
            logger.info("AutoRetrainer started (every %.1fh)", _retrainer.interval_hours)
    except Exception as e:
        logger.warning("AutoRetrainer init skipped: %s", e)

    # ── Journal Sync: now runs inside CandleScheduler's asyncio loop ──
    # (MT5 C-API is not thread-safe; daemon thread approach silently crashed)
    logger.info("JournalSync: integrated into CandleScheduler event loop (hourly)")

    daemon = DaemonRunner(agents)
    try:
        daemon.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
    finally:
        daemon.stop_all()
        # JournalSync is now in CandleScheduler's loop — no daemon thread to stop
        if _retrainer is not None:
            try:
                _retrainer.stop()
            except Exception as e:
                logger.warning("Error stopping retrainer: %s", e)
        if _scheduler is not None:
            try:
                if hasattr(_scheduler, 'stop'):
                    _scheduler.stop()
                    logger.info("Scheduler stopped")
            except Exception as e:
                logger.warning("Error stopping scheduler: %s", e)
        if PID_FILE.exists():
            PID_FILE.unlink()

    return 0


#  MODE: Web UI (Legacy)

def run_web(args: argparse.Namespace) -> int:
    """[DEPRECATED] [BROKEN — web_interface/ missing] Start the legacy Flask web UI. Use api mode instead."""
    port = args.port or 5000

    print(BANNER)
    print(f"🌐 Starting web UI on port {port}...")
    print()

    try:
        from web_interface.app import app as flask_app
        flask_app.run(host="0.0.0.0", port=port, debug=False)
    except ImportError as e:
        logger.error("Web UI not available: %s", e)
        print("  Install Flask: pip install flask")
        return 1
    except Exception as e:
        logger.error("Web UI error: %s", e)
        return 1

    return 0


#  MODE: LiveEngine Trading Loop

def run_live(args: argparse.Namespace) -> int:
    """Run the LiveEngine trading loop (60s cycle, full pipeline)."""
    print(BANNER)
    print("🏃 LiveEngine — trading loop starting...")
    print()
    try:
        from quant_nanggroe.live_engine import LiveEngine
        engine = LiveEngine()
        engine.start()
    except KeyboardInterrupt:
        print("\n🛑 LiveEngine stopped by user.")
    except Exception as e:
        logger.error("LiveEngine error: %s", e)
        return 1
    return 0


#  MODE: Status / Health Check

def run_status(args: argparse.Namespace) -> int:
    """Show system status and health."""
    print(BANNER)
    print("📊 System Status\n")

    print(f"  Version:      {__version__}")
    print(f"  Python:       {sys.version.split()[0]}")
    print(f"  Platform:     {sys.platform}")
    print(f"  Project Root: {PROJECT_ROOT}")
    print()

    # Check if API server is running
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8000/health", timeout=3)
        if resp.status == 200:
            print("  API Server:   ✅ Running (port 8000)")
        else:
            print("  API Server:   ⚠️  Responding but unhealthy")
    except Exception:
        print("  API Server:   ❌ Not running (port 8000)")
        print("                 Start with: python qna.py api")

    # Check if web UI is running
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:5000/", timeout=3)
        print("  Web UI:       ✅ Running (port 5000)")
    except Exception:
        print("  Web UI:       ❌ Not running (port 5000)")
        print("                 Start with: python qna.py web")

    # Import project to check version consistency
    _import_quant_nanggroe()

    print()
    print("  Modes available:")
    print("    python qna.py unified              [DEFAULT] Auto-detect & orchestrate")
    print("    python qna.py unified --mode hedge  Run unified in hedge mode")
    print("    python qna.py api                   API server (FastAPI)")
    print("    python qna.py daemon                Background daemon")
    print("    python qna.py status                This status check")
    print("    python qna.py hedge                 Hedge Fund aggregator (multi-provider voting)")
    print("    python qna.py hedge --paper EURUSD  Paper trade EURUSD")
    print("    python qna.py stop                  Stop running daemon")
    print("    python qna.py cli         [DEPRECATED] Interactive CLI")
    print("    python qna.py web         [DEPRECATED] [BROKEN — web_interface/ missing] Legacy web UI")

    return 0


def _import_quant_nanggroe() -> bool:
    """Lazy import of quant_nanggroe package. Returns True if successful."""
    try:
        import quant_nanggroe  # noqa: F401
        logger.debug("quant_nanggroe package loaded successfully")
        return True
    except ImportError as e:
        logger.debug("quant_nanggroe package not available: %s", e)
        return False
    except Exception as e:
        logger.warning("quant_nanggroe package import warning: %s", e)
        return False


#  MODE: Hedge Fund Aggregator

def run_hedge(args: argparse.Namespace) -> int:
    """Run the multi-provider hedge fund aggregator.

    Reads causal macro context from env vars (set by unified mode's pre-filter):
      - QNA_CAUSAL_BIAS_{ASSET}: Directional bias (-1.0 to +1.0) per CME futures symbol
        e.g. QNA_CAUSAL_BIAS_GC1! = +0.72 (Gold bias)
      - QNA_MACRO_WEATHER: Risk-On / Risk-Off / NEUTRAL_MIXED
      - QNA_COT_STATUS: EXTREME_LONG_OVERBOUGHT / EXTREME_SHORT_OVERSOLD / BALANCED

    Also reads DCC-GARCH dynamic correlation context:
      - QNA_DCC_MEAN_CORR: Mean DCC correlation across assets
      - QNA_DCC_MEAN_VOL_PCT: Mean GARCH volatility %%
      - QNA_DCC_N_ASSETS: Number of assets in the correlation model

    Signal providers and strategy selectors should read these to filter
    signals by macro context. Example:
      bias_gc = float(os.environ.get("QNA_CAUSAL_BIAS_GC1!", "0"))
      if bias_gc < 0.3 and signal == "BUY" on XAUUSD: skip
    """
    print(BANNER)
    symbols = args.symbols or ["EURUSD"]
    print(f"🛡️  Hedge Fund Aggregator — symbols: {', '.join(symbols)}")
    if args.paper:
        print("   Paper trading mode ON")
        import os
        os.environ["PAPER_TRADE"] = "true"
    print()

    # Log macro context if available from causal pre-filter
    weather = os.environ.get("QNA_MACRO_WEATHER", "")
    cot = os.environ.get("QNA_COT_STATUS", "")
    biases = {k: v for k, v in os.environ.items() if k.startswith("QNA_CAUSAL_BIAS_")}
    if weather or cot or biases:
        logger.info(
            "Macro context active: weather=%s cot=%s biases=%d assets",
            weather, cot, len(biases),
        )

    # Log DCC-GARCH dynamic correlation context if available
    dcc_mean_corr = os.environ.get("QNA_DCC_MEAN_CORR", "")
    dcc_mean_vol = os.environ.get("QNA_DCC_MEAN_VOL_PCT", "")
    if dcc_mean_corr:
        logger.info(
            "DCC-GARCH context: mean_corr=%s mean_vol=%s%%",
            dcc_mean_corr, dcc_mean_vol or "?",
        )

    # Log COT institutional positioning context if available
    cot_signal = os.environ.get("QNA_COT_SIGNAL", "")
    cot_symbol = os.environ.get("QNA_COT_SYMBOL", "")
    if cot_signal:
        logger.info(
            "COT context: %s=%s (grade=%s, action=%s)",
            cot_symbol or "?",
            cot_signal,
            os.environ.get("QNA_COT_GRADE", "?"),
            os.environ.get("QNA_COT_ACTION", "?"),
        )

    # Thesis Drift Guard runs intra-engine in LiveEngine.execute_cycle()
    # and is not exposed via env vars (engine-internal concern).

    # Log Macro Surprise Index context if available
    msi_n = os.environ.get("QNA_MSI_N_SIGNIFICANT", "")
    if msi_n:
        logger.info(
            "MSI context: %s significant surprises",
            msi_n,
        )

    # Try the new pipeline module first
    try:
        from quant_nanggroe.pipeline.factory import create_pipeline
        pipeline = create_pipeline()
        import asyncio
        print("  Using unified pipeline...")
        results = []
        for sym in symbols:
            print(f"  {'='*58}")
            print(f"  HF RUN: {sym}")
            print(f"  {'='*58}")
            result = asyncio.run(pipeline.run(symbol=sym))
            results.append((sym, result))
            if result:
                verdict = "EXECUTED" if result.get("executed") else "SKIPPED"
                print(f"  → {verdict}: {json.dumps(result, default=str, indent=4)}")
            else:
                print("  → FAILED: no result returned")
            print()
        print(f"  DONE — {len(results)} symbols processed")
        for sym, res in results:
            status = "✅" if res and res.get("executed") else "⏭️"
            print(f"  {status} {sym}: verdict={res.get('verdict','?') if res else 'NONE'}")
        return 0
    except ImportError:
        logger.critical("Pipeline module NOT AVAILABLE — falling back to legacy hedge_fund")
    except Exception as e:
        logger.critical("Pipeline run FAILED (%s) — falling back to legacy hedge_fund", e)

    try:
        from quant_nanggroe.hedge_fund import run_once

        results = []
        for sym in symbols:
            print(f"  {'='*58}")
            print(f"  HF RUN: {sym}")
            print(f"  {'='*58}")
            result = run_once(sym)
            results.append((sym, result))
            if result:
                verdict = "EXECUTED" if result.get("executed") else "SKIPPED"
                print(f"  → {verdict}: {json.dumps(result, default=str, indent=4)}")
            else:
                print("  → FAILED: no result returned")
            print()

        print(f"  {'='*58}")
        print(f"  DONE — {len(results)} symbols processed")
        for sym, res in results:
            status = "✅" if res and res.get("executed") else "⏭️"
            print(f"  {status} {sym}: verdict={res.get('verdict','?') if res else 'NONE'}")
        return 0

    except ImportError as e:
        logger.error("Hedge Fund module not available: %s", e)
        logger.error("  Ensure quant_nanggroe.hedge_fund is in your PYTHONPATH")
        return 1
    except Exception as e:
        logger.error("Hedge Fund error: %s", e)
        return 1

#  MODE: Unified — Auto-detect & orchestrate

def run_unified(args: argparse.Namespace) -> int:
    """Run in unified mode — auto-detect and orchestrate all subsystems.

    This is the DEFAULT entry point. It:
      1. Checks the --mode flag (auto|hedge|crypto|agentic)
      2. Auto-detects from env vars if mode=auto
      3. Tries the pipeline factory first
      4. Falls back to legacy modes gracefully
    """
    print(BANNER)
    mode = args.unified_mode or os.environ.get("QNA_UNIFIED_MODE", "auto")
    print(f"🔀 Unified mode — mode={mode}")
    print()

    if mode == "agentic":
        print("  Agentic mode: running agent orchestration pipeline...")
        try:
            from quant_nanggroe.pipeline.factory import create_pipeline
            pipeline = create_pipeline()
            import asyncio
            result = asyncio.run(pipeline.run(symbol="BTC/USDT"))
            print(f"  ✅ Pipeline complete: {result}")
            return 0
        except ImportError:
            print("  ⚠️  Pipeline not available. Falling back to daemon mode.")
            return run_daemon(args)
        except Exception as e:
            logger.error("Agentic pipeline error: %s", e)
            return 1

    if mode == "crypto":
        print("  Crypto mode: running crypto pipeline...")
        try:
            from quant_nanggroe.pipeline.factory import create_pipeline
            pipeline = create_pipeline()
            import asyncio
            result = asyncio.run(pipeline.run(symbol="BTC/USDT"))
            print(f"  ✅ Pipeline complete: {result}")
            return 0
        except ImportError:
            print("  ⚠️  Pipeline not available. Falling back to hedge mode.")
            symbols = args.symbols or ["BTCUSDT", "ETHUSDT"]
            fallback_args = argparse.Namespace(symbols=symbols, paper=args.paper)
            return run_hedge(fallback_args)
        except Exception as e:
            logger.error("Crypto pipeline error: %s", e)
            return 1

    if mode == "hedge":
        print("  Hedge mode: delegating to run_hedge...")
        # Run causal macro pre-filter before hedge execution
        macro_event = os.environ.get("QNA_MACRO_EVENT", "")
        if macro_event:
            try:
                from quant_nanggroe.engine.causal import MasterQuantNanggroeEngine
                causal = MasterQuantNanggroeEngine()
                dxy = float(os.environ.get("QNA_DXY_CHANGE", "0"))
                bond = float(os.environ.get("QNA_BOND_CHANGE", "0"))
                # Phase 1-2: Macro context only (weather, biases, COT)
                # SMC alignment (Phase 3-4) requires a trade signal, which
                # doesn't exist yet at this pipeline stage. The macro context
                # is exposed via env for downstream signal generation to use.
                #
                # Build returns data for DCC-GARCH from available market data
                # (best-effort — if no data available, DCC phase is skipped).
                _returns_data = None
                try:
                    import numpy as np
                    import pandas as pd

                    from quant_nanggroe.engine_bridge import EnginePriceProvider as _EPP
                    _provider = _EPP()
                    _klines_data: dict[str, list[float]] = {}
                    for _sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
                        try:
                            _klines = _provider.get_klines(_sym, interval="1h", limit=50)
                            if _klines and len(_klines) >= 30:
                                _klines_data[_sym] = [c["close"] for c in _klines]
                        except Exception:
                            pass
                    if len(_klines_data) >= 2:
                        _min_n = min(len(v) for v in _klines_data.values())
                        _aligned = {s: v[-_min_n:] for s, v in _klines_data.items()}
                        _df = pd.DataFrame(_aligned)
                        _returns_data = np.log(_df / _df.shift(1)).dropna()
                        logger.info(
                            "DCC returns data: %d rows x %d assets",
                            len(_returns_data), len(_returns_data.columns),
                        )
                except Exception as _e:
                    logger.debug("DCC returns fetch unavailable: %s", _e)

                pre_filter = causal.evaluate_full_pipeline(
                    event_type=macro_event,
                    geopolitical_risk_delta=float(os.environ.get("QNA_GEOPOLITICAL_RISK", "0")),
                    dxy_change=dxy,
                    bond_change=bond,
                    smc_signal="HOLD",  # no signal yet — macro context only
                    returns=_returns_data,  # pass returns for DCC-GARCH fitting
                )
                logger.info("Causal macro context: %s", pre_filter["summary"])
                # Expose macro context to downstream via env vars
                for asset, bias in pre_filter.get("phase1_causal", {}).get("asset_biases", {}).items():
                    os.environ[f"QNA_CAUSAL_BIAS_{asset}"] = str(bias)
                weather = pre_filter.get("phase2_weather", {}).get("classification", "UNKNOWN")
                os.environ["QNA_MACRO_WEATHER"] = weather
                cot = pre_filter.get("phase2_cot", {}).get("status", "UNKNOWN")
                os.environ["QNA_COT_STATUS"] = cot
                # Expose DCC-GARCH dynamic correlation context
                dcc = pre_filter.get("phase2_dcc", {})
                if dcc.get("mean_corr") is not None:
                    os.environ["QNA_DCC_MEAN_CORR"] = str(dcc["mean_corr"])
                    os.environ["QNA_DCC_MEAN_VOL_PCT"] = str(dcc.get("mean_vol_pct", ""))
                    os.environ["QNA_DCC_N_ASSETS"] = str(dcc.get("n_assets", 0))
                # Expose detailed COT signal from phase2_cot (if available from COTAnalyzer)
                cot_detail = pre_filter.get("phase2_cot", {})
                cot_status = cot_detail.get("status", "UNKNOWN")
                os.environ["QNA_COT_STATUS"] = cot_status
                if cot_detail.get("analyzer_used"):
                    os.environ["QNA_COT_SYMBOL"] = str(cot_detail.get("symbol", ""))
                    os.environ["QNA_COT_SIGNAL"] = cot_status
                    os.environ["QNA_COT_GRADE"] = str(cot_detail.get("grade", ""))
                    os.environ["QNA_COT_ACTION"] = str(cot_detail.get("action", ""))
                    pct = cot_detail.get("percentile_noncomm")
                    if pct is not None:
                        os.environ["QNA_COT_PERCENTILE"] = str(pct)

                # Expose Macro Surprise Index context from phase1_msi
                msi = pre_filter.get("phase1_msi", {})
                if msi.get("connected"):
                    os.environ["QNA_MSI_CONNECTED"] = "1"
                    os.environ["QNA_MSI_N_SIGNIFICANT"] = str(msi.get("n_significant", 0))
                    events = msi.get("events", {})
                    for event_name, event_data in events.items():
                        if event_data.get("is_significant"):
                            os.environ[f"QNA_MSI_{event_name}"] = str(event_data.get("avg_msi", 0))

                if pre_filter.get("phase2_smt", {}).get("smt_divergence_detected"):
                    logger.warning("SMT divergence detected between correlated pairs — review positions")
                logger.info(
                    "Macro context: weather=%s cot=%s biases=%s",
                    weather, cot,
                    {k: round(float(v), 2) for k, v in os.environ.items()
                     if k.startswith("QNA_CAUSAL_BIAS_")},
                )
            except Exception as e:
                logger.debug("Causal pre-filter unavailable: %s", e)
        else:
            logger.info("No macro event set. Set QNA_MACRO_EVENT to enable causal macro context.")
        return run_hedge(args)

    # mode == "auto" (default)
    print("  Auto-detecting optimal mode...")

    # Priority 1: Try pipeline factory
    try:
        from quant_nanggroe.pipeline.factory import create_pipeline
        pipeline = create_pipeline()
        import asyncio
        print("  ✅ Pipeline found. Running unified pipeline...")
        result = asyncio.run(pipeline.run(symbol="BTC/USDT"))
        print(f"  ✅ Pipeline complete: {result}")
        return 0
    except ImportError:
        print("  ⚠️  Pipeline module not available.")
    except Exception as e:
        logger.warning("Pipeline error, falling back: %s", e)

    # Priority 2: Check if API should start
    if os.environ.get("QNA_MODE") == "api":
        print("  → Detected QNA_MODE=api. Starting API server...")
        return run_api(args)

    # Priority 3: Default to hedge mode
    print("  → Falling back to hedge fund aggregator mode.")
    return run_hedge(args)



def _auto_open_browser(url: str) -> None:
    """Open browser to URL if QNA_AUTO_OPEN is set (or default True)."""
    if os.environ.get("QNA_AUTO_OPEN", "1").lower() in ("1", "true", "yes"):
        try:
            import webbrowser
            webbrowser.open(url)
            logger.info("Auto-opened browser: %s", url)
        except Exception as e:
            logger.debug("Auto-open browser failed: %s", e)


#  CLI ARGUMENT PARSER

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="qna",
        description="Quant Nanggroe AI — Unified Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python qna.py unified                    [DEFAULT] Auto-detect & orchestrate
  python qna.py unified --mode hedge       Run unified in hedge mode
  python qna.py unified --mode crypto      Run unified in crypto mode
  python qna.py api                        Start API server on port 8000
  python qna.py api --port 8080            Custom port
  python qna.py daemon                     Background daemon mode
  python qna.py hedge --paper EURUSD       Paper trade EURUSD
  python qna.py status                     System health check
  python qna.py live                        LiveEngine trading loop (60s cycle)
  python qna.py cli             [DEPRECATED] Interactive CLI shell
  python qna.py web             [DEPRECATED] [BROKEN — web_interface/ missing] Legacy web UI on port 5000
        """,
    )

    parser.add_argument(
        "mode",
        nargs="?",
        choices=["unified", "cli", "api", "daemon", "web", "status", "stop", "hedge", "live"],
        default="unified",
        help="Launch mode (default: unified)",
    )
    parser.add_argument(
        "--mode",
        dest="unified_mode",
        type=str,
        default="auto",
        choices=["auto", "hedge", "crypto", "agentic"],
        help="Sub-mode for unified mode (auto|hedge|crypto|agentic, default: auto)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number (api: 8000, web: 5000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable hot-reload (api mode only)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Disable auto-open browser on start",
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        default=False,
        help="Force paper trading mode (hedge mode only)",
    )
    parser.add_argument(
        "symbols",
        nargs="*",
        default=None,
        help="Symbols to trade (hedge mode only, default: EURUSD)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    return parser


#  MAIN ENTRY POINT

def main() -> int:
    """Main entry point — routes to the selected mode."""
    parser = build_parser()
    args, _ = parser.parse_known_args()

    if args.version:
        print(f"Quant Nanggroe AI v{__version__}")
        return 0

    # ── C5: converge every mode (cli/daemon/api/web) on ONE kill-switch
    # state file. Without this the daemon + api + any bridge each keep their
    # own in-memory switch and never agree (split-brain). Idempotent; tests
    # that set QNA_KILL_SWITCH_STATE_FILE keep their isolation. Fail-closed
    # is enforced inside KillSwitch() if the file later becomes unreadable.
    try:
        from quant_nanggroe.engine.risk.kill_switch import configure_kill_switch_file
        configure_kill_switch_file()
    except Exception:  # pragma: no cover - never block boot on this
        pass

    # Route to the selected mode
    mode_map = {
        "unified": run_unified,
        "cli": run_cli,
        "api": run_api,
        "daemon": run_daemon,
        "web": run_web,
        "status": run_status,
        "hedge": run_hedge,
        "live": run_live,
        "stop": lambda a: stop_daemon(),
    }

    runner = mode_map.get(args.mode, run_unified)
    exit_code = runner(args)

    # Auto-open browser for api/web modes (unless --no-browser)
    if args.mode in ("api", "web") and not args.no_browser:
        port = args.port or (8000 if args.mode == "api" else 5000)
        _auto_open_browser(f"http://localhost:{port}")

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested.")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error: %s", e)
        sys.exit(1)
