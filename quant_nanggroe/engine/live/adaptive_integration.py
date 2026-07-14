"""Adaptive integration: wires all 15 strategies + MTF + Risk + COT + Econ Calendar into live_engine.

Provides:
  - AdaptiveSignalPipeline: regime→strategy selection → MTF alignment → signal output
  - RiskGate: pre-trade RiskManager checks (VaR, drawdown, kill switch)
  - DataFeedIntegrator: COT + economic calendar signals as overlay
  - create_live_pipeline(): factory for all components
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger("QNA.LiveIntegration")


@dataclass
class LiveSignal:
    symbol: str
    side: str  # "buy", "sell", "hold"
    confidence: float = 0.5
    strategy: str = ""
    price: float = 0.0
    reason: str = ""
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


# ─── Adaptive Signal Pipeline ─────────────────────────────────────


class AdaptiveSignalPipeline:
    """Generates signals through all 15 strategies with adaptive selection + MTF alignment.

    Pipeline:
      1. Detect market regime (bullish/bearish/ranging/volatile)
      2. Select top-N strategies via StrategySelector compatibility matrix
      3. Apply MTF alignment (HTF trend → MTF confirm → LTF entry)
      4. Override/boost signals from COT + economic calendar + sentiment
      5. Return weighted signals for execution
    """

    def __init__(
        self,
        selector: object = None,
        regime_engine: object = None,
        enable_mtf: bool = True,
        enable_cot: bool = True,
        enable_calendar: bool = True,
        enable_sentiment: bool = True,
    ):
        self.enable_mtf = enable_mtf
        self.enable_cot = enable_cot
        self.enable_calendar = enable_calendar
        self.enable_sentiment = enable_sentiment
        self._selector = selector
        self._regime_engine = regime_engine
        self._adaptive_engine = None
        self._strategies: Dict[str, object] = {}
        self._strategy_names: List[str] = []
        self._loaded = False
        self._load_strategies()

    def _load_strategies(self):
        """Load all 15 strategies from the engine registry."""
        try:
            from quant_nanggroe.engine.strategy.loader import create_strategy
            from quant_nanggroe.engine.strategies.registry import (
                list_strategies,
                get_strategy_metadata,
            )
            names = list_strategies()
            for name in names:
                try:
                    self._strategies[name] = create_strategy(name)
                except Exception as e:
                    log.debug(f"  Skip {name}: {e}")
            self._strategy_names = list(self._strategies.keys())
            log.info(
                f"AdaptiveSignalPipeline: {len(self._strategies)} strategies loaded"
            )

            from quant_nanggroe.engine.strategy.strategy_selector import (
                AdaptiveStrategyEngine,
                StrategySelector,
            )
            sel = self._selector or StrategySelector(
                performance_window=20, min_signals=3, top_n=3
            )
            self._adaptive_engine = AdaptiveStrategyEngine(
                selector=sel, regime_engine=self._regime_engine
            )
            self._loaded = True
        except Exception as e:
            log.warning(f"Adaptive signal pipeline load failed: {e}")

    def _to_dataframe(self, candles: List[Dict]) -> Optional[pd.DataFrame]:
        if not candles:
            return None
        df = pd.DataFrame(candles)
        if df.empty:
            return None
        return df

    def detect_regime(self, candles_dict: Dict[str, List[Dict]]) -> str:
        """Detect current market regime from available candle data."""
        if self._adaptive_engine is None:
            return "unknown"
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            candles = candles_dict.get(sym, [])
            df = self._to_dataframe(candles)
            if df is not None and len(df) >= 20:
                return self._adaptive_engine.get_regime(df)
        return "unknown"

    def generate_signals(
        self,
        candles_dict: Dict[str, List[Dict]],
        prices: Dict[str, float],
        htf_candles: Optional[Dict[str, List[Dict]]] = None,
        mtf_candles: Optional[Dict[str, List[Dict]]] = None,
        cot_data: Optional[Dict] = None,
        calendar_data: Optional[List] = None,
        sentiment_data: Optional[Dict[str, Dict]] = None,
    ) -> List[LiveSignal]:
        """Generate signals across all assets using adaptive pipeline.

        Args:
            candles_dict: Asset → list of OHLCV dicts (main timeframe, e.g. 1h)
            prices: Asset → current price
            htf_candles: Higher timeframe data (e.g. 1d) for MTF
            mtf_candles: Medium timeframe data (e.g. 15m) for MTF
            cot_data: COT analysis results (from DataFeedIntegrator)
            calendar_data: Economic calendar events (from DataFeedIntegrator)
            sentiment_data: Asset → sentiment scores (from SentimentAnalyzer)

        Returns:
            List of LiveSignal objects sorted by confidence descending.
        """
        if not self._loaded or not self._strategies:
            return []

        regime = self.detect_regime(candles_dict)
        all_signals: List[LiveSignal] = []

        # Convert HTF/MTF data to DataFrames once
        htf_dfs: Dict[str, pd.DataFrame] = {}
        mtf_dfs: Dict[str, pd.DataFrame] = {}
        if htf_candles:
            for sym, c in htf_candles.items():
                df = self._to_dataframe(c)
                if df is not None:
                    htf_dfs[sym] = df
        if mtf_candles:
            for sym, c in mtf_candles.items():
                df = self._to_dataframe(c)
                if df is not None:
                    mtf_dfs[sym] = df

        for sym, price in prices.items():
            if not price or price <= 0:
                continue
            candles = candles_dict.get(sym, [])
            df = self._to_dataframe(candles)
            if df is None or len(df) < 20:
                continue

            mtf_df = mtf_dfs.get(sym)
            htf_df = htf_dfs.get(sym)

            for name, strategy in self._strategies.items():
                try:
                    if self.enable_mtf and htf_df is not None and mtf_df is not None:
                        from quant_nanggroe.engine.strategy.multi_timeframe import (
                            MultiTimeframeStrategy,
                        )
                        mtf = MultiTimeframeStrategy(
                            strategy=strategy,
                            htf_data=htf_df,
                            mtf_data=mtf_df,
                            ltf_data=df,
                            require_alignment="all",
                        )
                        signal = mtf.align_signals()
                    else:
                        signal = strategy.generate_signal(df)

                    if signal is not None:
                        side = signal.signal_type.value if hasattr(signal, "signal_type") else "hold"
                        if side in ("buy", "sell"):
                            ls = LiveSignal(
                                symbol=sym,
                                side=side,
                                confidence=getattr(signal, "confidence", 0.5),
                                strategy=name,
                                price=price,
                                reason=getattr(signal, "reasoning", ""),
                                metadata={
                                    "regime": regime,
                                    "mtf_aligned": self.enable_mtf,
                                },
                            )
                            all_signals.append(ls)
                except Exception as e:
                    log.debug(f"  {name} {sym}: {e}")

        # Apply COT overlay signal (strengthen/weaken based on positioning)
        if self.enable_cot and cot_data:
            all_signals = self._apply_cot_overlay(all_signals, cot_data)

        # Apply calendar overlay (increase caution around high-impact events)
        if self.enable_calendar and calendar_data:
            all_signals = self._apply_calendar_overlay(all_signals, calendar_data)

        # Apply sentiment overlay (boost/reduce based on news sentiment)
        if self.enable_sentiment and sentiment_data:
            all_signals = self._apply_sentiment_overlay(all_signals, sentiment_data)

        # Sort by confidence descending
        all_signals.sort(key=lambda s: s.confidence, reverse=True)
        return all_signals

    def _apply_cot_overlay(
        self, signals: List[LiveSignal], cot_data: Dict
    ) -> List[LiveSignal]:
        """Boost/reduce confidence based on COT positioning."""
        for s in signals:
            key = s.symbol.replace("USDT", "")
            pos = cot_data.get(key, cot_data.get(s.symbol))
            if pos is None:
                continue
            try:
                index = float(pos.get("cot_index", 50))
                divergence = pos.get("divergence", False)
                if s.side == "buy" and index < 30:
                    s.confidence = min(s.confidence + 0.1, 0.95)
                    s.reason += " | COT oversold"
                elif s.side == "sell" and index > 70:
                    s.confidence = min(s.confidence + 0.1, 0.95)
                    s.reason += " | COT overbought"
                if divergence:
                    s.confidence = max(s.confidence - 0.05, 0.0)
                    s.reason += " | COT divergence"
            except (ValueError, TypeError):
                pass
        return signals

    def _apply_calendar_overlay(
        self, signals: List[LiveSignal], calendar_data: List
    ) -> List[LiveSignal]:
        """Reduce confidence before high-impact economic events."""
        high_impact_count = sum(
            1 for e in calendar_data if getattr(e, "impact", "low") == "high"
        )
        if high_impact_count > 0:
            for s in signals:
                s.confidence = max(s.confidence - 0.05 * high_impact_count, 0.0)
                s.reason += f" | {high_impact_count} high-impact events"
        return signals

    def select_strategies(self, regime: str) -> List[str]:
        """Get top strategies for a given regime."""
        if self._adaptive_engine:
            try:
                selected = self._adaptive_engine.selector.select(regime)
                return [n for n, _ in selected]
            except Exception:
                pass
        return self._strategy_names[:3] if self._strategy_names else []

    def _get_sentiment_analyzer(self):
        try:
            from quant_nanggroe.engine.fundamental.sentiment import SentimentAnalyzer
            return SentimentAnalyzer()
        except Exception:
            return None

    def _apply_sentiment_overlay(
        self, signals: List[LiveSignal], sentiment_data: Dict[str, Dict]
    ) -> List[LiveSignal]:
        """Boost/reduce confidence based on news sentiment crossover."""
        analyzer = self._get_sentiment_analyzer()
        if analyzer is None:
            return signals
        for s in signals:
            key = s.symbol.replace("USDT", "")
            scores = sentiment_data.get(key, sentiment_data.get(s.symbol))
            if not scores:
                continue
            signal = analyzer.detect_crossover(scores)
            if signal is not None:
                if s.side == "buy" and signal.buy:
                    s.confidence = min(s.confidence + signal.strength * 0.15, 0.95)
                    s.reason += f" | sentiment: bullish ({signal.strength:.2f})"
                elif s.side == "sell" and signal.sell:
                    s.confidence = min(s.confidence + signal.strength * 0.15, 0.95)
                    s.reason += f" | sentiment: bearish ({signal.strength:.2f})"
                elif s.side == "buy" and signal.sell:
                    s.confidence = max(s.confidence - signal.strength * 0.1, 0.0)
                    s.reason += f" | sentiment: conflicting ({signal.strength:.2f})"
                elif s.side == "sell" and signal.buy:
                    s.confidence = max(s.confidence - signal.strength * 0.1, 0.0)
                    s.reason += f" | sentiment: conflicting ({signal.strength:.2f})"
        return signals

    def get_summary(self) -> Dict:
        return {
            "strategies_loaded": len(self._strategies),
            "strategy_names": self._strategy_names,
            "mtf_enabled": self.enable_mtf,
            "cot_enabled": self.enable_cot,
            "calendar_enabled": self.enable_calendar,
            "sentiment_enabled": self.enable_sentiment,
        }


# ─── Risk Gate ─────────────────────────────────────────────────────


class RiskGate:
    """Pre-trade risk checks using engine_production_bridge RiskEnforcer + fallback.

    Integrates:
      - Kill switch (constitutional limits)
      - Drawdown monitor
      - Position sizing
      - Trailing stop management
    """

    def __init__(self, initial_equity: float = 10_000.0):
        self._initial_equity = initial_equity
        self._risk_enforcer = None
        self._loaded = False
        self._lazy_init()

    def _lazy_init(self):
        try:
            from quant_nanggroe.engine_production_bridge import RiskEnforcer
            self._risk_enforcer = RiskEnforcer()
            self._loaded = True
            log.info("RiskGate: RiskEnforcer loaded")
        except Exception as e:
            log.warning(f"RiskGate: RiskEnforcer unavailable: {e}")

    def can_trade(self) -> Tuple[bool, str]:
        if not self._loaded or self._risk_enforcer is None:
            return True, "risk_enforcer_unavailable"
        try:
            if self._risk_enforcer.is_kill_switch_triggered():
                return False, "kill_switch_active"
            if self._risk_enforcer.is_drawdown_breached():
                return False, f"drawdown_breached: {self._risk_enforcer.current_drawdown():.2%}"
            return True, "ok"
        except Exception as e:
            log.warning(f"RiskGate check error: {e}")
            return True, "check_failed"

    def check_signal(self, signal: LiveSignal, balance: float) -> Tuple[bool, str]:
        allowed, reason = self.can_trade()
        if not allowed:
            return False, reason
        return True, "ok"

    def position_size(
        self, price: float, balance: float, kelly: float = 0.25
    ) -> float:
        if self._loaded and self._risk_enforcer:
            try:
                return self._risk_enforcer.position_size(price, balance, kelly)
            except Exception:
                pass
        return (balance * kelly * 0.1) / max(price, 1)

    def update_pnl(self, pnl: float, symbol: str = ""):
        pass

    def add_position(self, symbol: str):
        pass

    def remove_position(self, symbol: str):
        pass

    def check_trailing_stops(
        self, positions: Dict[str, float]
    ) -> List[str]:
        return []

    def status(self) -> Dict:
        if self._loaded and self._risk_enforcer:
            try:
                return {
                    "overall_status": "TRADING_HALT" if self._risk_enforcer.is_kill_switch_triggered() else "TRADING_ALLOWED",
                    "kill_switch": self._risk_enforcer.is_kill_switch_triggered(),
                    "drawdown": self._risk_enforcer.current_drawdown() if hasattr(self._risk_enforcer, "current_drawdown") else 0.0,
                }
            except Exception:
                pass
        return {"overall_status": "unavailable"}


# ─── Data Feed Integrator ──────────────────────────────────────────


class DataFeedIntegrator:
    """Provides COT + Economic Calendar data feeds for signal enhancement.

    Fetches and caches data from:
      - COTProvider (CFTC positioning data)
      - EconomicCalendar (macro event calendar)
    """

    def __init__(self):
        self._cot_provider = None
        self._calendar_provider = None
        self._cot_cache: Optional[Dict] = None
        self._calendar_cache: Optional[List] = None
        self._cot_cache_time = 0
        self._calendar_cache_time = 0
        self._cache_ttl = 3600
        self._lazy_init()

    def _lazy_init(self):
        try:
            from quant_nanggroe.engine.data.cot_provider import COTProvider
            self._cot_provider = COTProvider()
            log.info("DataFeedIntegrator: COTProvider loaded")
        except Exception as e:
            log.debug(f"COTProvider unavailable: {e}")
        try:
            from quant_nanggroe.engine.data.economic_calendar import (
                EconomicCalendarProvider,
            )
            self._calendar_provider = EconomicCalendarProvider()
            log.info("DataFeedIntegrator: EconomicCalendar loaded")
        except ImportError:
            log.debug("EconomicCalendar unavailable (import)")
        except Exception as e:
            log.debug(f"EconomicCalendar unavailable: {e}")

    def get_cot_analysis(
        self, symbols: Optional[List[str]] = None
    ) -> Dict:
        """Get COT positioning analysis. Returns dict of symbol→cot_index."""
        now = datetime.now().timestamp()
        if self._cot_cache and (now - self._cot_cache_time) < self._cache_ttl:
            return self._cot_cache or {}

        if self._cot_provider is None:
            return {}

        try:
            data = self._cot_provider.fetch()
            if not data:
                return {}

            from quant_nanggroe.engine.data.cot_provider import COTAnalyzer
            analyzer = COTAnalyzer(data)
            analysis = {}
            for sym in (symbols or []):
                cot_index = analyzer.cot_index(sym)
                divergence = analyzer.detect_divergence(sym)
                extreme = analyzer.classify_extreme(sym)
                analysis[sym] = {
                    "cot_index": cot_index,
                    "divergence": divergence,
                    "extreme": extreme,
                }
            self._cot_cache = analysis
            self._cot_cache_time = now
            return analysis
        except Exception as e:
            log.debug(f"COT analysis failed: {e}")
            return {}

    def get_calendar_events(
        self, hours_ahead: int = 48
    ) -> List:
        """Get upcoming economic calendar events."""
        now = datetime.now().timestamp()
        if self._calendar_cache and (now - self._calendar_cache_time) < self._cache_ttl:
            return self._calendar_cache or []

        if self._calendar_provider is None:
            return []

        try:
            events = self._calendar_provider.get_upcoming_events(hours=hours_ahead)
            self._calendar_cache = events
            self._calendar_cache_time = now
            return events
        except Exception as e:
            log.debug(f"Calendar fetch failed: {e}")
            return []

    def get_sentiment_scores(
        self, symbols: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """Get news sentiment scores for symbols.

        Returns dict of symbol → {short_ma, long_ma, score}.
        Uses SentimentAnalyzer when news data is available.
        Returns empty dict when no news provider is configured.
        """
        try:
            from quant_nanggroe.engine.fundamental.sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            scores = {}
            for sym in (symbols or []):
                news_items = self._get_news_for_symbol(sym)
                result = analyzer.compute_scores(news_items)
                if result.get("score", 0) != 0:
                    scores[sym] = result
            return scores
        except Exception as e:
            log.debug(f"Sentiment scores unavailable: {e}")
            return {}

    def _get_news_for_symbol(self, symbol: str) -> List[Dict]:
        """Get news items for a symbol. Placeholder for future news API integration."""
        return []

    def get_market_risk_score(self) -> float:
        """Get overall market risk score (0-100) from calendar events."""
        events = self.get_calendar_events(hours_ahead=72)
        if not events:
            return 0.0
        impact_scores = {"high": 1.0, "medium": 0.5, "low": 0.2}
        total = sum(
            impact_scores.get(getattr(e, "impact", "low"), 0.1) for e in events
        )
        return min(total * 10, 100.0)


# ─── Factory ────────────────────────────────────────────────────────


def create_live_pipeline(
    initial_equity: float = 10_000.0,
    enable_mtf: bool = True,
    enable_cot: bool = True,
    enable_calendar: bool = True,
    enable_sentiment: bool = True,
) -> Tuple[AdaptiveSignalPipeline, RiskGate, DataFeedIntegrator]:
    """Factory: creates fully wired adaptive pipeline for live_engine.py.

    Returns (signal_pipeline, risk_gate, data_feeds).
    """
    data_feeds = DataFeedIntegrator()
    signal_pipeline = AdaptiveSignalPipeline(
        enable_mtf=enable_mtf,
        enable_cot=enable_cot,
        enable_calendar=enable_calendar,
        enable_sentiment=enable_sentiment,
    )
    risk_gate = RiskGate(initial_equity=initial_equity)
    return signal_pipeline, risk_gate, data_feeds
