"""QuantDinger-inspired multi-broker abstraction layer."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class BrokerType(Enum):
    CRYPTO = "crypto"
    IBKR = "ibkr"
    MT5 = "mt5"
    SIMULATED = "simulated"


@dataclass
class Order:
    symbol: str
    side: str  # buy/sell
    quantity: float
    order_type: str  # market/limit/stop
    price: Optional[float] = None
    stop_loss: Optional[float] = None  # P0 fix: protective SL price sent to broker
    take_profit: Optional[float] = None  # P0 fix: protective TP price sent to broker
    broker: str = ""


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    pnl: float = 0.0
    broker: str = ""


class BrokerConnector(ABC):
    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def place_order(self, order: Order) -> str: ...  # returns order_id

    @abstractmethod
    def get_positions(self) -> List[Position]: ...

    @abstractmethod
    def get_balance(self) -> float: ...

    @abstractmethod
    def disconnect(self): ...

