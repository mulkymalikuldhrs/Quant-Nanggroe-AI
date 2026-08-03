"""Live MT5 broker connector (Exness/Valutrades). Fail-closed: no terminal -> raise, never silent.
Reuses BrokerConnector ABC + Order/Position from broker_base. Symbol map: BTC-USD -> BTCUSD.

ACTIVE IMPLEMENTATION — This is the broker used by the engine execution layer.
The exchange-layer adapter at quant_nanggroe/exchange/mt5_broker.py provides
the ExchangeInterface abstraction (async, Pydantic models) for external consumers.
"""
from typing import List

from quant_nanggroe.connectors.broker_base import BrokerConnector, BrokerType, Order, Position


def _mt5_symbol(qna_symbol: str) -> str:
    # ponytail: yfinance BTC-USD -> MT5 BTCUSD; forex EUR-USD -> EURUSD
    # Keep suffix case (Valetax uses lowercase ".vx", e.g. EURUSD.vx) — .upper()
    # breaks symbol_select. Only strip dashes and upper-case the base part.
    s = qna_symbol.replace("-", "")
    if "." in s:
        base, ext = s.split(".", 1)
        return base.upper() + "." + ext  # ext kept as-is (vx, not VX)
    return s.upper()


class MT5Broker(BrokerConnector):
    def __init__(self, login: int = 0, password: str = "", server: str = "", magic: int = 888888):
        self.login = login
        self.password = password
        self.server = server
        self.magic = magic
        self._mt5 = None
        self.connected = False

    def connect(self) -> bool:
        try:
            import MetaTrader5 as mt5  # ponytail: only dep; pip install MetaTrader5
        except ImportError:
            raise RuntimeError("MetaTrader5 lib missing — pip install MetaTrader5")
        self._mt5 = mt5
        # P0 fix: add explicit timeout + terminal path so a slow/unresponsive
        # Valetax terminal cannot hang the entire build_execution_manager() call.
        # mt5.initialize without `path` can hang on some installs (terminal not
        # found via registry) — pass the known terminal path explicitly.
        import os as _os
        term_path = _os.environ.get("MT5_TERMINAL_PATH") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
        # retry=3 survives transient IPC timeouts; timeout=15000ms bounds each try.
        for attempt in range(3):
            try:
                ok = mt5.initialize(
                    path=term_path,
                    login=self.login,
                    password=self.password,
                    server=self.server,
                    timeout=15000,
                )
                if ok:
                    self.connected = True
                    return True
                err = mt5.last_error()
                if isinstance(err, (tuple, list)) and err and err[0] == -10005:
                    # -10005 IPC timeout — transient, retry after brief pause
                    import time as _t
                    _t.sleep(1.5 * (attempt + 1))
                    continue
                raise RuntimeError(f"MT5 init failed: {err}")  # ponytail: fail-closed, no silent paper fallback
            except RuntimeError:
                raise
            except Exception as e:  # unexpected — fail closed
                raise RuntimeError(f"MT5 init exception: {e}")
        raise RuntimeError("MT5 init failed after retries: IPC timeout")

    _TRANSIENT_RETCODES = {"TRADE_RETCODE_REQUOTE", "TRADE_RETCODE_TIMEOUT"}

    def place_order(self, order: Order) -> str:
        if not self.connected:
            raise RuntimeError("not connected")
        sym = _mt5_symbol(order.symbol)
        if not self._mt5.symbol_select(sym, True):
            raise RuntimeError(f"MT5 symbol unavailable: {sym}")

        req = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": sym,
            "volume": float(order.quantity),
            "type": self._mt5.ORDER_TYPE_BUY if order.side == "buy" else self._mt5.ORDER_TYPE_SELL,
            "deviation": 20,
            "magic": self.magic,
            "type_filling": self._mt5.ORDER_FILLING_FOK,
            "type_time": self._mt5.ORDER_TIME_GTC,
        }
        # G12: broker comment carries strategy attribution (auditable in MT5 terminal)
        _comment = order.notes or (order.strategy_name or "qna")
        if _comment:
            req["comment"] = str(_comment)[:32]
        # R7 FIX (2026-08-04, 7/7 council + user GO): fail-closed — never place a
        # naked order without SL/TP. Reject outright if missing/invalid.
        if order.stop_loss is None or float(order.stop_loss) <= 0:
            raise RuntimeError(
                f"MT5Broker.blocked — SL required (no naked fill): {order.symbol} {order.side}"
            )
        req["sl"] = float(order.stop_loss)
        if order.take_profit is None or float(order.take_profit) <= 0:
            raise RuntimeError(
                f"MT5Broker.blocked — TP required (no naked fill): {order.symbol} {order.side}"
            )
        req["tp"] = float(order.take_profit)

        max_retries = 2
        last_error = None
        for attempt in range(max_retries):
            # Refresh tick price on each attempt (requote = stale price)
            tick = self._mt5.symbol_info_tick(sym)
            if tick is None:
                raise RuntimeError(f"no tick for {sym}")
            req["price"] = tick.ask if order.side == "buy" else tick.bid

            res = self._mt5.order_send(req)
            if res.retcode == self._mt5.TRADE_RETCODE_DONE:
                return str(res.order)

            last_error = res
            retcode_name = getattr(res, "retcode_name", str(res.retcode))
            if retcode_name in self._TRANSIENT_RETCODES or res.retcode in (10009, 10013):
                import time as _t
                _t.sleep(1.0 * (attempt + 1))
                continue
            break

        code = getattr(last_error, "retcode", "unknown") if last_error else "unknown"
        comment = getattr(last_error, "comment", "") if last_error else ""
        raise RuntimeError(f"MT5 order failed after retries: retcode={code} comment={comment}")

    def get_positions(self) -> List[Position]:
        if not self.connected:  # ponytail: fail-closed, consistent with get_balance/place_order
            raise RuntimeError("not connected")
        out = []
        for p in self._mt5.positions_get() or []:
            out.append(Position(
                symbol=p.symbol, quantity=p.volume, entry_price=p.price_open,
                current_price=p.price_current, pnl=p.profit, broker=BrokerType.MT5.value))
        return out

    def get_balance(self) -> float:
        if not self.connected:  # ponytail: fail-closed, consistent with get_balance/place_order
            raise RuntimeError("not connected")
        acc = self._mt5.account_info()
        return float(acc.balance) if acc else 0.0

    def history_deals_get(self, from_dt, to_dt):
        """P0 fix: expose MT5 realized-deal history so RiskManager can read REAL
        daily/weekly P&L (closes the phantom-veto hole). Returns list of deals
        with `.profit` attribute, or empty list on failure."""
        if not self.connected or self._mt5 is None:
            return []
        try:
            # MT5 expects (from, to) as datetime tuples
            deals = self._mt5.history_deals_get(from_dt, to_dt)
            return list(deals) if deals else []
        except Exception:
            return []

    def get_rates(self, symbol: str, timeframe: int = None, count: int = 200):
        """Fetch OHLCV bars via the broker's own MT5 handle.

        Routes through self._mt5 (the session the broker initialized) to avoid
        the 'copy_rates_from_pos returned exception set' C-API corruption that
        happens when the cycle imports MetaTrader5 as a second bare module and
        calls copy_rates after the broker already initialized the terminal.
        Returns a list of rate tuples or empty list on failure.
        """
        if not self.connected or self._mt5 is None:
            return []
        tf = timeframe if timeframe is not None else self._mt5.TIMEFRAME_M15
        try:
            raw = self._mt5.copy_rates_from_pos(symbol, tf, 0, count)
            return list(raw) if raw is not None else []
        except Exception:
            return []

    def get_equity(self) -> float:
        """P0 fix: real equity (not balance) for risk/MTM calculations."""
        if not self.connected:
            raise RuntimeError("not connected")
        acc = self._mt5.account_info()
        return float(acc.equity) if acc else 0.0

    def disconnect(self):
        if self._mt5:
            self._mt5.shutdown()
        self.connected = False


if __name__ == "__main__":
    # ponytail: self-check — fails fast if no terminal (expected in CI/headless)
    b = MT5Broker()
    assert hasattr(b, "connect") and hasattr(b, "place_order")
    assert _mt5_symbol("BTC-USD") == "BTCUSD" and _mt5_symbol("EUR-USD") == "EURUSD"
    try:
        b.connect()
        print("MT5 connected, balance:", b.get_balance())
    except RuntimeError as e:
        print("self-check OK (fail-closed):", e)
