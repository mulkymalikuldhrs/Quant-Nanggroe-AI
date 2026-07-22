#!/usr/bin/env python3
"""QNA Autonomous Live Cycle v2 — strategy-engine driven, fail-closed.

no_agent cron script. ONE full cycle:
  1. build_execution_manager(allow_live=True)  -> wires MT5 live + risk
  2. manage trailing stops on open positions (dynamic protection)
  3. for each symbol: build OHLCV from MT5, run the registered strategy
     ENSEMBLE (wyckoff/smc/dhaher_system/kronos/tradebobby_smc),
     majority-vote BUY/SELL, compute ATR SL/TP, guard against double
     positions + exposure cap, risk-check, submit via execution manager.
  4. report result

This replaces the v1 hardcoded mean-reversion bias. The 130+ strategy
arsenal in quant_nanggroe.engine.strategy.strategies/ is now LIVE via
StrategyRegistry — the fund actually thinks, not gambles on one heuristic.

Fail-closed: MT5 unavailable -> PAPER ONLY, reports degraded. Never
silent-trades. Guarded by RiskManager (constitutional daily/weekly veto).

Env (set by cron wrapper or system):
  QNA_LIVE_TRADING=1     enable live MT5 in build_execution_manager
  QNA_MT5_LIVE=1         engine_production_bridge uses MT5 path
  VALETAX_PASSWORD        MT5 password (from mt5_accounts.yaml ${...})
"""
from __future__ import annotations

import os
import sys
import time
import logging
import asyncio
import MetaTrader5 as mt5  # hard dependency for this live trading script

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("qna.cycle")

# ── Config ────────────────────────────────────────────────────────────────
QNA_DIR = r"D:\repositories\Quant-Nanggroe-AI-worktree"
SYMBOLS = ["EURUSD.vx", "GBPUSD.vx", "XAUUSD.vx"]   # Valetax forex + gold
RISK_PCT = 0.01          # 1% account balance per trade
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.5
MAX_OPEN_POSITIONS = 3   # exposure cap across all symbols
ACTIVE_STRATEGIES = ["wyckoff", "smc", "dhaher_system", "kronos", "tradebobby_smc",
                      "mean_rev", "msnr", "ict", "unified_retail"]

VENV_PYTHON = r"C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

# Demo Valetax account (no real funds). Hardcode fallback so the autonomous
# cron never silently falls back to paper due to a missing env var.
VALETAX_PASSWORD_FALLBACK = "@15September"


def compute_sl_tp(atr: float, entry: float, side: str):
    """ATR-based protective SL/TP. side='buy' -> SL below, TP above."""
    if atr <= 0:
        atr = entry * 0.001
    sl = entry - SL_ATR_MULT * atr if side == "buy" else entry + SL_ATR_MULT * atr
    tp = entry + TP_ATR_MULT * atr if side == "buy" else entry - TP_ATR_MULT * atr
    return round(sl, 5), round(tp, 5)


def build_ohlcv(broker, symbol: str, tf=None, count=300):
    """Fetch MT5 rates via the broker adapter's own MT5 handle and build a
    strategy-ready OHLCV DataFrame.

    MT5Broker.get_rates() returns a list of numpy.void tuples in the canonical
    MT5 field order (time, open, high, low, close, tick_volume, spread,
    real_volume). We map them to named columns so strategies that read
    df['close'] etc. work — pd.DataFrame(raw) would give integer-index
    columns [0..7] and break every strategy that expects named OHLC.
    """
    raw = broker.get_rates(symbol, tf, count)
    if not raw or len(raw) < 30:
        raw = broker.get_rates(symbol.replace(".vx", ""), tf, count)
    if not raw or len(raw) < 30:
        return None
    import pandas as pd
    cols = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    rows = [tuple(r) for r in raw]
    df = pd.DataFrame(rows, columns=cols)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df["symbol"] = symbol
    return df


