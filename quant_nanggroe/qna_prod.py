#!/usr/bin/env python3
"""QNA Production Runner — Autonomous Quant Trading Pipeline.

Based on research consolidation:
- n8n trading pipeline: Start → AI Analysis → Risk Mgmt → LTF Confirm → News + COT → Telegram
- SMC/ICT engine for primary signal generation
- MULKY_OS ATR-based stop loss
- ConstitutionalRiskGuard for risk enforcement
- 15-minute cycle
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("qna_prod.log"),
    ],
)
logger = logging.getLogger("qna_prod")

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_SYMBOLS = ["BTC-USD", "ETH-USD", "EURUSD", "XAUUSD"]
CYCLE_INTERVAL = 900  # 15 minutes
DB_PATH = Path("data/qna_prod.db")


# ── Database ──────────────────────────────────────────────────────────────────

def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            side TEXT,
            confidence REAL,
            entry_price REAL,
            stop_loss REAL,
            atr_sl_distance REAL,
            lot_size REAL,
            risk_amount REAL,
            risk_pct REAL,
            confluence_score REAL,
            regime TEXT,
            smc_bias TEXT,
            poi_type TEXT,
            killzone TEXT,
            checks_passed INTEGER,
            checks_total INTEGER,
            metadata TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cycle_number INTEGER,
            symbols_analyzed INTEGER,
            signals_generated INTEGER,
            errors INTEGER,
            duration_ms REAL
        )
    """)
    conn.commit()
    return conn


def save_signal(conn: sqlite3.Connection, signal: Dict[str, Any]) -> None:
    conn.execute(
        """INSERT INTO signals (
            timestamp, symbol, signal_type, side, confidence,
            entry_price, stop_loss, atr_sl_distance,
            lot_size, risk_amount, risk_pct,
            confluence_score, regime, smc_bias, poi_type,
            killzone, checks_passed, checks_total, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            signal.get("timestamp", datetime.now().isoformat()),
            signal.get("symbol", ""),
            signal.get("signal_type", ""),
            signal.get("side"),
            signal.get("confidence"),
            signal.get("entry_price"),
            signal.get("stop_loss"),
            signal.get("atr_sl_distance"),
            signal.get("lot_size"),
            signal.get("risk_amount"),
            signal.get("risk_pct"),
            signal.get("confluence_score"),
            signal.get("regime"),
            signal.get("smc_bias"),
            signal.get("poi_type"),
            signal.get("killzone"),
            signal.get("checks_passed", 0),
            signal.get("checks_total", 0),
            json.dumps(signal.get("metadata", {})),
        ),
    )
    conn.commit()


def save_cycle(
    conn: sqlite3.Connection,
    cycle_number: int,
    symbols: int,
    signals: int,
    errors: int,
    duration_ms: float,
) -> None:
    conn.execute(
        """INSERT INTO cycles (timestamp, cycle_number, symbols_analyzed, signals_generated, errors, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(), cycle_number, symbols, signals, errors, duration_ms),
    )
    conn.commit()


# ── Engine Integration ────────────────────────────────────────────────────────

