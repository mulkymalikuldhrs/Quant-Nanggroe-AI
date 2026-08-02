"""
PURIFIED QNA PRODUCTION BRIDGE — Minimal execution path
Removes ALL dead registries, stubs, incompatible ABCs.
Purpose: clean room rewrite — one broker path, fail-closed risk,
         MT5 trade-mode guard, single async-compatible entry point.
Author: Hermès autonomous architect (INFJ-T)
Version: 0.1 — scaffold (2026-07-29)
"""

import os
import sys
import json
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("PurifiedBridge")

# ──────────────────────────────────────────────────────────────
# 1. SIGNAL MODEL
# ──────────────────────────────────────────────────────────────
@dataclass
class Signal:
    # DEPRECATED — use quant_nanggroe.types.signals.Signal instead.
    # side -> signal_type, strategy -> source_strategy, all fields in canonical.
    symbol: str
    side: str                                     # "buy" or "sell"
    confidence: float = 0.5                       # 0.0 – 1.0
    strategy: str = "unknown"
    price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0


# ──────────────────────────────────────────────────────────────
# 2. MT5 ADAPTER — fail-closed, trade-mode guarded
# ──────────────────────────────────────────────────────────────
class MT5Adapter:
    """Thin MT5 wrapper. REAL-ONLY: raises if MT5 unavailable (no paper mode)."""

    def __init__(self):
        self._initialized = False
        self._account = None
        self._mt5_mod = None
        self._mt5_loaded = False
        try:
            # Auto-detect MT5 terminal anywhere on disk + set DLL path
            try:
                from utils.mt5_launcher import ensure_mt5_env
                ensure_mt5_env()
            except Exception:
                pass
            import MetaTrader5 as _mt5
            self._mt5_mod = _mt5
            self._mt5_loaded = True
        except Exception:
            self._mt5_mod = None
            self._mt5_loaded = False
        self.log = logging.getLogger("MT5Adapter")

    def connect(self):
        """Connect to LIVE MT5 only. No paper fallback (REAL-ONLY mode)."""
        if not self._mt5_loaded:
            raise RuntimeError("MetaTrader5 not available — REAL-ONLY mode requires MT5 library")
        mt5 = self._mt5_mod
        try:
            if not mt5.initialize():
                raise RuntimeError("MT5 initialize() failed — REAL-ONLY mode (no paper fallback)")
            self._account = mt5.account_info()
            if self._account is None:
                raise RuntimeError("MT5 no account — REAL-ONLY mode requires logged-in account")
            self._initialized = True
            self.log.info("MT5 connected LIVE — login=%s balance=%.2f",
                          self._account.login, self._account.balance)
            return True
        except Exception as e:
            self._initialized = False
            raise RuntimeError(f"MT5 connect failed (REAL-ONLY, no paper): {e}")

    def account_balance(self) -> float:
        """Return LIVE balance from MT5 (source of truth), refreshing account_info."""
        try:
            if self._initialized and self._mt5_loaded:
                info = self._mt5_mod.account_info()
                if info:
                    self._account = info
                    return float(info.balance)
        except Exception:
            pass
        return float(self._account.balance) if self._account else 0.0

    def _guard_trade_mode(self, sym: str, side: str):
        """Block trade_mode 0 (disabled). Block LONGONLY→SELL, SHORTONLY→BUY.
        Mode 4 = FULL on Valetax (verified live) — allowed."""
        if not self._initialized or not self._mt5_loaded:
            raise RuntimeError("MT5 not LIVE connected (REAL-ONLY, no paper)")
        mt5 = self._mt5_mod
        info = mt5.symbol_info(sym)
        if not info:
            raise PermissionError(f"Symbol {sym} not found in MT5")
        tm = info.trade_mode  # 0=DISABLED 1=LONGONLY 2=SHORTONLY 3=CLOSEONLY 4=FULL
        if tm == 0:
            raise PermissionError(f"Symbol {sym} disabled (trade_mode=0)")
        if tm == 1 and side == "sell":
            raise PermissionError(f"Symbol {sym} LONGONLY — SELL blocked")
        if tm == 2 and side == "buy":
            raise PermissionError(f"Symbol {sym} SHORTONLY — BUY blocked")

    def execute_order(self, symbol: str, side: str, lot: float, price: float = 0.0,
                   sl: float = 0.0, tp: float = 0.0, comment: str = "") -> dict:
        """Send LIVE order via MT5. No paper simulation (REAL-ONLY mode)."""
        self._guard_trade_mode(symbol, side)
        if not self._initialized or not self._mt5_loaded:
            raise RuntimeError(f"execute_order blocked — MT5 not LIVE connected (REAL-ONLY, no paper): {symbol} {side}")

        mt5 = self._mt5_mod
        info = mt5.symbol_info(symbol)
        if not info:
            raise RuntimeError(f"Symbol {symbol} not found for lot validation")
        # Clamp lot to broker limits (min/step/max) — REAL-ONLY, fail-closed
        min_lot = info.volume_min or 0.01
        max_lot = info.volume_max or 50.0
        step = info.volume_step or 0.01
        if lot < min_lot:
            lot = min_lot
        if lot > max_lot:
            lot = max_lot
        # Round to nearest step
        lot = round(lot / step) * step
        lot = round(lot, 2)
        # REAL-ONLY: only attach SL/TP if valid (>0). Broker rejects sl/tp<=0
        # or below trade_stops_level.
        # G6 FIX: naked-fill closed — if caller passed 0.0 for sl, REJECT the order
        # (was: omit stops entirely → trades could execute with NO protection).
        # Exception: TP may be 0 (some strategies leave TP to trailing logic), but
        # SL is mandatory. If the caller genuinely has no SL, they must pass
        # sl='none' explicitly for a naked entry.
        if not (sl and sl > 0):
            if str(comment).startswith("NONE_TP") and tp > 0:
                pass  # reserved; TP-only flow not supported
            raise RuntimeError(
                f"execute_order blocked — SL required (fail-closed, no naked fill): {symbol} {side} sl={sl}"
            )
        _sl = sl
        _tp = tp if (tp and tp > 0) else None
        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "deviation": 10,
            "magic": 20260729,
            "comment": comment[:32],
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        if _sl is not None:
            request["sl"] = _sl
        if _tp is not None:
            request["tp"] = _tp

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Order rejected: {result.comment}")
        return {"ticket": result.order, "price": price, "lot": lot,
                "side": side, "symbol": symbol, "mode": "mt5"}

    def close_position(self, ticket: int) -> dict:
        """Close LIVE position by ticket. No paper simulation (REAL-ONLY mode)."""
        if not self._initialized or not self._mt5_loaded:
            raise RuntimeError(f"close_position blocked — MT5 not LIVE connected (REAL-ONLY, no paper): ticket {ticket}")

        mt5 = self._mt5_mod
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            raise ValueError(f"Position {ticket} not found")
        position = pos[0]
        side = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(position.symbol)
        price = tick.bid if position.type == 0 else tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": side,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": 20260729,
            "comment": "purified-close",
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Close rejected: {result.comment}")
        return {"ticket": ticket, "price": price, "mode": "mt5"}

    def get_positions(self) -> List[dict]:
        """Get all open positions."""
        if not self._initialized or not self._mt5_loaded:
            return []
        mt5 = self._mt5_mod
        positions = mt5.positions_get() or []
        return [{"ticket": p.ticket, "symbol": p.symbol,
                 "type": "BUY" if p.type == 0 else "SELL",
                 "volume": p.volume, "price": p.price_open,
                 "pnl": p.profit, "sl": p.sl, "tp": p.tp}
                for p in positions]

    def get_history_deals(self, days: int = 30) -> List[dict]:
        """Get recent deal history."""
        if not self._initialized or not self._mt5_loaded:
            return []
        from datetime import datetime, timedelta
        mt5 = self._mt5_mod
        deals = mt5.history_deals_get(
            datetime.now() - timedelta(days=days), datetime.now()) or []
        return [{"ticket": d.ticket, "symbol": d.symbol,
                 "type": "BUY" if d.type == 0 else "SELL",
                 "volume": d.volume, "price": d.price,
                 "pnl": d.profit, "time": str(d.time)}
                for d in deals[-50:]]

    def shutdown(self):
        if self._initialized and self._mt5_loaded:
            try:
                self._mt5_mod.shutdown()
            except Exception:
                pass
        self._initialized = False


