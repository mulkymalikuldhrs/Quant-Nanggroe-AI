from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LeadLagType(Enum):
    SAME_DIRECTION = "same_direction"
    INVERTED = "inverted"


class AssetClass(Enum):
    METAL = "metal"
    FOREX = "forex"
    INDEX = "index"
    BOND = "bond"
    CRYPTO = "crypto"


@dataclass
class FuturesSpotPair:
    futures: str
    spot: str
    asset_class: AssetClass
    lead_lag: LeadLagType
    correlated_pairs: list[str] | None = None


FUTURES_SPOT_MAP: dict[str, FuturesSpotPair] = {
    "GC1!": FuturesSpotPair("GC1!", "XAUUSD", AssetClass.METAL, LeadLagType.SAME_DIRECTION, correlated_pairs=["SI1!"]),
    "SI1!": FuturesSpotPair("SI1!", "XAGUSD", AssetClass.METAL, LeadLagType.SAME_DIRECTION, correlated_pairs=["GC1!"]),
    "6E1!": FuturesSpotPair("6E1!", "EURUSD", AssetClass.FOREX, LeadLagType.SAME_DIRECTION, correlated_pairs=["6B1!"]),
    "6B1!": FuturesSpotPair("6B1!", "GBPUSD", AssetClass.FOREX, LeadLagType.SAME_DIRECTION, correlated_pairs=["6E1!"]),
    "6J1!": FuturesSpotPair("6J1!", "USDJPY", AssetClass.FOREX, LeadLagType.INVERTED),
    "6A1!": FuturesSpotPair("6A1!", "AUDUSD", AssetClass.FOREX, LeadLagType.SAME_DIRECTION),
    "6C1!": FuturesSpotPair("6C1!", "USDCAD", AssetClass.FOREX, LeadLagType.INVERTED),
    "6S1!": FuturesSpotPair("6S1!", "USDCHF", AssetClass.FOREX, LeadLagType.INVERTED),
    "ES1!": FuturesSpotPair("ES1!", "US500", AssetClass.INDEX, LeadLagType.SAME_DIRECTION, correlated_pairs=["NQ1!"]),
    "NQ1!": FuturesSpotPair("NQ1!", "NAS100", AssetClass.INDEX, LeadLagType.SAME_DIRECTION, correlated_pairs=["ES1!"]),
    "YM1!": FuturesSpotPair("YM1!", "US30", AssetClass.INDEX, LeadLagType.SAME_DIRECTION),
    "ZB1!": FuturesSpotPair("ZB1!", "US30Y", AssetClass.BOND, LeadLagType.SAME_DIRECTION),
    "ZN1!": FuturesSpotPair("ZN1!", "US10Y", AssetClass.BOND, LeadLagType.SAME_DIRECTION),
    "BTC1!": FuturesSpotPair("BTC1!", "BTCUSD", AssetClass.CRYPTO, LeadLagType.SAME_DIRECTION),
    "ETH1!": FuturesSpotPair("ETH1!", "ETHUSD", AssetClass.CRYPTO, LeadLagType.SAME_DIRECTION),
}


SPOT_TO_FUTURES: dict[str, str] = {v.spot: k for k, v in FUTURES_SPOT_MAP.items()}


class FuturesLeadLagMatrix:
    def __init__(self, pairs: dict[str, FuturesSpotPair] | None = None):
        self._pairs = pairs or FUTURES_SPOT_MAP

    def resolve_spot(self, futures_symbol: str) -> str | None:
        pair = self._pairs.get(futures_symbol)
        return pair.spot if pair else None

    def resolve_futures(self, spot_symbol: str) -> str | None:
        return SPOT_TO_FUTURES.get(spot_symbol)

    def get_pair(self, symbol: str) -> FuturesSpotPair | None:
        return self._pairs.get(symbol) or (FUTURES_SPOT_MAP.get(SPOT_TO_FUTURES.get(symbol, "")) if symbol in SPOT_TO_FUTURES else None)

    def detect_smt_divergence(self, futures_a_highs: list[float], futures_b_highs: list[float]) -> tuple[bool, str]:
        if len(futures_a_highs) < 2 or len(futures_b_highs) < 2:
            return False, "insufficient_data"
        a_hh = futures_a_highs[-1] > futures_a_highs[-2]
        b_hh = futures_b_highs[-1] > futures_b_highs[-2]
        diverged = a_hh != b_hh
        if not diverged:
            return False, "aligned"
        if a_hh and not b_hh:
            return True, "a_higher_high_b_lower_high"
        return True, "b_higher_high_a_lower_high"

    def get_correlated_pairs(self, futures_symbol: str) -> list[str]:
        pair = self._pairs.get(futures_symbol)
        if pair and pair.correlated_pairs:
            return pair.correlated_pairs
        return []

    def asset_class_bias(self, asset_class: AssetClass, signal: str) -> float | None:
        mapping: dict[AssetClass, dict[str, float]] = {
            AssetClass.METAL: {"buy": 0.7, "sell": -0.7},
            AssetClass.FOREX: {"buy": 0.5, "sell": -0.5},
            AssetClass.INDEX: {"buy": 0.8, "sell": -0.8},
            AssetClass.BOND: {"buy": 0.6, "sell": -0.6},
            AssetClass.CRYPTO: {"buy": 0.6, "sell": -0.6},
        }
        return mapping.get(asset_class, {}).get(signal)

    def to_dict(self) -> dict[str, Any]:
        return {
            sym: {
                "futures": p.futures,
                "spot": p.spot,
                "asset_class": p.asset_class.value,
                "lead_lag": p.lead_lag.value,
                "correlated_pairs": p.correlated_pairs or [],
            }
            for sym, p in self._pairs.items()
        }
