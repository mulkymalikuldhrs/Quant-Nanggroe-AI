"""Profile Mapper — maps (pair, strategy_type, timeframe) → risk profile.

Constitutional limits from constants.py override any profile parameter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from quant_nanggroe.engine.risk.constants import MAX_RISK_PER_TRADE as _CONST_MAX_RISK_PCT

logger = logging.getLogger(__name__)

DEFAULT_KILLZONES: List[str] = [
    "london_open", "ny_open", "london_close",
]


@dataclass
class RiskProfile:
    """Risk parameters for a specific (pair, strategy, timeframe) combo."""
    max_risk_pct: float = 0.5          # % of account per trade
    min_rr: float = 2.0                # minimum risk-reward ratio
    max_correlation: float = 0.7       # max Pearson correlation to other positions
    preferred_killzones: List[str] = field(default_factory=lambda: list(DEFAULT_KILLZONES))


PROFILES: Dict[Tuple[str, str, str], RiskProfile] = {
    # ── Forex – SMC ──
    ("EURUSD", "smc", "H1"):     RiskProfile(0.5, 2.5, 0.6, ["london_open", "london_close"]),
    ("GBPUSD", "smc", "H1"):     RiskProfile(0.5, 2.5, 0.6, ["london_open", "london_close"]),
    ("USDJPY", "smc", "H1"):     RiskProfile(0.4, 2.0, 0.6, ["ny_open", "tokyo_open"]),
    ("EURUSD", "smc", "H4"):     RiskProfile(0.6, 3.0, 0.5, ["london_open", "ny_open"]),
    ("GBPUSD", "smc", "H4"):     RiskProfile(0.6, 3.0, 0.5, ["london_open", "ny_open"]),

    # ── Forex – Momentum ──
    ("EURUSD", "momentum", "H1"): RiskProfile(0.3, 1.8, 0.7, ["london_open", "ny_open"]),
    ("GBPUSD", "momentum", "H1"): RiskProfile(0.3, 1.8, 0.7, ["london_open", "ny_open"]),
    ("USDJPY", "momentum", "H1"): RiskProfile(0.3, 1.8, 0.7, ["ny_open", "tokyo_open"]),

    # ── Indices – SMC ──
    ("SPY", "smc", "H1"):        RiskProfile(0.4, 2.0, 0.5, ["ny_open"]),
    ("QQQ", "smc", "H1"):        RiskProfile(0.4, 2.0, 0.5, ["ny_open"]),
    ("SPY", "smc", "H4"):        RiskProfile(0.5, 2.5, 0.4, ["ny_open"]),

    # ── Indices – Momentum ──
    ("SPY", "momentum", "H1"):   RiskProfile(0.3, 1.5, 0.6, ["ny_open"]),
    ("QQQ", "momentum", "H1"):   RiskProfile(0.3, 1.5, 0.6, ["ny_open"]),

    # ── Crypto – SMC ──
    ("BTC-USD", "smc", "H1"):    RiskProfile(0.5, 2.0, 0.5, ["ny_open", "london_open"]),
    ("ETH-USD", "smc", "H1"):    RiskProfile(0.5, 2.0, 0.5, ["ny_open", "london_open"]),
    ("SOL-USD", "smc", "H1"):    RiskProfile(0.4, 2.0, 0.5, ["ny_open", "london_open"]),
    ("BTC-USD", "smc", "H4"):    RiskProfile(0.6, 2.5, 0.4, ["ny_open"]),

    # ── Crypto – Momentum ──
    ("BTC-USD", "momentum", "H1"): RiskProfile(0.3, 1.5, 0.6, ["ny_open", "london_open"]),
    ("ETH-USD", "momentum", "H1"): RiskProfile(0.3, 1.5, 0.6, ["ny_open", "london_open"]),

    # ── Commodities ──
    ("XAUUSD", "smc", "H1"):     RiskProfile(0.4, 2.5, 0.5, ["london_open", "ny_open"]),
    ("XAUUSD", "smc", "H4"):     RiskProfile(0.5, 3.0, 0.4, ["london_open", "ny_open"]),
    ("XAGUSD", "smc", "H1"):     RiskProfile(0.3, 2.0, 0.6, ["london_open", "ny_open"]),
    ("USOIL", "momentum", "H1"): RiskProfile(0.3, 2.0, 0.6, ["ny_open", "london_open"]),
}

# Wildcard keys for broader matching
WILDCARD_PROFILES: Dict[str, RiskProfile] = {
    "forex":  RiskProfile(0.4, 2.0, 0.7, ["london_open", "ny_open"]),
    "index":  RiskProfile(0.3, 2.0, 0.6, ["ny_open"]),
    "crypto": RiskProfile(0.4, 2.0, 0.6, ["ny_open", "london_open"]),
    "commodity": RiskProfile(0.3, 2.0, 0.7, ["london_open", "ny_open"]),
    "other":  RiskProfile(0.3, 2.0, 0.8, ["london_open", "ny_open"]),
}

# ── Sector map (mirrors constants.SECTOR_MAP) — used as fallback for sector-based profiles
_FALLBACK_SECTOR_MAP: Dict[str, str] = {
    "EURUSD": "forex", "GBPUSD": "forex", "USDJPY": "forex",
    "USDCAD": "forex", "AUDUSD": "forex", "NZDUSD": "forex",
    "EURGBP": "forex", "EURJPY": "forex", "GBPJPY": "forex",
    "CHFJPY": "forex", "AUDJPY": "forex", "NZDJPY": "forex",
    "SPY": "index", "QQQ": "index", "DIA": "index", "IWM": "index",
    "SPX": "index", "NDX": "index", "VIX": "index",
    "BTC-USD": "crypto", "ETH-USD": "crypto", "SOL-USD": "crypto",
    "XRP-USD": "crypto", "ADA-USD": "crypto",
    "XAUUSD": "commodity", "XAGUSD": "commodity", "USOIL": "commodity",
    "UKOIL": "commodity", "NG": "commodity",
}


class ProfileMapper:
    """Maps (pair, strategy_type, timeframe) → risk profile.

    Lookup order:
      1. Exact match (pair, strategy, tf)
      2. Pair + strategy (any tf)
      3. Sector-level wildcard based on pair's sector
      4. Default generic profile

    Constitutional limits override the result: ``max_risk_pct`` is capped at
    the system-wide ``MAX_RISK_PER_TRADE`` (currently 0.5 %).
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str, str], RiskProfile] = {}

    def get_profile(
        self,
        pair: str,
        strategy_type: str,
        timeframe: str,
    ) -> RiskProfile:
        """Return the risk profile for the given parameters.

        Parameters
        ----------
        pair:
            Instrument symbol (e.g. EURUSD, BTC-USD, SPY).
        strategy_type:
            Strategy identifier (e.g. smc, momentum, mean_reversion).
        timeframe:
            Chart timeframe (e.g. H1, H4, D1).

        Returns
        -------
        RiskProfile
            Mapped profile with constitutional limits enforced.
        """
        key = (pair.upper(), strategy_type.lower(), timeframe.upper())
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        profile = self._resolve(key)

        # ── Constitutional override ──────────────────────────────────
        const_max = _CONST_MAX_RISK_PCT * 100  # 0.5 by default
        if profile.max_risk_pct > const_max:
            logger.info(
                "Profile %s max_risk_pct=%.2f%% > constitutional limit %.2f%% — capped",
                key, profile.max_risk_pct, const_max,
            )
            profile.max_risk_pct = const_max

        self._cache[key] = profile
        return profile

    def _resolve(self, key: Tuple[str, str, str]) -> RiskProfile:
        pair, strategy, tf = key

        # 1. Exact match
        exact = PROFILES.get((pair, strategy, tf))
        if exact is not None:
            return RiskProfile(**{k: getattr(exact, k) for k in
                                  ["max_risk_pct", "min_rr", "max_correlation",
                                   "preferred_killzones"]})

        # 2. Pair + strategy (any tf)
        for (p, s, _), prof in PROFILES.items():
            if p == pair and s == strategy:
                return RiskProfile(**{k: getattr(prof, k) for k in
                                      ["max_risk_pct", "min_rr", "max_correlation",
                                       "preferred_killzones"]})

        # 3. Sector-level wildcard
        sector = _FALLBACK_SECTOR_MAP.get(pair, "other")
        wild = WILDCARD_PROFILES.get(sector)
        if wild is not None:
            return RiskProfile(**{k: getattr(wild, k) for k in
                                  ["max_risk_pct", "min_rr", "max_correlation",
                                   "preferred_killzones"]})

        # 4. Default
        logger.debug("No profile for %s — using generic default", key)
        return RiskProfile()

    def invalidate_cache(self, pair: Optional[str] = None) -> None:
        """Clear cached profiles, optionally for a specific pair."""
        if pair is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if k[0] != pair.upper()}
