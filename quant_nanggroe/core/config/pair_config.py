from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AssetClass(str, Enum):
    FOREX_MAJOR = "forex_major"
    FOREX_MINOR = "forex_minor"
    FOREX_EXOTIC = "forex_exotic"
    CRYPTO = "crypto"
    EQUITY = "equity"
    COMMODITY = "commodity"
    INDEX = "index"
    BOND = "bond"


class TimeframeKey(str, Enum):
    HTF = "htf"
    MTF = "mtf"
    LTF = "ltf"


@dataclass
class PairAlignmentConfig:
    asset_class: AssetClass
    htf: str
    mtf: str
    ltf: str
    description: str = ""


DEFAULT_PAIR_CONFIGS: dict[AssetClass, PairAlignmentConfig] = {
    AssetClass.FOREX_MAJOR: PairAlignmentConfig(
        asset_class=AssetClass.FOREX_MAJOR,
        htf="W1",
        mtf="D1",
        ltf="H4",
        description="EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, NZD/USD",
    ),
    AssetClass.FOREX_MINOR: PairAlignmentConfig(
        asset_class=AssetClass.FOREX_MINOR,
        htf="D1",
        mtf="H4",
        ltf="H1",
        description="EUR/GBP, EUR/AUD, GBP/JPY, etc.",
    ),
    AssetClass.CRYPTO: PairAlignmentConfig(
        asset_class=AssetClass.CRYPTO,
        htf="D1",
        mtf="H4",
        ltf="M15",
        description="BTC/USD, ETH/USD, SOL/USD, etc.",
    ),
    AssetClass.EQUITY: PairAlignmentConfig(
        asset_class=AssetClass.EQUITY,
        htf="MN",
        mtf="W1",
        ltf="D1",
        description="AAPL, TSLA, SPY, etc.",
    ),
    AssetClass.COMMODITY: PairAlignmentConfig(
        asset_class=AssetClass.COMMODITY,
        htf="W1",
        mtf="D1",
        ltf="H4",
        description="XAU/USD, XAG/USD, BTC, etc.",
    ),
    AssetClass.INDEX: PairAlignmentConfig(
        asset_class=AssetClass.INDEX,
        htf="MN",
        mtf="W1",
        ltf="D1",
        description="SPX, NDX, DJI, FTSE, DAX, NKY",
    ),
    AssetClass.BOND: PairAlignmentConfig(
        asset_class=AssetClass.BOND,
        htf="MN",
        mtf="W1",
        ltf="D1",
        description="US10Y, US2Y, DE10Y, GB10Y, JP10Y",
    ),
}


SYMBOL_TO_ASSET_CLASS: dict[str, AssetClass] = {
    "EURUSD": AssetClass.FOREX_MAJOR,
    "GBPUSD": AssetClass.FOREX_MAJOR,
    "USDJPY": AssetClass.FOREX_MAJOR,
    "USDCHF": AssetClass.FOREX_MAJOR,
    "AUDUSD": AssetClass.FOREX_MAJOR,
    "USDCAD": AssetClass.FOREX_MAJOR,
    "NZDUSD": AssetClass.FOREX_MAJOR,
    "XAUUSD": AssetClass.COMMODITY,
    "XAGUSD": AssetClass.COMMODITY,
    "BTCUSD": AssetClass.CRYPTO,
    "ETHUSD": AssetClass.CRYPTO,
    "SOLUSD": AssetClass.CRYPTO,
    "SPY": AssetClass.EQUITY,
    "QQQ": AssetClass.EQUITY,
    "AAPL": AssetClass.EQUITY,
    "TSLA": AssetClass.EQUITY,
    "SPX": AssetClass.INDEX,
    "NDX": AssetClass.INDEX,
}


def get_pair_config(symbol: str) -> PairAlignmentConfig:
    asset_class = SYMBOL_TO_ASSET_CLASS.get(symbol.upper(), AssetClass.FOREX_MAJOR)
    return DEFAULT_PAIR_CONFIGS.get(asset_class, DEFAULT_PAIR_CONFIGS[AssetClass.FOREX_MAJOR])


def get_alignment(symbol: str) -> tuple[str, str, str]:
    config = get_pair_config(symbol)
    return config.htf, config.mtf, config.ltf