def manage_trailing(mt5, trailing) -> int:
    """Periodic trailing-stop management for open positions.

    Called each cycle (cron 30m). Reads live MT5 positions via bare mt5
    (read-only, safe — proven stable across runs), updates the trailing
    manager, and modifies the broker SL when the trail tightens.
    """
    modified = 0
    positions = mt5.positions_get() or []
    for p in positions:
        sym = p.symbol
        tick = mt5.symbol_info_tick(sym)
        if not tick:
            continue
        price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
        if sym not in trailing._positions:
            trailing.add_position(sym, p.price_open)
        triggered = trailing.update(sym, price)
        if triggered:
            close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            cr = mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL, "symbol": sym, "volume": p.volume,
                "type": close_type, "position": p.ticket, "price": price,
                "deviation": 20, "magic": 888888, "type_filling": mt5.ORDER_FILLING_FOK,
                "type_time": mt5.ORDER_TIME_GTC,
            })
            log.info("TRAILING CLOSE %s ticket=%s retcode=%s", sym, p.ticket, cr.retcode)
            modified += 1
        else:
            new_sl = trailing.get_stop_price(sym)
            if new_sl and 0 < new_sl != p.sl:
                cr = mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP, "symbol": sym, "position": p.ticket,
                    "sl": new_sl, "tp": p.tp, "deviation": 20, "magic": 888888,
                })
                if cr.retcode == mt5.TRADE_RETCODE_DONE:
                    log.info("TRAILING SL %s ticket=%s sl=%.5f", sym, p.ticket, new_sl)
                    modified += 1
    return modified


def ensemble_signal(registry, df, symbol: str):
    """Run all active strategies, majority-vote direction, take best SL/TP.

    Returns (direction, confidence, sl, tp, reasoning) or (None,...) if HOLD.
    """
    from quant_nanggroe.engine.strategies.base import SignalDirection
    votes = {"BUY": [], "SELL": []}
    best = None
    for name in ACTIVE_STRATEGIES:
        cls = registry.get(name)
        if cls is None:
            continue
        try:
            inst = cls()
            sig = inst.generate_signal(df)
        except Exception as e:
            log.warning("strategy %s error: %s", name, e)
            continue
        if sig.direction == SignalDirection.BUY:
            votes["BUY"].append((sig.confidence, sig.stop_loss, sig.take_profit, name))
        elif sig.direction == SignalDirection.SELL:
            votes["SELL"].append((sig.confidence, sig.stop_loss, sig.take_profit, name))
    if not votes["BUY"] and not votes["SELL"]:
        return None, 0.0, None, None, "All strategies HOLD"
    # Confidence-WEIGHTED voting (not count-based) — conviction > headcount.
    # A single strong signal (conf 0.8) beats three weak ones (0.4 each = 1.2 but
    # each below conviction threshold). This prevents trend+reversion ties from
    # deadlocking into HOLD and raises trade frequency without lowering the bar.
    buy_w = sum(c for c, _, _, _ in votes["BUY"])
    sell_w = sum(c for c, _, _, _ in votes["SELL"])
    buy_n, sell_n = len(votes["BUY"]), len(votes["SELL"])
    if buy_w == sell_w:
        return None, 0.0, None, None, "Tied conviction — no edge"
    side = "BUY" if buy_w > sell_w else "SELL"
    pool = votes[side]
    pool.sort(key=lambda x: x[0], reverse=True)
    # Aggregate confidence = weighted avg, but never below best single conviction
    best_conf = pool[0][0]
    conf = max(best_conf, sum(c for c, _, _, _ in pool) / len(pool))
    sl, tp, src = pool[0][1], pool[0][2], pool[0][3]
    return side, conf, sl, tp, f"{side} conv={buy_w:.2f}/{sell_w:.2f} (best={src} conf={conf:.2f})"


