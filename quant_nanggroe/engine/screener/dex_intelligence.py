"""DEX Intelligence Engine — On-chain / DEX data analysis.

Analyzes DEX (decentralized exchange) data, on-chain metrics,
liquidity pools, and token flow patterns for crypto markets.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class DexIntelligenceEngine(ScreenerComponent):
    """DEX Intelligence Engine.

    Analyzes DEX and on-chain data including:
    - DEX volume and liquidity
    - Token flow (whale movements, smart money)
    - Protocol TVL changes
    - On-chain metrics (active addresses, transaction volume)
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "dex_intelligence"

    @property
    def description(self) -> str:
        return "DEX/on-chain intelligence (volume, liquidity, token flow, TVL)"

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        volume_score = self._analyze_dex_volume(data)
        liquidity_score = self._analyze_liquidity(data)
        flow_score = self._analyze_token_flow(data)
        tvl_score = self._analyze_tvl(data)

        combined = (
            volume_score * 0.25
            + liquidity_score * 0.25
            + flow_score * 0.30
            + tvl_score * 0.20
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
                "dex_volume_score": volume_score,
                "liquidity_score": liquidity_score,
                "token_flow_score": flow_score,
                "tvl_score": tvl_score,
            },
        )

    @staticmethod
    def _analyze_dex_volume(data: Dict[str, Any]) -> float:
        dex = data.get("dex_data", {})
        if not isinstance(dex, dict):
            return 0.0

        volume_change = dex.get("volume_24h_change", 0.0)
        if volume_change > 0.5:
            return 0.4  # High volume increase
        elif volume_change > 0.1:
            return 0.2
        elif volume_change < -0.3:
            return -0.2
        return 0.0

    @staticmethod
    def _analyze_liquidity(data: Dict[str, Any]) -> float:
        dex = data.get("dex_data", {})
        if not isinstance(dex, dict):
            return 0.0

        liquidity_change = dex.get("liquidity_change_7d", 0.0)
        if liquidity_change > 0.2:
            return 0.3  # Increasing liquidity = bullish
        elif liquidity_change < -0.2:
            return -0.3
        return 0.0

    @staticmethod
    def _analyze_token_flow(data: Dict[str, Any]) -> float:
        onchain = data.get("onchain_data", {})
        if not isinstance(onchain, dict):
            return 0.0

        # Whale accumulation
        whale_net = onchain.get("whale_net_flow", 0.0)
        if whale_net > 0.3:
            return 0.4  # Whales accumulating
        elif whale_net < -0.3:
            return -0.4  # Whales distributing
        return 0.0

    @staticmethod
    def _analyze_tvl(data: Dict[str, Any]) -> float:
        defi = data.get("defi_data", {})
        if not isinstance(defi, dict):
            return 0.0

        tvl_change = defi.get("tvl_change_7d", 0.0)
        if tvl_change > 0.15:
            return 0.3
        elif tvl_change < -0.15:
            return -0.3
        return 0.0