class QNAProductionRunner:
    """Main production trading runner — 15-minute autonomous cycle."""

    def __init__(self, symbols: Optional[List[str]] = None, telegram: bool = False):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.running = False
        self.cycle_number = 0
        self._db: Optional[sqlite3.Connection] = None
        self._smc_engine: Any = None
        self._risk_gate: Any = None
        self._telegram_bot: Any = None
        self._use_telegram = telegram
        self._register_signals()

    def _register_signals(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_stop)
        signal.signal(signal.SIGINT, self._handle_stop)

    def _handle_stop(self, *args) -> None:
        logger.info("Shutdown signal received")
        self.running = False

    def _init_engines(self) -> None:
        try:
            from quant_nanggroe.engine.smc.engine import SMCEngine
            from quant_nanggroe.engine.smc.killzone import KillZone
            from quant_nanggroe.engine.risk.checks import ConstitutionalRiskGuard
            from quant_nanggroe.engine.risk.atr_sl import calculate_atr_sl
            from quant_nanggroe.engine.risk.sizing import calculate_position_size
            from quant_nanggroe.engine.execution.protection import ProtectionEngine
            from quant_nanggroe.exchange.broker_pack import TradingMode, get_registry

            self._smc_engine = SMCEngine()
            self._killzone = KillZone()
            self._risk_gate = ConstitutionalRiskGuard()
            self._protection_engine = ProtectionEngine(intrabar_mode="balanced")
            self._broker_registry = get_registry()
            self._trading_mode = TradingMode()
            logger.info("BrokerPacks: %d registered, mode=%s",
                        len(self._broker_registry.list_packs()),
                        self._trading_mode.mode)
            try:
                from quant_nanggroe.engine.council_integration import integrate_council_findings
                asyncio.create_task(self._run_council_integration())
            except ImportError:
                pass

            if self._use_telegram:
                try:
                    from quant_nanggroe.agents.telegram_bot import TelegramSignalBot
                    self._telegram_bot = TelegramSignalBot()
                    logger.info("Telegram bot initialized")
                except Exception as e:
                    logger.warning(f"Telegram init failed: {e}")

            logger.info("Engines initialized: SMC, Risk, Killzone, Protection, BrokerPacks")
        except ImportError as e:
            logger.warning(f"Engine import failed (using fallback): {e}")
            self._smc_engine = None


    async def _run_council_integration(self) -> None:
        """Run council integration findings asynchronously at startup."""
        try:
            from quant_nanggroe.engine.council_integration import integrate_council_findings
            result = await integrate_council_findings()
            logger.info("Council integration: HF=%d rules, QNA=%d packs, SKILLS=%d pending",
                        result["wave1_hf"]["rules_added"],
                        result["wave2_qna"]["packs_registered"],
                        result["wave3_skills"]["pending_algorithms"])
        except Exception as e:
            logger.warning(f"Council integration skipped: {e}")
    def _generate_ohlcv(self, symbol: str) -> Dict[str, Any]:
        """Fetch OHLCV data for symbol."""
        try:
            from quant_nanggroe.providers.crypto_provider import CryptoProvider

            provider = CryptoProvider()
            data = provider.get_historical_data(symbol, "1h", limit=100)
            if data and "high" in data:
                return data
        except Exception as e:
            logger.warning(f"Provider failed for {symbol}: {e}")
        return {}

    def _run_smc_analysis(self, symbol: str, ohlcv: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run SMC analysis pipeline."""
        if not ohlcv or not self._smc_engine:
            return None

        try:
            analysis = self._smc_engine.analyze(
                high=ohlcv.get("high", []),
                low=ohlcv.get("low", []),
                close=ohlcv.get("close", []),
                volume=ohlcv.get("volume", []),
            )

            # Calculate ATR stop loss
            atr_result = {}
            try:
                from quant_nanggroe.engine.risk.atr_sl import calculate_atr_sl

                atr_result = calculate_atr_sl(
                    high=ohlcv.get("high", []),
                    low=ohlcv.get("low", []),
                    close=ohlcv.get("close", []),
                    entry_price=analysis.get("entry_price", ohlcv.get("close", [0])[-1] if ohlcv.get("close") else 0),
                    side=analysis.get("bias", "neutral"),
                )
            except Exception as e:
                logger.debug(f"ATR calc failed: {e}")

            return {**analysis, **atr_result}
        except Exception as e:
            logger.error(f"SMC analysis failed for {symbol}: {e}")
            return None

    def _run_risk_gate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Run risk gate checks on signal."""
        if not self._risk_gate:
            return {"approved": True, "checks_passed": 0, "checks_total": 0}

        try:
            from quant_nanggroe.engine.risk.checks import TradeRequest, TradeAction, PortfolioSnapshot

            request = TradeRequest(
                symbol=signal.get("symbol", ""),
                action=TradeAction.BUY if signal.get("side") == "buy" else TradeAction.SELL,
                quantity=signal.get("lot_size", 0),
                price=signal.get("entry_price", 0),
            )
            portfolio = PortfolioSnapshot(total_equity=10000)
            result = self._risk_gate.check_trade(request=request, portfolio=portfolio)
            return {
                "approved": result.approved,
                "checks_passed": sum(1 for c in result.check_results if c.approved) if result.check_results else 0,
                "checks_total": len(result.check_results) if result.check_results else 0,
                "details": str(result.details),
            }
        except Exception as e:
            logger.warning(f"Risk gate failed: {e}")
            return {"approved": True, "checks_passed": 0, "checks_total": 0}

    async def run_cycle(self) -> int:
        """Execute one full trading cycle."""
        self.cycle_number += 1
        cycle_start = time.time()
        signals_generated = 0
        errors = 0

        logger.info(f"=== Cycle {self.cycle_number} ===")

        for symbol in self.symbols:
            try:
                # 1. Fetch market data
                ohlcv = self._generate_ohlcv(symbol)

                # 2. Run SMC analysis
                analysis = self._run_smc_analysis(symbol, ohlcv)
                if not analysis:
                    logger.debug(f"No analysis for {symbol}")
                    continue

                # 3. Calculate position size
                try:
                    from quant_nanggroe.engine.risk.sizing import calculate_position_size

                    sizing = calculate_position_size(
                        entry_price=analysis.get("entry_price", 0),
                        stop_loss=analysis.get("stop_loss", 0),
                        account_balance=10000,
                        risk_per_trade=0.02,
                    )
                except Exception:
                    sizing = {}

                # 4. Run risk gate
                risk_result = self._run_risk_gate({
                    "symbol": symbol,
                    "side": analysis.get("bias"),
                    "lot_size": sizing.get("lot_size", 0),
                    "entry_price": analysis.get("entry_price", 0),
                })

                # 5. Build signal
                signal = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": symbol,
                    "signal_type": "smc",
                    "side": analysis.get("bias"),
                    "confidence": analysis.get("confidence", 0),
                    "entry_price": analysis.get("entry_price"),
                    "stop_loss": analysis.get("stop_loss"),
                    "atr_sl_distance": analysis.get("sl_distance"),
                    "lot_size": sizing.get("lot_size"),
                    "risk_amount": sizing.get("risk_amount"),
                    "risk_pct": sizing.get("risk_pct"),
                    "confluence_score": analysis.get("confluence_score"),
                    "regime": analysis.get("regime"),
                    "smc_bias": analysis.get("smc_bias"),
                    "poi_type": analysis.get("poi_type"),
                    "killzone": analysis.get("killzone"),
                    "checks_passed": risk_result.get("checks_passed", 0),
                    "checks_total": risk_result.get("checks_total", 0),
                    "metadata": {"risk_approved": risk_result.get("approved", True)},
                }

                # 6. Send Telegram
                if self._telegram_bot and signal.get("side") and signal.get("side") != "neutral":
                    try:
                        msg = (
                            f"\U0001f4c8 *{symbol}* — QNA Signal\n"
                            f"Side: {signal.get('side')}\n"
                            f"Entry: {signal.get('entry_price') or 'N/A'}\n"
                            f"SL: {signal.get('stop_loss') or 'N/A'}\n"
                            f"Confidence: {signal.get('confidence', 0)*100:.0f}%\n"
                            f"Risk: {signal.get('risk_pct', 0):.1f}%\n"
                            f"Confluence: {signal.get('confluence_score', 'N/A')}\n"
                            f"POI: {signal.get('poi_type', 'N/A')}"
                        )
                        await self._telegram_bot.send_message(msg)
                    except Exception as e:
                        logger.debug(f"Telegram send failed: {e}")

                # 7. Persist
                if self._db:
                    save_signal(self._db, signal)

                signals_generated += 1
                logger.info(
                    f"Signal: {symbol} {signal.get('side')} "
                    f"conf={signal.get('confidence'):.2f} "
                    f"risk={risk_result.get('approved', True)}"
                )

            except Exception as e:
                errors += 1
                logger.error(f"Error processing {symbol}: {e}")

        duration = (time.time() - cycle_start) * 1000
        if self._db:
            save_cycle(self._db, self.cycle_number, len(self.symbols), signals_generated, errors, duration)

        if self._telegram_bot and signals_generated > 0:
            try:
                summary = (
                    f"\u26a1 *Cycle {self.cycle_number} Summary*\n"
                    f"Symbols: {len(self.symbols)}\n"
                    f"Signals: {signals_generated}\n"
                    f"Errors: {errors}\n"
                    f"Duration: {duration:.0f}ms"
                )
                await self._telegram_bot.send_message(summary)
            except Exception as e:
                logger.debug(f"Telegram summary failed: {e}")

        logger.info(
            f"Cycle {self.cycle_number} done: "
            f"{signals_generated} signals, {errors} errors, {duration:.0f}ms"
        )
        return signals_generated

    async def run_forever(self) -> None:
        """Run production cycle indefinitely."""
        self.running = True
        self._db = init_db()
        self._init_engines()

        logger.info(f"QNA Production Runner started — {len(self.symbols)} symbols, {CYCLE_INTERVAL}s cycle")

        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Cycle failed: {e}")

            for _ in range(CYCLE_INTERVAL):
                if not self.running:
                    break
                await asyncio.sleep(1)

        self._cleanup()

    def _cleanup(self) -> None:
        if self._db:
            self._db.close()
        if self._telegram_bot:
            try:
                asyncio.run(self._telegram_bot.close())
            except Exception:
                pass
        logger.info("QNA Production Runner stopped")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QNA Production Trading Runner")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS, help="Symbols to trade")
    parser.add_argument("--cycle", type=int, default=CYCLE_INTERVAL, help="Cycle interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run single cycle then exit")
    parser.add_argument("--db", type=str, default=None, help="Database path")
    parser.add_argument("--telegram", action="store_true", default=False, help="Enable Telegram alerts")
    args = parser.parse_args()

    if args.db:
        global DB_PATH
        DB_PATH = Path(args.db)

    runner = QNAProductionRunner(symbols=args.symbols, telegram=args.telegram)

    if args.once:
        runner._db = init_db(DB_PATH)
        runner._init_engines()
        asyncio.run(runner.run_cycle())
        if runner._db:
            runner._db.close()
    else:
        try:
            asyncio.run(runner.run_forever())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
