"""Provider interface definitions for Quant Nanggroe data layer.

Defines the abstract base for all data providers and the shared
data types used by the fallback chain and registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List


class DataCategory(Enum):
    EQUITY_OHLCV = auto()
    CRYPTO_OHLCV = auto()
    FOREX_OHLCV = auto()
    TICKER = auto()
    NEWS = auto()
    ECONOMIC = auto()
    MACRO = auto()


@dataclass
class DataRequest:
    category: DataCategory
    symbol: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataResponse:
    results: List[Dict[str, Any]]
    provider: str = ""
    error: str = ""


class QNAProviderBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def fetch(self, request: DataRequest) -> DataResponse:
        ...
