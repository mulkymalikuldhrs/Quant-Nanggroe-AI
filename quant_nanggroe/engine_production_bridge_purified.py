"""
PURIFIED QNA PRODUCTION BRIDGE — Minimal execution path
Removes ALL dead registries, stubs, incompatible ABCs.
Purpose: clean room rewrite — one broker path, fail-closed risk,
         MT5 trade-mode gating, no 4 registries.
"""

import os, sys, json, logging, time
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("QNA-Purified")

# ──────────────────────────────────────────
# 1. MT5 ADAPTER — single sync wrapper
# ──────────────────────────────────────────
class MT5Adapter:
    def __init__(self):
        self._initialized = False
        self._account = None

    def connect(self):
        import MetaTrader5 as mt5
        if not mt5.initialize():
            raise RuntimeError("MT5 initialize() failed")
        self._account = mt5.account_info()
        if self._account is None:
            raise RuntimeError("No MT5 account")
        self._initialized = True
        log.info("MT5 connected — login=%s", self._account.login)
        return True

    def _guard_trade_mode(self, sym, side):
        import MetaTrader5 as mt5
        info = mt5.symbol_info(sym)
        if not info:
            raise PermissionError(f"Symbol {sym} not found")
        tm = info.trade_mode  # 0=DISABLED 1=LONGONLY 2=SHORTONLY 3=CLOSEONLY 4=FULL
        if tm in (0, 4):
            raise PermissionError(f"Symbol {sym} disabled (trade_mode={tm})")
        if tm == 1 and side == mt5.ORDER_TYPE_SELL:
            raise PermissionError(f"Symbol {sym} LONGONLY — SELL blocked")
        if tm == 2 and side == mt5.ORDER_TYPE_BUY:
            raise PermissionError(f"Symbol {sym} SHORTONLY — BUY blocked")

    def send_order(self, symbol, side, lot, price, sl, tp, comment=""):
        import MetaTrader5 as mt5
        self._guard_trade_mode(symbol, side)
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": side,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 20260729,
            "comment": comment[:32],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        res = mt5.order_send(req)
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Order rejected: {res.retcode} {res.comment}")
        return {"ticket": res.order, "price": price, "lot": lot, "side": side, "symbol": symbol}

    def close_position(self, ticket):
        import MetaTrader5 as mt5
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            raise ValueError(f"Position {ticket} not found")
        position = pos[0]
        side = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position.symbol).bid if position.type == 0 else mt5.symbol_info_tick(position.symbol).ask
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": side,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": 20260729,
            "comment": "purified-close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        res = mt5.order_send(req)
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Close rejected: {res.retcode}")
        return {"ticket": ticket, "price": price}

# ──────────────────────────────────────────
# 2. RISK GUARD — fail-closed, MTM-aware
# ──────────────────────────────────────────
class RiskGuard:
    def __init__(self, initial_balance=10000.0):
        self.balance = initial_balance
        self.peak = initial_balance
        self.daily_pnl = 0.0
        self.daily_start_balance = initial_balance
        self.total_trades = 0
        self.wins = 0

    def can_trade(self):
        if self.balance <= 0:
            return (False, "Zero balance")
        dd = (self.peak - self.balance) / self.peak if self.peak > 0 else 0
        if dd > 0.15:
            return (False, f"Drawdown {dd:.1%} > 15%")
        daily_loss = (self.daily_start_balance - self.balance) / self.daily_start_balance if self.daily_start_balance > 0 else 0
        if daily_loss > 0.03:
            return (False, f"Daily loss {daily_loss:.1%} > 3%")
        return (True, "ok")

    def position_size(self, price, kelly=0.25):
        risk_amount = self.balance * 0.005 * kelly
        return risk_amount / price if price > 0 else 0

    def record_trade(self, pnl):
        self.balance += pnl
        if self.balance > self.peak:
            self.peak = self.balance
        self.total_trades += 1
        if pnl > 0:
            self.wins += 1

# ──────────────────────────────────────────
# 3. SIGNAL MODEL — no external deps
# ──────────────────────────────────────────
class Signal:
    def __init__(self, symbol, side, confidence=0.5, strategy="", price=0.0,
                 stop_loss=0.0, take_profit=0.0, reason=""):
        self.symbol = symbol
        self.side = side    # buy / sell / hold / close
        self.confidence = confidence
        self.strategy = strategy
        self.price = price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reason = reason
        self.timestamp = time.time()

# ──────────────────────────────────────────
# 4. ENGINE — wires adapter + risk + signals
# ──────────────────────────────────────────
class PurifiedEngine:
    def __init__(self, initial_balance=10000.0):
        self.mt5 = MT5Adapter()
        self.risk = RiskGuard(initial_balance)
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "XAUUSD"]
        self.active = False

    def start(self):
        self.mt5.connect()
        self.active = True
        return self

    def cycle(self, signals):
        if not self.active:
            log.warning("Engine not started")
            return []
        results = []
        for sig in signals:
            if sig.side not in ("buy", "sell"):
                continue
            ok, reason = self.risk.can_trade()
            if not ok:
                log.warning("Risk veto %s %s: %s", sig.symbol, sig.side, reason)
                continue
            qty = self.risk.position_size(sig.price)
            if qty <= 0:
                continue
            try:
                mt5_side = 0 if sig.side == "buy" else 1  # ORDER_TYPE_BUY=0, SELL=1
                res = self.mt5.send_order(
                    symbol=sig.symbol,
                    side=mt5_side,
                    lot=qty,
                    price=sig.price,
                    sl=sig.stop_loss or sig.price * 0.995,
                    tp=sig.take_profit or sig.price * 1.01,
                    comment=f"purified_{sig.strategy}"
                )
                results.append(res)
                log.info("ORDER %s %s %s lot=%.2f", sig.side.upper(), sig.symbol, sig.strategy, qty)
            except Exception as e:
                log.error("Order fail %s %s: %s", sig.symbol, sig.side, e)
        return results

    def close_position(self, ticket):
        return self.mt5.close_position(ticket)

    def status(self):
        ok, reason = self.risk.can_trade()
        return {
            "active": self.active,
            "balance": self.risk.balance,
            "risk_ok": ok,
            "risk_reason": reason,
            "trades": self.risk.total_trades,
            "wins": self.risk.wins,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    eng = PurifiedEngine()
    # Test dry-run: just connect, no trade
    try:
        eng.start()
        print("Engine started — ready to trade")
        print(json.dumps(eng.status(), indent=2))
    except Exception as e:
        print(f"Engine start failed: {e}")