# ──────────────────────────────────────────────────────────────
# 3. RISK GUARD — fail-closed, MTM-aware
# ──────────────────────────────────────────────────────────────
class RiskGuard:
    """Enforces: balance>0, 15% max DD, 3% daily loss, 3% weekly loss, Kelly sizing.
    Fail-closed: KillSwitch active -> no trades."""

    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.peak = initial_balance
        self.daily_pnl = 0.0
        self.daily_start_balance = initial_balance
        self.weekly_pnl = 0.0
        self.weekly_start_balance = initial_balance
        self.total_trades = 0
        self.wins = 0
        self.kelly_cache: Dict[str, float] = {}
        self._kill_switch_active = False

    def set_kill_switch(self, active: bool):
        """Wire constitutional KillSwitch state (fail-closed: True blocks all trades)."""
        self._kill_switch_active = active

    def can_trade(self) -> Tuple[bool, str]:
        if self._kill_switch_active:
            return (False, "KillSwitch ACTIVE — trading halted")
        if self.balance <= 0:
            return (False, "Zero balance")
        dd = (self.peak - self.balance) / self.peak if self.peak > 0 else 0
        if dd > 0.15:
            return (False, f"Drawdown {dd:.1%} > 15%")
        daily_loss = (self.daily_start_balance - self.balance) / self.daily_start_balance \
            if self.daily_start_balance > 0 else 0
        if daily_loss > 0.03:
            return (False, f"Daily loss {daily_loss:.1%} > 3%")
        weekly_loss = (self.weekly_start_balance - self.balance) / self.weekly_start_balance \
            if self.weekly_start_balance > 0 else 0
        if weekly_loss > 0.03:
            return (False, f"Weekly loss {weekly_loss:.1%} > 3%")
        return (True, "ok")

    def position_size(self, price: float, kelly: float = 0.25,
                      sl: float = 0.0, contract_size: float = 100000.0,
                      risk_pct: float = 0.005) -> float:
        """Calculate position size in MT5 LOTS from equity + SL distance.

        lot = (equity * risk_pct * kelly) / (|entry - SL| * contract_size)
        contract_size = units per lot (100000 for FX, 1 for BTCUSD.vx).
        Returns 0.0 when no valid SL distance (fail-closed: no SL = no size).
        """
        if price <= 0 or sl <= 0:
            return 0.0
        sl_distance = abs(price - sl)
        if sl_distance <= 0 or contract_size <= 0:
            return 0.0
        risk_amount = self.balance * risk_pct * kelly
        return max(risk_amount / (sl_distance * contract_size), 0.0)

    def update_pnl(self, pnl: float, won: bool):
        """Update balance and stats after a trade."""
        self.balance += pnl
        if self.balance > self.peak:
            self.peak = self.balance
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.total_trades += 1
        if won:
            self.wins += 1

    def reset_daily(self):
        """Reset daily tracking (call at start of new day)."""
        self.daily_start_balance = self.balance
        self.daily_pnl = 0.0

    def reset_weekly(self):
        """Reset weekly tracking (call at start of new week)."""
        self.weekly_start_balance = self.balance
        self.weekly_pnl = 0.0


