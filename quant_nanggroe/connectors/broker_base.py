"""QuantDinger-inspired multi-broker abstraction layer."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


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
    broker: str = "simulated"


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    pnl: float = 0.0
    broker: str = "simulated"


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


class MultiBrokerManager:
    def __init__(self):
        self.brokers: Dict[str, BrokerConnector] = {}

    def register(self, name: str, broker: BrokerConnector):
        self.brokers[name] = broker

    def place_order(self, order: Order) -> Dict[str, str]:
        results = {}
        for name, broker in self.brokers.items():
            try:
                order_id = broker.place_order(order)
                results[name] = order_id
            except Exception as e:
                results[name] = f"error: {e}"
        return results

    def aggregate_positions(self) -> Dict[str, List[Position]]:
        return {name: b.get_positions() for name, b in self.brokers.items()}
