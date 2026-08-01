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
    """Thin MT5 wrapper. Paper mode if MT5 unavailable."""

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

    def _guard_trade_mode(self, sym: str, side: str):
        """Block trade_mode 0,4 (disabled). Block LONGONLY→SELL, SHORTONLY→BUY."""
        if not self._initialized or not self._mt5_loaded:
            return  # Paper mode — skip
        mt5 = self._mt5_mod
        info = mt5.symbol_info(sym)
        if not info:
            raise PermissionError(f"Symbol {sym} not found in MT5")
        tm = info.trade_mode  # 0=DISABLED 1=LONGONLY 2=SHORTONLY 3=CLOSEONLY 4=FULL
        if tm in (0, 4):
            raise PermissionError(f"Symbol {sym} disabled (trade_mode={tm})")
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
        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 20260729,
            "comment": comment[:32],
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
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
    """Enforces: balance>0, 15% max DD, 3% daily loss, Kelly sizing."""

    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.peak = initial_balance
        self.daily_pnl = 0.0
        self.daily_start_balance = initial_balance
        self.total_trades = 0
        self.wins = 0
        self.kelly_cache: Dict[str, float] = {}

    def can_trade(self) -> Tuple[bool, str]:
        if self.balance <= 0:
            return (False, "Zero balance")
        dd = (self.peak - self.balance) / self.peak if self.peak > 0 else 0
        if dd > 0.15:
            return (False, f"Drawdown {dd:.1%} > 15%")
        daily_loss = (self.daily_start_balance - self.balance) / self.daily_start_balance \
            if self.daily_start_balance > 0 else 0
        if daily_loss > 0.03:
            return (False, f"Daily loss {daily_loss:.1%} > 3%")
        return (True, "ok")

    def position_size(self, price: float, kelly: float = 0.25) -> float:
        """Calculate position size: 0.5% risk * kelly / price."""
        if price <= 0:
            return 0.0
        risk_amount = self.balance * 0.005 * kelly
        return risk_amount / price

    def update_pnl(self, pnl: float, won: bool):
        """Update balance and stats after a trade."""
        self.balance += pnl
        if self.balance > self.peak:
            self.peak = self.balance
        self.daily_pnl += pnl
        self.total_trades += 1
        if won:
            self.wins += 1

    def reset_daily(self):
        """Reset daily tracking (call at start of new day)."""
        self.daily_start_balance = self.balance
        self.daily_pnl = 0.0


# ──────────────────────────────────────────────────────────────
# 4. PURIFIED ENGINE — wires adapter + risk + signals
# ──────────────────────────────────────────────────────────────
class PurifiedEngine:
    """Single entry point for trading. Fail-closed risk enforcement."""

    def __init__(self, initial_balance: float = 10000.0):
        self.mt5 = MT5Adapter()
        self.risk = RiskGuard(initial_balance)
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "XAUUSD"]
        self.active = False

    def start(self):
        """Connect MT5 (or paper mode)."""
        self.mt5.connect()
        self.active = True
        log.info("Engine started — mode=%s",
                 "MT5" if self.mt5._initialized else "PAPER")
        return self

    def cycle(self, signals: List[Signal]) -> List[dict]:
        """Execute signal batch through risk guard + MT5 adapter."""
        if not self.active:
            log.warning("Engine not started")
            return []

        results = []
        for sig in signals:
            if sig.side not in ("buy", "sell"):
                continue

            # Risk gate — fail-closed
            ok, reason = self.risk.can_trade()
            if not ok:
                log.warning("Risk veto %s %s: %s", sig.symbol, sig.side, reason)
                continue

            # Size position
            kelly = self.risk.kelly_cache.get(sig.strategy, 0.25)
            lot = self.risk.position_size(sig.price, kelly)
            if lot <= 0:
                log.warning("Position size 0 for %s", sig.symbol)
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
            "mt5": "live" if self.mt5._initialized else "paper",
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
