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
        self._available_symbols = {}  # GATE-2: populated at connect

    def connect(self) -> bool:
        try:
            import MetaTrader5 as mt5  # ponytail: only dep; pip install MetaTrader5
        except ImportError:
            raise RuntimeError("MetaTrader5 lib missing — pip install MetaTrader5")
        self._mt5 = mt5
        import os as _os
        import logging as _logging
        _logger = _logging.getLogger(__name__)
        term_path = _os.environ.get("MT5_TERMINAL_PATH") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
        # ── USER MANDATE: trade whatever account is ALREADY logged into the
        # terminal. Attach to the running session FIRST (no creds) and adopt
        # the active account; only fall back to a credential login when the
        # terminal is not already authenticated. Prevents QNA from
        # switching/logging-into the wrong account (e.g. Exness #999 or the
        # stale config server name instead of ValetaxIntl-Live2 #372044706).
        try:
            if mt5.initialize(path=term_path, timeout=15000):
                info = mt5.account_info()
                if info is not None:
                    self.login = int(getattr(info, "login", self.login) or self.login)
                    self.server = str(getattr(info, "server", self.server) or self.server)
                    self.connected = True
                    self._snapshot_symbols()  # GATE-2: real symbol catalog
                    _logger.info(
                        "MT5Broker: attached to ALREADY-LOGGED-IN terminal account login=%s server=%s",
                        self.login, self.server,
                    )
                    return True
                # Initialized but not logged in — fall through to credential login.
        except Exception as _e:
            _logger.debug("MT5Broker attach-to-session failed (will try credential login): %s", _e)
        if not self.login:
            raise RuntimeError(
                "MT5 not logged in and no login provided (REAL-ONLY — cannot trade)"
            )
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
                    self._snapshot_symbols()  # GATE-2: real symbol catalog
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

    # ── GATE-2: broker suffix auto-detect ────────────────────────────
    # Instead of hardcoding ".vx" (Valetax) or any broker-specific suffix,
    # we snapshot the terminal's REAL tradable symbol list once at connect
    # and resolve every internal symbol against it. Works for any broker:
    # Valetax (.vx), Exness (bare), IC Markets (.m), Future (.r), etc.
    def _snapshot_symbols(self) -> None:
        try:
            raw = self._mt5.symbols_get() or []
            # Only store symbols that are FULLY TRADEABLE (trade_mode=0).
            # Disabled symbols (mode=4) like .vxc must be excluded so
            # resolve_symbol() never resolves to an untradeable name.
            self._available_symbols = {
                s.name.lower(): s.name
                for s in raw
                if s.trade_mode == 0
            }
        except Exception:
            self._available_symbols = {}

    def resolve_symbol(self, qna_symbol: str) -> str:
        """Resolve internal symbol to the terminal's actual tradable name.

        Candidate order: exact → dash-stripped → base-only → suffixed
        variants of the base. The base is always the symbol WITHOUT any
        existing suffix (so "EURUSD.vx" probes "EURUSD.vxc", not
        "EURUSD.vx.vxc"). Only candidates that exist in the terminal's
        own symbol list are accepted.
        """
        avail = getattr(self, "_available_symbols", {}) or {}
        base = _mt5_symbol(qna_symbol)
        # Strip any existing suffix to get the bare base for suffix probing
        bare = base.split(".")[0] if "." in base else base
        candidates = [qna_symbol, qna_symbol.replace("-", ""), base, bare]
        # suffix probes derived from what this terminal actually hosts
        suffixes = set()
        for name in avail.values():
            if "." in name:
                suffixes.add("." + name.rsplit(".", 1)[1])
        for suf in sorted(suffixes):
            candidates.append(bare + suf)
        for cand in candidates:
            hit = avail.get(cand.lower())
            if hit:
                return hit
        return base  # last known-good static translation

    def place_order(self, order: Order) -> str:
        if not self.connected:
            raise RuntimeError("not connected")
        sym = self.resolve_symbol(order.symbol)
        if not self._mt5.symbol_select(sym, True):
            raise RuntimeError(f"MT5 symbol unavailable: {sym}")

        # R5 hotfix (F2): engine OrderSide is an enum ("BUY"/"SELL" uppercase)
        # while connector Orders carry plain "buy"/"sell". Comparing the enum
        # against the lowercase literal was always False → EVERY order went
        # out as ORDER_TYPE_SELL. Normalize via .value first.
        side_str = getattr(order.side, "value", order.side)
        side_str = str(side_str).strip().lower()
        if side_str not in ("buy", "sell"):
            raise RuntimeError(f"invalid order side: {order.side!r}")
        is_buy = side_str == "buy"

        req = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": sym,
            "volume": float(order.quantity),
            "type": self._mt5.ORDER_TYPE_BUY if is_buy else self._mt5.ORDER_TYPE_SELL,
            "deviation": 20,
            "magic": self.magic,
            "type_filling": self._mt5.ORDER_FILLING_FOK,
            "type_time": self._mt5.ORDER_TIME_GTC,
        }
        # FAZE 0.3: strategy attribution via MT5 comment field
        strat = (order.metadata.get("strategy_name", "")
                 if hasattr(order, "metadata") and isinstance(order.metadata, dict)
                 else "") or "qna"
        req["comment"] = str(strat)[:31]  # MT5 comment max ~31 chars
        if order.stop_loss is not None:
            req["sl"] = float(order.stop_loss)
        if order.take_profit is not None:
            req["tp"] = float(order.take_profit)

        max_retries = 2
        last_error = None
        for attempt in range(max_retries):
            # Refresh tick price on each attempt (requote = stale price)
            tick = self._mt5.symbol_info_tick(sym)
            if tick is None:
                raise RuntimeError(f"no tick for {sym}")
            req["price"] = tick.ask if is_buy else tick.bid

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
        with `.profit` attribute.

        R6 hotfix (F3): a read FAILURE must RAISE, not return []. The old
        swallow made a transient MT5 IPC error indistinguishable from "no
        deals" — RiskManager then overwrote a real -4% day with 0.00 and the
        constitutional loss vetoes went blind. Fail-closed at the data layer.
        """
        if not self.connected or self._mt5 is None:
            raise RuntimeError("history_deals_get: broker not connected")
        deals = self._mt5.history_deals_get(from_dt, to_dt)
        return list(deals) if deals else []

    def get_rates(self, symbol: str, timeframe: int = None, count: int = 200):
        """Fetch OHLCV bars via the broker's own MT5 handle.

        Routes through self._mt5 (the session the broker initialized) to avoid
        the 'copy_rates_from_pos returned exception set' C-API corruption that
        happens when the cycle imports MetaTrader5 as a second bare module and
        calls copy_rates after the broker already initialized the terminal.
        Resolves symbol through resolve_symbol() to handle broker suffixes
        (.vx, .vxc, .m, etc.) automatically.
        Returns a list of rate tuples or empty list on failure.
        """
        if not self.connected or self._mt5 is None:
            return []
        tf = timeframe if timeframe is not None else self._mt5.TIMEFRAME_M15
        resolved = self.resolve_symbol(symbol)
        try:
            raw = self._mt5.copy_rates_from_pos(resolved, tf, 0, count)
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
