"""Liquidity & Order Flow Engine — Liquidity analysis and order flow.

Analyzes market liquidity, order flow imbalances, bid/ask spreads,
and volume-weighted price levels for execution quality assessment.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class LiquidityOrderflowEngine(ScreenerComponent):
    """Liquidity & Order Flow Engine.

    Analyzes:
    - Market depth and liquidity
    - Order flow imbalances (buy vs sell pressure)
    - Bid/ask spread analysis
    - Volume-weighted price levels (VWAP)
    - Execution quality metrics
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "liquidity_orderflow"

    @property
    def description(self) -> str:
        return "Liquidity & order flow (depth, imbalance, VWAP, spread)"

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        liquidity_score = self._analyze_liquidity(data)
        orderflow_score = self._analyze_orderflow(data)
        spread_score = self._analyze_spread(data)
        vwap_score = self._analyze_vwap(data)

        combined = (
            liquidity_score * 0.25
            + orderflow_score * 0.35
            + spread_score * 0.20
            + vwap_score * 0.20
        )

        direction = (
            ScreenerDirection.BULLISH
            if combined > 0.2
            else ScreenerDirection.BEARISH
            if combined < -0.2
            else ScreenerDirection.NEUTRAL
        )

        return ScreenerResult(
            component_name=self.name,
            direction=direction,
            score=combined,
            confidence=min(0.8, abs(combined) + 0.3),
            details={
                "liquidity_score": liquidity_score,
                "orderflow_score": orderflow_score,
                "spread_score": spread_score,
                "vwap_score": vwap_score,
                "execution_quality": "good" if spread_score > -0.2 else "poor",
            },
        )

    @staticmethod
    def _analyze_liquidity(data: Dict[str, Any]) -> float:
        lob = data.get("orderbook", {})
        if not isinstance(lob, dict):
            return 0.0

        bid_depth = lob.get("bid_depth", 0.0)
        ask_depth = lob.get("ask_depth", 0.0)

        if bid_depth + ask_depth == 0:
            return 0.0

        # Imbalance ratio
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
        return max(-1.0, min(1.0, imbalance))

    @staticmethod
    def _analyze_orderflow(data: Dict[str, Any]) -> float:
        flow = data.get("order_flow", {})
        if not isinstance(flow, dict):
            return 0.0

        buy_volume = flow.get("buy_volume", 0.0)
        sell_volume = flow.get("sell_volume", 0.0)
        total = buy_volume + sell_volume

        if total == 0:
            return 0.0

        imbalance = (buy_volume - sell_volume) / total
        return max(-1.0, min(1.0, imbalance * 2))

    @staticmethod
    def _analyze_spread(data: Dict[str, Any]) -> float:
        spread = data.get("spread", {})
        if not isinstance(spread, dict):
            return 0.0

        spread_bps = spread.get("spread_bps", 10.0)

        # Tight spreads = good liquidity
        if spread_bps < 5:
            return 0.3
        elif spread_bps < 15:
            return 0.1
        elif spread_bps > 50:
            return -0.4  # Wide spread = poor liquidity
        return 0.0

    @staticmethod
    def _analyze_vwap(data: Dict[str, Any]) -> float:
        prices = data.get("prices")
        if prices is None or not isinstance(prices, pd.DataFrame):
            return 0.0

        if "close" not in prices.columns or "volume" not in prices.columns:
            return 0.0

        close = prices["close"]
        volume = prices["volume"]

        if volume.sum() == 0:
            return 0.0

        vwap = float((close * volume).sum() / volume.sum())
        current = float(close.iloc[-1])

        # Price above VWAP = bullish
        if vwap > 0:
            deviation = (current - vwap) / vwap
            return max(-0.5, min(0.5, deviation * 10))

        return 0.0
