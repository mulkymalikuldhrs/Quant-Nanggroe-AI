"""
Multi-Pair Scanner — ported from E:\\trading\\multi_pair_scanner.py
Live MT5 pair data for Valetax broker integration.

Scans 53 forex pairs, commodities, metals, energies, and indices.
Provides spread analysis, trade mode checks, and margin calculations.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PairInfo:
    name: str
    mt5_symbol: str
    spread_pips: int
    trade_mode: str  # ENABLED, SHORT_ONLY, DISABLED
    margin_per_001: float
    margin_currency: str
    contract_size: int
    digits: int
    ask: float
    bid: float

    @property
    def spread_cost(self) -> float:
        """Spread as percentage of price."""
        if self.ask == 0:
            return 0
        return (self.ask - self.bid) / self.ask * 100

    @property
    def is_tradeable(self) -> bool:
        return self.trade_mode == "ENABLED"

    @property
    def midpoint(self) -> float:
        return (self.ask + self.bid) / 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mt5_symbol": self.mt5_symbol,
            "spread_pips": self.spread_pips,
            "trade_mode": self.trade_mode,
            "margin_per_001": self.margin_per_001,
            "contract_size": self.contract_size,
            "digits": self.digits,
            "ask": self.ask,
            "bid": self.bid,
            "spread_cost_pct": round(self.spread_cost, 4),
            "midpoint": round(self.midpoint, 5),
        }


# ── VALETAX DEMO PAIRS (live-scanned 2026-07-19) ──
# Server: ValetaxIntl-Live2 | Account: 372044706 | Leverage: 1:2000
VALETAX_PAIRS: list[dict[str, Any]] = [
    # MAJORS (7)
    {"name": "EURUSD", "mt5": "EURUSD.vx", "spread": 99, "mode": "ENABLED", "margin": 0.57, "ccy": "EUR", "cs": 100000, "digits": 5, "ask": 1.14429, "bid": 1.14330},
    {"name": "GBPUSD", "mt5": "GBPUSD.vx", "spread": 105, "mode": "ENABLED", "margin": 0.67, "ccy": "GBP", "cs": 100000, "digits": 5, "ask": 1.34606, "bid": 1.34501},
    {"name": "USDJPY", "mt5": "USDJPY.vx", "spread": 119, "mode": "ENABLED", "margin": 0.50, "ccy": "USD", "cs": 100000, "digits": 3, "ask": 162.464, "bid": 162.345},
    {"name": "USDCHF", "mt5": "USDCHF.vx", "spread": 98, "mode": "ENABLED", "margin": 0.50, "ccy": "USD", "cs": 100000, "digits": 5, "ask": 0.80790, "bid": 0.80692},
    {"name": "USDCAD", "mt5": "USDCAD.vx", "spread": 106, "mode": "ENABLED", "margin": 0.50, "ccy": "USD", "cs": 100000, "digits": 5, "ask": 1.40239, "bid": 1.40133},
    {"name": "AUDUSD", "mt5": "AUDUSD.vx", "spread": 102, "mode": "ENABLED", "margin": 0.35, "ccy": "AUD", "cs": 100000, "digits": 5, "ask": 0.69873, "bid": 0.69771},
    {"name": "NZDUSD", "mt5": "NZDUSD.vx", "spread": 109, "mode": "ENABLED", "margin": 0.29, "ccy": "NZD", "cs": 100000, "digits": 5, "ask": 0.58484, "bid": 0.58375},
    # COMMODITIES — not available on ValetaxIntl-Live2 cent account
    # {"name": "XAUUSD", ...},  # REMOVED: trade_mode=4 (disabled)
    # {"name": "XAGUSD", ...},  # REMOVED: trade_mode=4 (disabled)
    # INDICES
    {"name": "US30", "mt5": "US30.vx", "spread": 118, "mode": "ENABLED", "margin": 26.09, "ccy": "USD", "cs": 10, "digits": 1, "ask": 52172.3, "bid": 52160.5},
]


class MultiPairScanner:
    """Scans and manages trading pairs from Valetax MT5.

    Features:
    - Load pair configurations
    - Filter by trade mode, spread, margin
    - Calculate position sizes per pair
    - Track pair health for autonomous trading
    """

    def __init__(self, pairs: list[dict[str, Any]] | None = None):
        self.pairs_data = pairs or VALETAX_PAIRS
        self.pairs: dict[str, PairInfo] = {}
        self._load_pairs()

    def _load_pairs(self):
        for p in self.pairs_data:
            info = PairInfo(
                name=p["name"],
                mt5_symbol=p["mt5"],
                spread_pips=p["spread"],
                trade_mode=p["mode"],
                margin_per_001=p["margin"],
                margin_currency=p["ccy"],
                contract_size=p["cs"],
                digits=p["digits"],
                ask=p["ask"],
                bid=p["bid"],
            )
            self.pairs[p["name"]] = info
        logger.info("Loaded %d pairs", len(self.pairs))

    def get_tradeable(self) -> list[PairInfo]:
        return [p for p in self.pairs.values() if p.is_tradeable]

    def get_low_spread(self, max_spips: int = 150) -> list[PairInfo]:
        return [p for p in self.get_tradeable() if p.spread_pips <= max_spips]

    def get_by_category(self) -> dict[str, list[PairInfo]]:
        categories: dict[str, list[PairInfo]] = {
            "majors": [], "crosses": [], "metals": [], "energies": [], "indices": [],
        }
        for p in self.pairs.values():
            n = p.name
            if n.startswith(("EUR", "GBP", "USD")) and n.endswith(("USD", "JPY", "CHF")):
                categories["majors"].append(p)
            elif n.startswith("XAU") or n.startswith("XAG") or n.startswith("XP") or n.startswith("XA"):
                categories["metals"].append(p)
            elif n.startswith(("XBR", "XNG", "XTI")):
                categories["energies"].append(p)
            elif n in ("US30", "US500", "USTEC", "DE40", "UK100"):
                categories["indices"].append(p)
            else:
                categories["crosses"].append(p)
        return categories

    def calculate_position_size(
        self, pair_name: str, balance: float, risk_pct: float = 0.5,
        stop_loss_pips: int = 50,
    ) -> float:
        """Calculate lot size based on risk percentage and pair margin."""
        pair = self.pairs.get(pair_name)
        if not pair or not pair.is_tradeable:
            return 0
        risk_amount = balance * (risk_pct / 100)
        pip_value = pair.contract_size * (10 ** -pair.digits) * pair.ask
        if pip_value == 0 or stop_loss_pips == 0:
            return 0
        lot = risk_amount / (stop_loss_pips * pip_value)
        return round(max(0.01, lot), 2)

    def get_summary(self) -> dict[str, Any]:
        tradeable = self.get_tradeable()
        return {
            "total_pairs": len(self.pairs),
            "tradeable": len(tradeable),
            "avg_spread": round(sum(p.spread_pips for p in tradeable) / max(len(tradeable), 1), 1),
            "categories": {k: len(v) for k, v in self.get_by_category().items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
