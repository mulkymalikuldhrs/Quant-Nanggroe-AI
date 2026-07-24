#!/usr/bin/env python3
"""
ai-hedge-fund → MT5 direct execution adapter.

Bridges ai-hedge-fund multi-agent trading decisions (15-investor debate)
to MT5 execution via QNA's existing infrastructure.

Usage:
    python qna-aihf-adapter.py EURUSD                  # paper mode (default)
    python qna-aihf-adapter.py AAPL --live              # live MT5 trading
    python qna-aihf-adapter.py BTC-USD --threshold 0.5  # custom min confidence
    python qna-aihf-adapter.py EURUSD --live --lots 0.1 # custom lot size
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── Ensure project root on sys.path ────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from quant_nanggroe.engine.agentic.adapters import AIHFAdapter
from quant_nanggroe.engine.agentic.voting import Bias

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] qna-aihf: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("qna-aihf-adapter")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ai-hedge-fund → MT5 direct execution adapter"
    )
    parser.add_argument("symbol", help="Trading symbol (e.g., EURUSD, AAPL, BTC-USD)")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute live MT5 trades (default: paper)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Minimum confidence threshold 0-1 (default: 0.6)",
    )
    parser.add_argument(
        "--lots",
        type=float,
        default=0.01,
        help="Trade lot/shares (default: 0.01)",
    )
    args = parser.parse_args()

    # ── Step 1: Fetch signal from ai-hedge-fund ─────────────────────
    logger.info("Fetching AIHF signal for %s...", args.symbol)
    adapter = AIHFAdapter()
    signal = adapter.fetch_signal(args.symbol)

    if signal is None:
        logger.warning(
            "No signal from AIHF (ai-hedge-fund unavailable or error). Exiting."
        )
        return 1

    if signal.bias == Bias.NEUTRAL:
        logger.info("AIHF recommends HOLD for %s. No trade.", args.symbol)
        return 0

    if signal.confidence < args.threshold:
        logger.info(
            "Signal %s for %s but confidence %.2f < threshold %.2f. Skipping.",
            signal.bias.value,
            args.symbol,
            signal.confidence,
            args.threshold,
        )
        return 0

    side = signal.bias.value  # "buy" or "sell"
    logger.info(
        "AIHF signal: %s (conf=%.2f) — threshold met, executing",
        side, signal.confidence,
    )

    # ── Step 2: Execute trade ───────────────────────────────────────
    if args.live:
        return _execute_live(side, args.symbol, args.lots)
    return _execute_paper(side, args.symbol, args.lots)


def _execute_paper(side: str, symbol: str, lots: float) -> int:
    """Paper-trade: log what would have happened."""
    logger.info(
        "[PAPER] ✓ %s %.4f %s — would place %s order",
        side.upper(), lots, symbol, side,
    )
    return 0


def _execute_live(side: str, symbol: str, lots: float) -> int:
    """Execute trade via MT5 through QNA's execution layer."""
    try:
        # Kill-switch guard
        try:
            from quant_nanggroe.engine.risk.kill_switch import KillSwitch

            ks = KillSwitch()
            if ks.is_any_level_active():
                logger.error("KILL SWITCH ACTIVE — trade blocked for %s", symbol)
                return 3
        except ImportError:
            logger.warning("KillSwitch not available, proceeding without guard")

        # MT5 execution
        from quant_nanggroe.connectors.mt5_broker import MT5Broker
        from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType
        from quant_nanggroe.engine.execution.brokers.mt5_adapter import MT5ExecutionBroker

        mt5 = MT5Broker()
        if not mt5.connect():
            logger.error("MT5 connection failed.")
            return 2

        broker = MT5ExecutionBroker(mt5)
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        order = Order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=lots,
        )
        result = broker.submit_order(order)
        fill_price = result.metadata.get("fill_price", "N/A")
        logger.info(
            "[LIVE] ✓ %s %.4f %s — status=%s fill=%s",
            side.upper(), lots, symbol,
            result.status.value, fill_price,
        )
        return 0

    except Exception as e:
        logger.error("MT5 execution failed: %s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
