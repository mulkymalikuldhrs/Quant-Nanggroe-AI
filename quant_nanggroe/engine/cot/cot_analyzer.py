"""
COTAnalyzer — CFTC Commitment of Traders analysis with historical percentile signals.

Analyzes COT positioning data for QNA's CME futures universe:
  - Commercials (Hedgers): True smart money → accumulation/distribution signals
  - Non-Commercials (Managed Money / Hedge Funds): Trend followers → crowded trade warnings
  - Non-Reportable (Retail): Contrarian indicator at extremes

Extreme thresholds:
  - Percentile > 90%  → EXTREME_LONG_OVERBOUGHT  (crowded trade → potential reversal)
  - Percentile < 10%  → EXTREME_SHORT_OVERSOLD   (capitulation → potential bottom)
  - Otherwise         → BALANCED

Usage:
    from quant_nanggroe.engine.cot import COTAnalyzer

    analyzer = COTAnalyzer()
    analyzer.fetch_history(years=3)
    signal = analyzer.evaluate("GC1!")
    # Returns: {"symbol": "GC1!", "market": "GOLD", "signal": "EXTREME_LONG_OVERBOUGHT",
    #            "net_noncomm": 235000, "percentile": 0.95, ...}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.cot.cot_fetcher import COTFetcher

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  CME → COT Market Name Mapping
# ══════════════════════════════════════════════════════════════════════

# Maps QNA's CME futures symbols to COT "Market and Exchange Names" substrings.
# These are the primary instruments in QNA's universe.
CME_TO_COT_MAP: dict[str, str] = {
    # Precious Metals
    "GC1!": "GOLD",
    "SI1!": "SILVER",
    "PL1!": "PLATINUM",
    "PA1!": "PALLADIUM",
    # Equity Indices
    "ES1!": "S&P 500 STOCK INDEX",
    "NQ1!": "NASDAQ STOCK INDEX",
    "YM1!": "DOW JONES STOCK INDEX",
    "RTY1!": "RUSSELL 2000",
    # FX
    "6E1!": "EURO FX",
    "6B1!": "BRITISH POUND",
    "6J1!": "JAPANESE YEN",
    "6A1!": "AUSTRALIAN DOLLAR",
    "6C1!": "CANADIAN DOLLAR",
    "6S1!": "SWISS FRANC",
    "DX1!": "US DOLLAR INDEX",
    "6N1!": "NEW ZEALAND DOLLAR",
    # Bonds
    "ZB1!": "30 YEAR US TREASURY BOND",
    "ZN1!": "10 YEAR US TREASURY NOTE",
    "ZF1!": "5 YEAR US TREASURY NOTE",
    "ZT1!": "2 YEAR US TREASURY NOTE",
    "UB1!": "US TREASURY BOND",
    # Energies
    "CL1!": "WTI CRUDE OIL",
    "NG1!": "NATURAL GAS",
    "HO1!": "HEATING OIL",
    "RB1!": "RBOB GASOLINE",
    # Softs / Agriculture
    "ZC1!": "CORN",
    "ZW1!": "WHEAT",
    "ZS1!": "SOYBEAN",
    "KC1!": "COFFEE",
    "SB1!": "SUGAR",
    "CT1!": "COTTON",
    # Crypto (CME)
    "BTC1!": "BITCOIN",
    "ETH1!": "ETHEREUM",
}


# ══════════════════════════════════════════════════════════════════════
#  Signal constants
# ══════════════════════════════════════════════════════════════════════

POSITIONING_SIGNAL = {
    "EXTREME_LONG_OVERBOUGHT": {
        "label": "Extreme Long — Overbought / Crowded",
        "grade": "F",
        "description": "Non-Commercial net long at 90th+ percentile. Crowded trade. "
                       "High reversal risk. Institutional smart money may be distributing.",
        "action": "REDUCE_EXISTING_LONGS / AVOID_NEW_LONGS",
        "contrary": "Consider counter-trend short if technical confirmation exists.",
    },
    "EXTREME_SHORT_OVERSOLD": {
        "label": "Extreme Short — Oversold / Capitulation",
        "grade": "F",
        "description": "Non-Commercial net short at 10th- percentile. "
                       "Capitulation. Potential bottom accumulation zone.",
        "action": "REDUCE_EXISTING_SHORTS / AVOID_NEW_SHORTS",
        "contrary": "Consider counter-trend long if technical confirmation exists.",
    },
    "COMMERCIAL_ACCUMULATION": {
        "label": "Commercial Accumulation — Smart Money Buying",
        "grade": "A",
        "description": "Commercial hedgers net long at 90th+ percentile. "
                       "Smart money accumulating — strong bullish signal.",
        "action": "PREFER_LONG_BIAS",
        "contrary": "High confidence signal when aligned with technical trend.",
    },
    "COMMERCIAL_DISTRIBUTION": {
        "label": "Commercial Distribution — Smart Money Selling",
        "grade": "A",
        "description": "Commercial hedgers net short at 10th- percentile. "
                       "Smart money distributing — strong bearish signal.",
        "action": "PREFER_SHORT_BIAS",
        "contrary": "High confidence signal when aligned with technical trend.",
    },
    "RETAIL_EXTREME_LONG": {
        "label": "Retail Extreme Long — Contrarian Bearish",
        "grade": "C",
        "description": "Non-Reportable (retail) net long at 90th+ percentile. "
                       "Retail is crowded long — contrarian sell signal.",
        "action": "CONTRARIAN: FAVOR_SHORT",
        "contrary": "Retail is usually wrong at extremes.",
    },
    "RETAIL_EXTREME_SHORT": {
        "label": "Retail Extreme Short — Contrarian Bullish",
        "grade": "C",
        "description": "Non-Reportable (retail) net short at 10th- percentile. "
                       "Retail is crowded short — contrarian buy signal.",
        "action": "CONTRARIAN: FAVOR_LONG",
        "contrary": "Retail is usually wrong at extremes.",
    },
    "BALANCED": {
        "label": "Balanced — No Extreme Signal",
        "grade": "B",
        "description": "Positioning within normal historical range. No extreme signal.",
        "action": "NONE_REQUIRED",
        "contrary": "Use other signal sources (causal, technical) for direction.",
    },
}


# ══════════════════════════════════════════════════════════════════════
#  COTAnalyzer
# ══════════════════════════════════════════════════════════════════════


class COTAnalyzer:
    """CFTC COT data analyzer with historical percentile signals.

    Downloads and caches COT data, then computes percentile-based
    positioning signals for QNA's CME futures universe.

    Usage:
        analyzer = COTAnalyzer(years_history=3)
        analyzer.fetch_history()
        signal = analyzer.evaluate("GC1!")
        all_signals = analyzer.evaluate_all()
    """

    def __init__(
        self,
        years_history: int = 5,
        extreme_long_threshold: float = 0.90,
        extreme_short_threshold: float = 0.10,
        fetcher: Optional[COTFetcher] = None,
    ):
        """
        Args:
            years_history: Years of COT history for percentile calc (default: 5).
            extreme_long_threshold: Percentile for EXTREME_LONG (default: 0.90).
            extreme_short_threshold: Percentile for EXTREME_SHORT (default: 0.10).
            fetcher: Optional pre-configured COTFetcher instance.
        """
        self.years_history = years_history
        self.extreme_long_threshold = extreme_long_threshold
        self.extreme_short_threshold = extreme_short_threshold
        self.fetcher = fetcher or COTFetcher()
        self._cot_data: Optional[pd.DataFrame] = None
        self._last_fetch_date: Optional[datetime] = None
        self._cache: dict[str, dict[str, Any]] = {}  # symbol -> signal cache

    # ── Data loading ───────────────────────────────────────────

    def fetch_history(self, force_refresh: bool = False) -> bool:
        """Fetch and cache COT historical data.

        Args:
            force_refresh: Bypass cache and re-download (default: False).

        Returns:
            True if data was loaded successfully.
        """
        df = self.fetcher.fetch_history(
            years=self.years_history, force_refresh=force_refresh
        )
        if df.empty:
            logger.error("COTAnalyzer: no data loaded")
            return False
        self._cot_data = df
        self._last_fetch_date = datetime.now(timezone.utc)
        self._cache.clear()
        logger.info(
            "COTAnalyzer ready: %d markets, %d rows",
            df["Market and Exchange Names"].nunique(),
            len(df),
        )
        return True

    @property
    def is_loaded(self) -> bool:
        """True if COT data has been loaded."""
        return self._cot_data is not None and not self._cot_data.empty

    @property
    def available_markets(self) -> list[str]:
        """List of available COT market names."""
        if not self.is_loaded:
            return []
        return sorted(self._cot_data["Market and Exchange Names"].unique().tolist())

    @property
    def available_symbols(self) -> list[str]:
        """List of CME symbols that have matching COT data."""
        if not self.is_loaded:
            return []
        available = []
        for sym, mkt_name in CME_TO_COT_MAP.items():
            if self._cot_data["Market and Exchange Names"].str.contains(
                mkt_name, case=False, na=False
            ).any():
                available.append(sym)
        return available

    # ── Core evaluation ────────────────────────────────────────

    def evaluate(self, symbol: str) -> dict[str, Any]:
        """Evaluate COT positioning for a single CME futures symbol.

        Computes:
            1. Latest net position for Non-Commercial, Commercial, Non-Reportable
            2. Historical percentile for each category
            3. Combined signal with action recommendation

        Args:
            symbol: CME futures symbol (e.g. 'GC1!', 'ES1!', '6E1!').

        Returns:
            Dict with positioning data, percentile, signal, and action.
            Returns a "NOT_FOUND" signal if symbol is not in the mapping
            or data is unavailable.
        """
        # Check cache
        if symbol in self._cache:
            return self._cache[symbol]

        result = self._evaluate_inner(symbol)
        self._cache[symbol] = result
        return result

    def evaluate_all(self) -> dict[str, dict[str, Any]]:
        """Evaluate COT positioning for ALL available CME symbols.

        Returns:
            Dict of symbol -> evaluation result.
        """
        results: dict[str, dict[str, Any]] = {}
        for sym in self.available_symbols:
            results[sym] = self.evaluate(sym)
        return results

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the current COT landscape.

        Returns:
            Dict with extreme signals count, top signals, timestamp.
        """
        if not self.is_loaded:
            return {"loaded": False, "n_extreme": 0, "signals": {}}

        all_sigs = self.evaluate_all()
        extremes = {
            sym: s
            for sym, s in all_sigs.items()
            if s.get("signal", "BALANCED") != "BALANCED"
        }

        return {
            "loaded": True,
            "last_fetch": str(self._last_fetch_date) if self._last_fetch_date else None,
            "n_markets": int(self._cot_data["Market and Exchange Names"].nunique()),
            "n_symbols": len(all_sigs),
            "n_extreme": len(extremes),
            "extreme_signals": extremes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Internal evaluation ────────────────────────────────────

    def _evaluate_inner(self, symbol: str) -> dict[str, Any]:
        """Evaluate COT for a symbol without cache."""
        default = {
            "symbol": symbol,
            "market": CME_TO_COT_MAP.get(symbol, "UNKNOWN"),
            "signal": "NOT_FOUND",
            "grade": "N/A",
            "net_noncomm": None,
            "net_comm": None,
            "net_retail": None,
            "percentile_noncomm": None,
            "percentile_comm": None,
            "percentile_retail": None,
            "open_interest": None,
            "latest_date": None,
            "n_weeks_history": 0,
            "action": "NO_DATA",
            "description": "Symbol not mapped or no COT data available.",
        }

        # Check symbol is mapped
        market_name = CME_TO_COT_MAP.get(symbol)
        if market_name is None:
            logger.debug("COT: unknown symbol '%s'", symbol)
            return default

        # Get contract data
        if not self.is_loaded:
            return default
        contract = self.fetcher.get_contract_data(market_name)
        if contract.empty:
            return default

        # Extract core columns
        date_col = "As of Date in Form YYYY-MM-DD"
        noncomm_long = "Noncommercial Positions-Long (All)"
        noncomm_short = "Noncommercial Positions-Short (All)"
        comm_long = "Commercial Positions-Long (All)"
        comm_short = "Commercial Positions-Short (All)"
        retail_long = "Nonreportable Positions-Long (All)"
        retail_short = "Nonreportable Positions-Short (All)"
        oi_col = "Open Interest (All)"

        # Compute net positions for each category
        contract = contract.sort_values(date_col)
        n_weeks = len(contract)

        net_noncomm = (
            pd.to_numeric(contract[noncomm_long], errors="coerce")
            - pd.to_numeric(contract[noncomm_short], errors="coerce")
        )
        net_comm = (
            pd.to_numeric(contract[comm_long], errors="coerce")
            - pd.to_numeric(contract[comm_short], errors="coerce")
        )
        net_retail = (
            pd.to_numeric(contract[retail_long], errors="coerce")
            - pd.to_numeric(contract[retail_short], errors="coerce")
        )
        oi = pd.to_numeric(contract[oi_col], errors="coerce")

        # Latest values
        latest = contract.iloc[-1]
        latest_date = latest.get(date_col)
        latest_net_noncomm = float(net_noncomm.iloc[-1]) if not net_noncomm.empty else None
        latest_net_comm = float(net_comm.iloc[-1]) if not net_comm.empty else None
        latest_net_retail = float(net_retail.iloc[-1]) if not net_retail.empty else None
        latest_oi = float(oi.iloc[-1]) if not oi.empty else None

        # Historical percentiles
        pct_noncomm = self._compute_percentile(net_noncomm.dropna())
        pct_comm = self._compute_percentile(net_comm.dropna())
        pct_retail = self._compute_percentile(net_retail.dropna())

        # Combine signals
        signal, signal_detail = self._classify_signal(
            symbol=market_name,
            percentile_noncomm=pct_noncomm,
            percentile_comm=pct_comm,
            percentile_retail=pct_retail,
            latest_net_noncomm=latest_net_noncomm,
            latest_net_comm=latest_net_comm,
        )

        return {
            "symbol": symbol,
            "market": market_name,
            "signal": signal,
            "grade": signal_detail.get("grade", "B"),
            "description": signal_detail.get("description", ""),
            "action": signal_detail.get("action", "NONE_REQUIRED"),
            "net_noncomm": latest_net_noncomm,
            "net_comm": latest_net_comm,
            "net_retail": latest_net_retail,
            "percentile_noncomm": round(pct_noncomm, 4) if pct_noncomm is not None else None,
            "percentile_comm": round(pct_comm, 4) if pct_comm is not None else None,
            "percentile_retail": round(pct_retail, 4) if pct_retail is not None else None,
            "open_interest": latest_oi,
            "latest_date": str(latest_date) if latest_date else None,
            "n_weeks_history": n_weeks,
            "net_noncomm_series": net_noncomm.tolist() if len(net_noncomm) <= 520 else None,
            "net_comm_series": net_comm.tolist() if len(net_comm) <= 520 else None,
        }

    # ── Percentile & classification ────────────────────────────

    @staticmethod
    def _compute_percentile(series: pd.Series) -> Optional[float]:
        """Compute the percentile of the latest value within its history.

        Uses (value - min) / (max - min) as the percentile measure.

        Args:
            series: Historical net position values.

        Returns:
            Percentile 0.0–1.0, or None if insufficient data.
        """
        if len(series) < 5:
            return None
        value = series.iloc[-1]
        lo = series.min()
        hi = series.max()
        if hi == lo:
            return 0.5
        return (value - lo) / (hi - lo)

    def _classify_signal(
        self,
        symbol: str,
        percentile_noncomm: Optional[float],
        percentile_comm: Optional[float],
        percentile_retail: Optional[float],
        latest_net_noncomm: Optional[float],
        latest_net_comm: Optional[float],
    ) -> tuple[str, dict[str, Any]]:
        """Classify the combined COT signal from all categories.

        Priority order:
          1. Commercial (Smart Money) extreme → highest confidence
          2. Non-Commercial (Hedge Funds) extreme → medium confidence
          3. Non-Reportable (Retail) extreme → contrarian (low confidence)
          4. Balanced → no extreme signal

        Args:
            symbol: Market name for logging.
            percentile_noncomm: Non-Commercial net position percentile.
            percentile_comm: Commercial (Hedgers) net position percentile.
            percentile_retail: Non-Reportable net position percentile.
            latest_net_noncomm: Latest Non-Commercial net position.
            latest_net_comm: Latest Commercial net position.

        Returns:
            Tuple of (signal_key, signal_detail_dict).
        """
        # 1. Commercial (Smart Money) — highest priority
        if percentile_comm is not None:
            if percentile_comm >= self.extreme_long_threshold and latest_net_comm is not None and latest_net_comm > 0:
                logger.debug("COT %s: Commercial accumulation (comm net long, p=%.2f)", symbol, percentile_comm)
                return "COMMERCIAL_ACCUMULATION", POSITIONING_SIGNAL["COMMERCIAL_ACCUMULATION"]
            if percentile_comm <= self.extreme_short_threshold and latest_net_comm is not None and latest_net_comm < 0:
                logger.debug("COT %s: Commercial distribution (comm net short, p=%.2f)", symbol, percentile_comm)
                return "COMMERCIAL_DISTRIBUTION", POSITIONING_SIGNAL["COMMERCIAL_DISTRIBUTION"]

        # 2. Non-Commercial (Hedge Funds) — medium priority
        if percentile_noncomm is not None:
            if percentile_noncomm >= self.extreme_long_threshold:
                logger.debug("COT %s: NonCom extreme long (p=%.2f)", symbol, percentile_noncomm)
                return "EXTREME_LONG_OVERBOUGHT", POSITIONING_SIGNAL["EXTREME_LONG_OVERBOUGHT"]
            if percentile_noncomm <= self.extreme_short_threshold:
                logger.debug("COT %s: NonCom extreme short (p=%.2f)", symbol, percentile_noncomm)
                return "EXTREME_SHORT_OVERSOLD", POSITIONING_SIGNAL["EXTREME_SHORT_OVERSOLD"]

        # 3. Non-Reportable (Retail) — contrarian
        if percentile_retail is not None:
            if percentile_retail >= self.extreme_long_threshold:
                return "RETAIL_EXTREME_LONG", POSITIONING_SIGNAL["RETAIL_EXTREME_LONG"]
            if percentile_retail <= self.extreme_short_threshold:
                return "RETAIL_EXTREME_SHORT", POSITIONING_SIGNAL["RETAIL_EXTREME_SHORT"]

        return "BALANCED", POSITIONING_SIGNAL["BALANCED"]

    # ── Compatibility with MasterQuantNanggroeEngine ──────────

    def get_cot_params_for_engine(self, symbol: str) -> dict[str, float]:
        """Get COT parameters formatted for MasterQuantNanggroeEngine.

        Args:
            symbol: CME futures symbol (e.g. 'GC1!').

        Returns:
            Dict with cot_net_positions, cot_hist_min, cot_hist_max
            compatible with engine.evaluate_full_pipeline().
        """
        if not self.is_loaded:
            return {}

        market_name = CME_TO_COT_MAP.get(symbol)
        if market_name is None:
            return {}

        contract = self.fetcher.get_contract_data(market_name)
        if contract.empty:
            return {}

        noncomm_long = "Noncommercial Positions-Long (All)"
        noncomm_short = "Noncommercial Positions-Short (All)"
        net = (
            pd.to_numeric(contract[noncomm_long], errors="coerce")
            - pd.to_numeric(contract[noncomm_short], errors="coerce")
        ).dropna()

        if len(net) < 5:
            return {}

        return {
            "cot_net_positions": float(net.iloc[-1]),
            "cot_hist_min": float(net.min()),
            "cot_hist_max": float(net.max()),
        }
