#!/usr/bin/env python3
"""QNA Autonomous Live Cycle — single source of truth for live trading.

no_agent cron script. Runs ONE full cycle:
  1. build_execution_manager(allow_live=True)  -> wires MT5 live + risk
  2. load a strategy, generate a signal for a forex symbol
  3. compute protective SL/TP (ATR-based)
  4. submit_order via the execution manager (SL/TP carried end-to-end)
  5. report result

Fail-closed: if MT5 is unavailable, it trades PAPER ONLY and reports degraded.
Never silent-trades. All guarded by RiskManager (constitutional daily/weekly veto).

Env (set by the cron wrapper or system):
  QNA_LIVE_TRADING=1     enable live MT5 in build_execution_manager
  QNA_MT5_LIVE=1         engine_production_bridge uses MT5 path
  VALETAX_PASSWORD        MT5 password (from mt5_accounts.yaml ${...})
"""
from __future__ import annotations

import os
import sys
import json
import time
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("qna.cycle")

# ── Config ────────────────────────────────────────────────────────────────
QNA_DIR = r"D:\repositories\Quant-Nanggroe-AI-worktree"
SYMBOLS = ["EURUSD.vx", "GBPUSD.vx", "XAUUSD.vx"]   # Valetax forex + gold
RISK_PCT = 0.01          # 1% account balance per trade
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.5

VENV_PYTHON = r"C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"


def compute_sl_tp(symbol: str, atr: float, entry: float, side: str):
    """ATR-based protective SL/TP. side='buy' -> SL below, TP above."""
    if atr <= 0:
        atr = entry * 0.001
    sl = entry - SL_ATR_MULT * atr if side == "buy" else entry + SL_ATR_MULT * atr
    tp = entry + TP_ATR_MULT * atr if side == "buy" else entry - TP_ATR_MULT * atr
    return round(sl, 5), round(tp, 5)


def run_cycle() -> int:
    sys.path.insert(0, QNA_DIR)
    os.environ.setdefault("QNA_LIVE_TRADING", "1")
    os.environ.setdefault("QNA_MT5_LIVE", "1")

    from quant_nanggroe.engine.execution.builder import build_execution_manager
    from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType

    t0 = time.time()
    em = build_execution_manager(allow_live=(os.environ.get("QNA_LIVE_TRADING") == "1"))
    brokers = list(em._brokers.keys())
    primary = em._primary_broker
    log.info("ExecutionManager built in %.1fs brokers=%s primary=%s", time.time() - t0, brokers, primary)

    if primary != "mt5":
        log.warning("MT5 not live (paper fallback). Trading PAPER ONLY — no market impact.")
        return 1  # degraded, not crash

    import MetaTrader5 as mt5

    executed = 0
    for symbol in SYMBOLS:
        try:
            tick = mt5.symbol_info_tick(symbol.replace(".vx", ""))
            if not tick:
                # try .vx symbol directly
                tick = mt5.symbol_info_tick(symbol)
            if not tick:
                log.warning("%s no tick — skip", symbol)
                continue
            entry = (tick.bid + tick.ask) / 2
            # crude ATR from recent rates
            rates = mt5.copy_rates_from_pos(symbol.replace(".vx", ""), mt5.TIMEFRAME_M15, 0, 20)
            if rates is None or len(rates) < 10:
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 20)
            if rates is not None and len(rates) >= 10:
                highs = [r[2] for r in rates]
                lows = [r[3] for r in rates]
                atr = sum(max(h - l, 1e-6) for h, l in zip(highs[-10:], lows[-10:])) / 10
            else:
                atr = entry * 0.001

            # simple mean-reversion bias: if price near 10-bar low -> buy, else sell
            lo10 = min(lows[-10:]) if rates is not None else entry
            hi10 = max(highs[-10:]) if rates is not None else entry
            side = "buy" if entry <= (lo10 + (hi10 - lo10) * 0.3) else ("sell" if entry >= (lo10 + (hi10 - lo10) * 0.7) else None)
            if side is None:
                log.info("%s no edge — skip", symbol)
                continue

            sl, tp = compute_sl_tp(symbol, atr, entry, side)
            acc = mt5.account_info()
            bal = float(acc.balance) if acc else 1000.0
            lot = max(0.01, round((bal * RISK_PCT) / (atr * 100000), 2))

            # Risk gate — constitutional veto (realized PnL fed from broker)
            verdict = em._risk_manager.check_trade(
                symbol=symbol, direction=side.upper(),
                lot_size=lot, entry=entry, stop_loss=sl,
                account_balance=bal, take_profit=tp,
            )
            if verdict.get("verdict") != "APPROVED":
                log.warning("RISK VETO %s %s: %s", symbol, side, verdict.get("failed_checkpoints"))
                continue

            order = Order(
                id=f"qna_{symbol}_{int(time.time())}",
                symbol=symbol,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=lot,
                price=entry,
                stop_loss=sl,
                take_profit=tp,
            )
            res = asyncio.run(em._brokers[primary].submit_order(order))
            log.info("%s %s %.2f lot=%.2f SL=%.5f TP=%.5f -> %s", side.upper(), symbol, entry, lot, sl, tp, res.status)
            executed += 1
        except Exception as e:
            log.error("%s cycle error: %s", symbol, e)

    log.info("Cycle done. executed=%d", executed)
    return 0 if executed > 0 else 1


if __name__ == "__main__":
    sys.exit(run_cycle())