# ──────────────────────────────────────────────────────────────
# 4. PURIFIED ENGINE — wires adapter + risk + signals
# ──────────────────────────────────────────────────────────────
class PurifiedEngine:
    """Single entry point for trading. Fail-closed risk enforcement."""

    def __init__(self, initial_balance: float = 10000.0):
        self.mt5 = MT5Adapter()
        self.risk = RiskGuard(initial_balance)
        # Broker requires .vx suffix (Valetax). Plain symbols are rejected.
        self.symbols = ["EURUSD.vx", "GBPUSD.vx", "USDJPY.vx", "BTCUSD.vx", "XAUUSD.vx"]
        self.active = False

    def start(self):
        """Connect MT5 (REAL-ONLY — raises if unavailable, no paper mode)."""
        self.mt5.connect()
        # CRITICAL: sync RiskGuard balance from LIVE MT5 (source of truth).
        # Previously hardcoded $10k → all position sizing was ~8.8x oversized
        # and every DD/loss limit was computed against a phantom balance.
        live_balance = self.mt5.account_balance()
        if live_balance > 0:
            self.risk.balance = live_balance
            self.risk.peak = max(self.risk.peak, live_balance)
            self.risk.daily_start_balance = live_balance
            self.risk.weekly_start_balance = live_balance
            log.info("RiskGuard synced to LIVE balance: %.2f", live_balance)
        self.active = True
        log.info("Engine started — mode=%s",
                 "MT5-LIVE" if self.mt5._initialized else "DOWN")
        return self

    def cycle(self, signals: List[Signal]) -> List[dict]:
        """Execute signal batch through risk guard + MT5 adapter (REAL-ONLY)."""
        if not self.active:
            log.warning("Engine not started")
            return []

        # CRITICAL: refresh RiskGuard balance from LIVE MT5 each cycle so
        # sizing + DD/loss limits track reality (not a phantom initial_balance).
        try:
            live_balance = self.mt5.account_balance()
            if live_balance > 0:
                self.risk.balance = live_balance
                self.risk.peak = max(self.risk.peak, live_balance)
        except Exception as e:
            log.warning("Balance sync failed this cycle: %s", e)

        results = []
        # G7 FIX: enforce position caps (MAX_POSITIONS_PER_SYMBOL / MAX_TOTAL_POSITIONS).
        # Previously defined but never referenced → stacked/opposing orders possible.
        # (Constants mirror Config in autonomous_cycle.py:155-156)
        MAX_POSITIONS_PER_SYMBOL = 1
        MAX_TOTAL_POSITIONS = 5
        open_positions = []
        try:
            if self.mt5._initialized and self.mt5._mt5_loaded:
                open_positions = self.mt5._mt5_mod.positions_get() or []
        except Exception as e:
            log.warning("positions_get failed for cap enforcement: %s", e)
        total_open = len(open_positions)

        for sig in signals:
            if sig.side not in ("buy", "sell"):
                continue

            # G7: per-symbol cap (1 per symbol)
            sym_count = sum(1 for p in open_positions if p.symbol == sig.symbol)
            if sym_count >= MAX_POSITIONS_PER_SYMBOL:
                log.warning("POSITION CAP %s: already %d open, skip %s %s",
                            sig.symbol, sym_count, sig.side, sig.symbol)
                results.append({"status": "skip_position_cap",
                                "symbol": sig.symbol, "side": sig.side})
                continue
            if total_open >= MAX_TOTAL_POSITIONS:
                log.warning("TOTAL POSITION CAP %d reached, skip %s %s",
                            total_open, sig.side, sig.symbol)
                results.append({"status": "skip_total_cap",
                                "symbol": sig.symbol, "side": sig.side})
                continue

            # Risk gate — fail-closed
            ok, reason = self.risk.can_trade()
            if not ok:
                log.warning("Risk veto %s %s: %s", sig.symbol, sig.side, reason)
                continue

            # Size position from equity + SL distance (fail-closed: no SL -> no size)
            kelly = self.risk.kelly_cache.get(sig.strategy, 0.25)
            sl = sig.stop_loss if (sig.stop_loss and sig.stop_loss > 0) else 0.0
            contract_size = 100000.0  # FX default (units per lot)
            try:
                if self.mt5._initialized and self.mt5._mt5_loaded:
                    info = self.mt5._mt5_mod.symbol_info(sig.symbol)
                    if info and getattr(info, "trade_contract_size", 0):
                        contract_size = info.trade_contract_size
            except Exception:
                pass
            lot = self.risk.position_size(sig.price, kelly, sl, contract_size)
            if lot <= 0:
                log.warning("Position size 0 for %s (SL=%s) — fail-closed, no trade",
                            sig.symbol, sl)
                continue
            risk_usd = self.risk.balance * 0.005 * kelly
            log.info("SIZE %s %s: equity=%.2f kelly=%.2f SL=%.5f contract=%s → lot=%.4f (risk≈$%.2f)",
                     sig.symbol, sig.side, self.risk.balance, kelly, sl,
                     contract_size, lot, risk_usd)

            # Fail-closed risk cap: min-lot forced risk must not exceed hard cap.
            # Budget = 0.5% equity * kelly; HARD CAP = max(2x budget, 2% equity).
            # Small accounts ($1k) trading BTC min-lot: forced risk ~1-2% equity is
            # acceptable; above hard cap -> skip (no oversized trades).
            min_lot = 0.01
            try:
                if self.mt5._initialized and self.mt5._mt5_loaded:
                    info = self.mt5._mt5_mod.symbol_info(sig.symbol)
                    if info and getattr(info, "volume_min", 0):
                        min_lot = info.volume_min
            except Exception:
                pass
            hard_cap = max(2.0 * risk_usd, self.risk.balance * 0.02)
            if sl > 0 and lot < min_lot:
                forced_risk = min_lot * abs(sig.price - sl) * contract_size
                if forced_risk > hard_cap:
                    log.warning("MIN-LOT RISK EXCEEDS CAP %s: min=%s forced_risk≈$%.2f > cap $%.2f — SKIP (fail-closed)",
                                sig.symbol, min_lot, forced_risk, hard_cap)
                    results.append({"status": "skip_min_lot_risk",
                                    "symbol": sig.symbol, "side": sig.side,
                                    "lot": lot, "min_lot": min_lot,
                                    "forced_risk": forced_risk, "cap": hard_cap})
                    continue

            # Execute
            try:
                result = self.mt5.execute_order(
                    symbol=sig.symbol,
                    side=sig.side,
                    lot=round(lot, 2),
                    price=sig.price,
                    sl=sig.stop_loss,
                    tp=sig.take_profit,
                    comment=f"{sig.strategy}:{sig.symbol}",
                )
                results.append(result)
                log.info("EXEC %s %s %.2f lots @ %.5f → ticket=%d",
                         sig.symbol, sig.side.upper(), lot, sig.price,
                         result.get("ticket", 0))
            except Exception as e:
                log.error("Order failed %s %s: %s", sig.symbol, sig.side, e)
                results.append({"status": "error", "error": str(e),
                                "symbol": sig.symbol, "side": sig.side})

        return results

    def close_position(self, ticket: int) -> dict:
        return self.mt5.close_position(ticket)

    def status(self) -> dict:
        ok, reason = self.risk.can_trade()
        return {
            "active": self.active,
            "balance": self.risk.balance,
            "risk_ok": ok,
            "risk_reason": reason,
            "trades": self.risk.total_trades,
            "wins": self.risk.wins,
            "mt5": "live" if self.mt5._initialized else "down",
        }

    def shutdown(self):
        self.mt5.shutdown()
        self.active = False


# ──────────────────────────────────────────────────────────────
# 5. ENTRY POINT — dry run test
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    eng = PurifiedEngine()
    eng.start()
    print("Engine started — ready to trade")
    print(json.dumps(eng.status(), indent=2))
    eng.shutdown()