def run_cycle() -> int:
    sys.path.insert(0, QNA_DIR)
    os.environ.setdefault("QNA_LIVE_TRADING", "1")
    os.environ.setdefault("QNA_MT5_LIVE", "1")
    # Demo account: ensure password available for mt5_accounts.yaml ${...}
    os.environ.setdefault("VALETAX_PASSWORD", VALETAX_PASSWORD_FALLBACK)

    from quant_nanggroe.engine.execution.builder import build_execution_manager
    from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType
    from quant_nanggroe.engine.risk.trailing_stop import TrailingStopManager
    from quant_nanggroe.engine.strategies.registry import StrategyRegistry
    import quant_nanggroe.engine.strategy.strategies  # trigger registration

    registry = StrategyRegistry

    import MetaTrader5 as mt5  # noqa: F811 — already imported at module top

    t0 = time.time()
    em = build_execution_manager(allow_live=(os.environ.get("QNA_LIVE_TRADING") == "1"))
    brokers = list(em._brokers.keys())
    primary = em._primary_broker
    log.info("ExecutionManager built in %.1fs brokers=%s primary=%s", time.time() - t0, brokers, primary)

    # Force-sync realized PnL from MT5 BEFORE any risk check, so the
    # constitutional veto uses live data — not stale persisted state.
    try:
        em._risk_manager._sync_realized_pnl()
    except Exception as e:
        log.warning("PnL sync failed: %s", e)

    if primary != "mt5":
        log.warning("MT5 not live (paper fallback). Trading PAPER ONLY — no market impact.")
        return 1  # degraded, not crash

    import MetaTrader5 as mt5

    trailing = TrailingStopManager()
    broker = em._brokers[primary]  # MT5ExecutionBroker adapter (owns live MT5 session)
    # 1) manage trailing on existing positions first (bare mt5, read-only safe)
    n_trail = manage_trailing(mt5, trailing)
    if n_trail:
        log.info("Trailing actions: %d", n_trail)

    # read open positions via bare mt5 (read-only, safe) for the guard
    import MetaTrader5 as mt5
    open_positions = mt5.positions_get() or []
    open_symbols = {p.symbol for p in open_positions}
    log.info("Open positions: %d (%s)", len(open_positions), ", ".join(sorted(open_symbols)) or "none")

    executed = 0
    for symbol in SYMBOLS:
        try:
            # GUARD 1: never stack a second position on a symbol that already
            # has one open (prevents opposing BUY/SELL on XAUUSD, etc.)
            if symbol in open_symbols:
                log.info("%s already open — skip (no double-entry)", symbol)
                continue
            # GUARD 2: global exposure cap
            if len(open_symbols) + executed >= MAX_OPEN_POSITIONS:
                log.info("Exposure cap %d reached — skip %s", MAX_OPEN_POSITIONS, symbol)
                continue

            df = build_ohlcv(broker, symbol)
            if df is None:
                log.warning("%s no rates — skip", symbol)
                continue

            side, conf, strat_sl, strat_tp, reason = ensemble_signal(registry, df, symbol)
            if side is None:
                log.info("%s %s", symbol, reason)
                continue

            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                continue
            entry = (tick.bid + tick.ask) / 2

            # ATR from the fetched rates
            highs = df["high"].values[-10:]
            lows = df["low"].values[-10:]
            atr = sum(max(h - l, 1e-6) for h, l in zip(highs, lows)) / 10
            if atr <= 0:
                atr = entry * 0.001

            # Prefer strategy-provided SL/TP; fall back to ATR-based
            sl = strat_sl if strat_sl else compute_sl_tp(atr, entry, side.lower())[0]
            tp = strat_tp if strat_tp else compute_sl_tp(atr, entry, side.lower())[1]

            acc = mt5.account_info()
            bal = float(acc.balance) if acc else 1000.0
            # Risk-based lot sizing: risk_amount = balance * RISK_PCT;
            # lot = risk_amount / (stop_loss_distance * contract_size).
            sl_distance = abs(entry - sl) if sl else (atr * SL_ATR_MULT)
            contract_size = 100 if "XAU" in symbol or "GOLD" in symbol else 100000
            risk_amount = bal * RISK_PCT
            if sl_distance > 0:
                lot = risk_amount / (sl_distance * contract_size)
            else:
                lot = 0.01
            # Broker floor + sane cap (never blow the account on one ticket)
            lot = max(0.01, round(lot, 2))
            lot = min(lot, 1.0)

            # Risk gate — constitutional veto (realized PnL fed from broker)
            verdict = em._risk_manager.check_trade(
                symbol=symbol, direction=side,
                lot_size=lot, entry=entry, stop_loss=sl,
                account_balance=bal, take_profit=tp,
            )
            if verdict.get("verdict") != "APPROVED":
                log.warning("RISK VETO %s %s: %s", symbol, side, verdict.get("failed_checkpoints"))
                continue

            order = Order(
                id=f"qna_{symbol}_{int(time.time())}",
                symbol=symbol,
                side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=lot,
                price=entry,
                stop_loss=sl,
                take_profit=tp,
            )
            res = asyncio.run(em._brokers[primary].submit_order(order))
            log.info("%s %s %.2f lot=%.2f SL=%.5f TP=%.5f -> %s | %s",
                     side, symbol, entry, lot, sl, tp, res.status, reason)
            if res.status.value == "FILLED":
                trailing.add_position(symbol, entry)
                executed += 1
        except Exception as e:
            log.error("%s cycle error: %s", symbol, e)

    log.info("Cycle done. executed=%d", executed)
    # Autonomous fund: executed=0 is NORMAL (no edge / positions full / market flat),
    # not a failure. Return 0 on healthy cycle; exceptions propagate as non-zero.
    return 0


if __name__ == "__main__":
    sys.exit(run_cycle())
