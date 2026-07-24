#!/usr/bin/env python3
"""QNA Standalone — Autonomous Quant Hedge Fund, zero Hermes dependency.

This is the "jalan tanpa Hermes" entry point. Everything runs in a single
process: AutonomousPipeline + SelfAware + StrategyEvolver + RiskGuard +
TradeLifecycleManager. No MCP servers, no gateway, no cron daemon needed.

Usage:
    python -m quant_nanggroe.standalone          # run forever (15min cycles)
    python -m quant_nanggroe.standalone --once   # single cycle then exit
    python -m quant_nanggroe.standalone --cycle 300  # 5-minute cycles

Optional Hermes integration (when available):
    Hermes can monitor/trigger this script via cron (no_agent mode).
    When Hermes is absent, the script runs fully autonomously.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Logging (file + console, no Hermes MCP) ──────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("qna_standalone.log"),
    ],
)
logger = logging.getLogger("qna_standalone")

# ── Optional components (graceful degradation) ───────────────────────

try:
    from quant_nanggroe.engine.agentic.autonomous import AutonomousPipeline
    _HAS_PIPELINE = True
except ImportError as e:
    AutonomousPipeline = None  # type: ignore
    _HAS_PIPELINE = False
    logger.warning("AutonomousPipeline not available: %s", e)

try:
    from quant_nanggroe.engine.self_aware import SelfAware
    _HAS_SELF_AWARE = True
except ImportError:
    SelfAware = None  # type: ignore
    _HAS_SELF_AWARE = False

try:
    from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
    _HAS_EVOLVER = True
except ImportError:
    StrategyEvolver = None  # type: ignore
    _HAS_EVOLVER = False

try:
    from quant_nanggroe.engine.risk.manager import RiskManager
    _HAS_RISK = True
except ImportError:
    RiskManager = None  # type: ignore
    _HAS_RISK = False


# ── DB (SQLite, zero infra) ──────────────────────────────────────────

DB_PATH = Path("data/qna_standalone.db")


def init_db(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            cycles_completed INTEGER DEFAULT 0,
            signals_generated INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            summary TEXT
        )
    """)
    return conn


# ── Standalone Runner ────────────────────────────────────────────────


class StandaloneRunner:
    """Runs the full autonomous hedge fund cycle without Hermes."""

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        cycle_interval: int = 900,
        db_path: Path = DB_PATH,
    ):
        self.symbols = symbols or ["EURUSD", "XAUUSD", "BTC-USD"]
        self.cycle_interval = cycle_interval
        self._db = init_db(db_path)
        self._db_path = db_path
        self._running = True
        self._cycle_count = 0

        # Pipeline (gracefully degrades if import fails)
        self._pipeline: Optional[AutonomousPipeline] = None
        self._evolver: Optional[StrategyEvolver] = None
        self._risk: Optional[RiskManager] = None

        self._init_components()

        # Signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _init_components(self) -> None:
        """Initialize all components — each is optional (graceful degrade)."""
        if _HAS_EVOLVER and StrategyEvolver is not None:
            try:
                self._evolver = StrategyEvolver()
                logger.info("StrategyEvolver initialized")
            except Exception as e:
                logger.warning("StrategyEvolver init failed: %s", e)

        if _HAS_RISK and RiskManager is not None:
            try:
                self._risk = RiskManager()
                logger.info("RiskManager initialized")
            except Exception as e:
                logger.warning("RiskManager init failed: %s", e)

        if _HAS_PIPELINE and AutonomousPipeline is not None:
            try:
                self._pipeline = AutonomousPipeline(
                    # Standalone mode: no Hermes self-correction, use local fallback
                    self_correction=None,
                )
                logger.info("AutonomousPipeline initialized")
            except Exception as e:
                logger.warning("AutonomousPipeline init failed: %s", e)

    def _handle_signal(self, signum: int, _frame: Any) -> None:
        logger.info("Received signal %d, shutting down gracefully...", signum)
        self._running = False

    async def _run_pipeline(self) -> dict[str, Any]:
        """Run one full autonomous pipeline cycle.

        Returns summary dict with signal count + any errors.
        """
        result: dict[str, Any] = {
            "signals": 0,
            "error": None,
            "evolutions": 0,
        }

        if self._pipeline is None:
            logger.warning("Pipeline not available — skipping cycle")
            return result

        try:
            pipeline_result = await self._pipeline.run(symbols=self.symbols)

            # Self-reflection (if available)
            reflection = getattr(pipeline_result, "self_reflection", None)
            if reflection:
                logger.info("Self-reflection: %s", reflection.summary if hasattr(reflection, 'summary') else str(reflection))

            # Evolution validation gate (auto-triggered if pipeline finds underperformers)
            if self._evolver is not None:
                stats = self._evolver.get_stats()
                result["evolutions"] = stats.get("total_attempts", 0)

            result["signals"] = getattr(pipeline_result, "signals_count", 0)

        except Exception as e:
            logger.exception("Pipeline cycle failed: %s", e)
            result["error"] = str(e)

        return result

    async def _write_state(self, summary: dict) -> None:
        """Persist cycle state to SQLite (zero Hermes dependency)."""
        try:
            cur = self._db.execute(
                "INSERT INTO cycles (started_at, finished_at, cycles_completed, signals_generated, errors, summary) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    self._cycle_count,
                    summary.get("signals", 0),
                    1 if summary.get("error") else 0,
                    json.dumps(summary),
                ),
            )
            self._db.commit()
        except Exception as e:
            # Non-fatal: DB write failure
            logger.error("DB write failed: %s", e)

    async def run_cycle(self) -> dict[str, Any]:
        """Execute exactly one cycle."""
        self._cycle_count += 1
        logger.info("=== Cycle %d started ===", self._cycle_count)

        summary = await self._run_pipeline()
        await self._write_state(summary)

        logger.info(
            "=== Cycle %d complete: %d signals, evos=%d ===",
            self._cycle_count,
            summary.get("signals", 0),
            summary.get("evolutions", 0),
        )
        return summary

    async def run_forever(self) -> None:
        """Run cycles indefinitely."""
        logger.info("Standalone runner started (interval=%ds)", self.cycle_interval)
        while self._running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.exception("Unhandled cycle error: %s", e)
            await asyncio.sleep(self.cycle_interval)
        logger.info("Standalone runner stopped after %d cycles", self._cycle_count)

    def close(self) -> None:
        """Cleanup resources."""
        if self._db:
            self._db.close()
        logger.info("Standalone runner closed")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for standalone mode (no Hermes)."""
    import json  # for DB write

    parser = argparse.ArgumentParser(
        description="QNA Standalone — Autonomous Quant Hedge Fund (no Hermes)"
    )
    parser.add_argument(
        "--symbols", nargs="+",
        default=["EURUSD", "XAUUSD", "BTC-USD"],
        help="Symbols to trade (default: EURUSD XAUUSD BTC-USD)",
    )
    parser.add_argument(
        "--cycle", type=int, default=900,
        help="Cycle interval in seconds (default: 900 = 15min)",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run single cycle then exit",
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="Custom database path",
    )
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else DB_PATH

    runner = StandaloneRunner(
        symbols=args.symbols,
        cycle_interval=args.cycle,
        db_path=db_path,
    )

    try:
        if args.once:
            asyncio.run(runner.run_cycle())
        else:
            asyncio.run(runner.run_forever())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        runner.close()


if __name__ == "__main__":
    main()
