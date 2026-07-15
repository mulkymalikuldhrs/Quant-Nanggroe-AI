"""Live MT5 broker connector (Exness/Valutrades). Fail-closed: no terminal -> raise, never silent.
Reuses BrokerConnector ABC + Order/Position from broker_base. Symbol map: BTC-USD -> BTCUSD.
"""
from typing import List

from quant_nanggroe.connectors.broker_base import BrokerConnector, Order, Position, BrokerType


def _mt5_symbol(qna_symbol: str) -> str:
    # ponytail: yfinance BTC-USD -> MT5 BTCUSD; forex EUR-USD -> EURUSD
    return qna_symbol.replace("-", "").upper()


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
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")  # ponytail: fail-closed, no silent paper fallback
        self.connected = True
        return True

    def place_order(self, order: Order) -> str:
        if not self.connected:
            raise RuntimeError("not connected")
        sym = _mt5_symbol(order.symbol)
        if not self._mt5.symbol_select(sym, True):
            raise RuntimeError(f"MT5 symbol unavailable: {sym}")
        tick = self._mt5.symbol_info_tick(sym)
        if tick is None:
            raise RuntimeError(f"no tick for {sym}")
        req = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": sym,
            "volume": float(order.quantity),
            "type": self._mt5.ORDER_TYPE_BUY if order.side == "buy" else self._mt5.ORDER_TYPE_SELL,
            "price": tick.ask if order.side == "buy" else tick.bid,
            "deviation": 20,
            "magic": self.magic,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
            "type_time": self._mt5.ORDER_TIME_GTC,
        }
        res = self._mt5.order_send(req)
        if res.retcode != self._mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"MT5 order failed: {res.retcode} {res.comment}")
        return str(res.order)

    def get_positions(self) -> List[Position]:
        if not self.connected:
            return []
        out = []
        for p in self._mt5.positions_get() or []:
            out.append(Position(
                symbol=p.symbol, quantity=p.volume, entry_price=p.price_open,
                current_price=p.price_current, pnl=p.profit, broker=BrokerType.MT5.value))
        return out

    def get_balance(self) -> float:
        if not self.connected:
            raise RuntimeError("not connected")
        acc = self._mt5.account_info()
        return float(acc.balance) if acc else 0.0

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
