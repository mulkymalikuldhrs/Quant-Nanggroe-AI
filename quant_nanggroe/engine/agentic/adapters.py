"""
External Signal Adapters — bridge E:\\trading signal providers into QNA.

Each adapter wraps an external tool/project and returns a standardized Signal
that can be fed into the SignalVotingSystem.

Adapters:
- WyckoffAdapter: Wyckoff Volume Spread Analysis
- AIHFAdapter: ai-hedge-fund multi-agent
- HiddenRegimeAdapter: Hidden Regime detector
- TradingAgentsAdapter: TradingAgents multi-agent
- MultiTimeframeAdapter: QNA's own MTF analysis
"""
from __future__ import annotations

import importlib
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Optional

from quant_nanggroe.engine.agentic.voting import Bias, Signal

logger = logging.getLogger(__name__)

# External project paths
E_TRADING = "E:/trading"
E_AI_HEDGE_FUND = "E:/ai-hedge-fund"
E_HIDDEN_REGIME = "E:/hidden-regime"
E_TRADING_AGENTS = "E:/tradingagents"
E_AI_TRADER = "E:/AI-Trader"
E_LANG_ALPHA = "E:/LangAlpha"


class SignalAdapter:
    """Base class for external signal adapters."""

    source_name: str = "base"
    timeout: int = 15

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        """Fetch signal from external source. Returns None on failure."""
        raise NotImplementedError

    def _safe_import(self, module_path: str, module_name: str, attr: str = None):
        """Safely import from external project."""
        try:
            sys.path.insert(0, module_path)
            mod = importlib.import_module(module_name)
            if attr:
                return getattr(mod, attr)
            return mod
        except Exception as e:
            logger.debug("Import failed %s/%s: %s", module_path, module_name, e)
            return None
        finally:
            if module_path in sys.path:
                sys.path.remove(module_path)


class WyckoffAdapter(SignalAdapter):
    """Wyckoff Volume Spread Analysis — Sharpe 3.0 historical."""
    source_name = "wyckoff"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            # Try QNA's built-in Wyckoff first
            from quant_nanggroe.engine.strategy.strategies.wyckoff_strategy import WyckoffStrategy
            df = kwargs.get("dataframe")
            if df is None or len(df) < 60:
                return None
            strat = WyckoffStrategy(lookback=50, volume_mult=1.3)
            signals = strat.generate_signals(df)
            last = signals.iloc[-1]
            if last.get("entry", 0) == 1:
                return Signal(Bias.BUY, 0.65, self.source_name)
            if last.get("entry", 0) == -1:
                return Signal(Bias.SELL, 0.65, self.source_name)
            return Signal(Bias.NEUTRAL, 0.0, self.source_name)
        except Exception as e:
            logger.debug("Wyckoff failed: %s", e)
            return None


class AIHFAdapter(SignalAdapter):
    """AI Hedge Fund — multi-agent analysis."""
    source_name = "aihf"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            mod = self._safe_import(E_AI_HEDGE_FUND, "src.main", "run_hedge_fund")
            if mod is None:
                return None
            result = mod({"symbol": symbol})
            decision = result.get("decision", "hold")
            confidence = result.get("confidence", 0.5)
            if decision == "hold":
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)
            bias = Bias.BUY if decision == "buy" else Bias.SELL
            return Signal(bias, confidence, self.source_name)
        except Exception as e:
            logger.debug("AIHF failed: %s", e)
            return None


class HiddenRegimeAdapter(SignalAdapter):
    """Hidden Regime detector — HMM-based regime classification."""
    source_name = "hidden_regime"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            mod = self._safe_import(E_HIDDEN_REGIME, "hidden_regime", "create_financial_pipeline")
            if mod is None:
                return None
            pipeline = mod()
            result = pipeline.run(symbol)
            regime = result.get("regime", "neutral")
            confidence = result.get("confidence", 0.3)
            regime_map = {"bull": Bias.BUY, "bear": Bias.SELL}
            bias = regime_map.get(regime, Bias.NEUTRAL)
            return Signal(bias, confidence, self.source_name)
        except Exception as e:
            logger.debug("HiddenRegime failed: %s", e)
            return None


class TradingAgentsAdapter(SignalAdapter):
    """TradingAgents — LangGraph multi-agent decision."""
    source_name = "tradingagents"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            mod = self._safe_import(E_TRADING_AGENTS, "tradingagents.graph.trading_graph", "TradingAgentsGraph")
            config_mod = self._safe_import(E_TRADING_AGENTS, "tradingagents.default_config", "DEFAULT_CONFIG")
            if mod is None or config_mod is None:
                return None
            today = datetime.now().strftime("%Y-%m-%d")
            ta = mod(debug=False, config=config_mod.copy())
            _, decision = ta.propagate(symbol.replace("EURUSD", "EURUSD=X"), today)
            if isinstance(decision, dict):
                action = decision.get("action", "hold")
                if action == "hold":
                    return Signal(Bias.NEUTRAL, 0.0, self.source_name)
                bias = Bias.BUY if action == "buy" else Bias.SELL
                return Signal(bias, 0.5, self.source_name)
            return Signal(Bias.NEUTRAL, 0.0, self.source_name)
        except Exception as e:
            logger.debug("TradingAgents failed: %s", e)
            return None


class MultiTimeframeAdapter(SignalAdapter):
    """QNA's own multi-timeframe analysis."""
    source_name = "mtf"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            from quant_nanggroe.engine.strategy.multi_timeframe import MultiTimeframeAnalyzer
            df = kwargs.get("dataframe")
            if df is None:
                return None
            analyzer = MultiTimeframeAnalyzer()
            result = analyzer.analyze(df, symbol)
            direction = result.get("direction", "neutral")
            confidence = result.get("confidence", 0.0)
            if direction == "neutral":
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)
            bias = Bias.BUY if direction == "bullish" else Bias.SELL
            return Signal(bias, confidence, self.source_name)
        except Exception as e:
            logger.debug("MTF failed: %s", e)
            return None


# ── Registry of all adapters ──
ALL_ADAPTERS: list[SignalAdapter] = [
    WyckoffAdapter(),
    AIHFAdapter(),
    HiddenRegimeAdapter(),
    TradingAgentsAdapter(),
    MultiTimeframeAdapter(),
]


def fetch_all_signals(symbol: str, dataframe=None, adapters: list[SignalAdapter] | None = None) -> list[Signal]:
    """Fetch signals from all registered adapters.

    Args:
        symbol: Trading symbol (e.g., "EURUSD")
        dataframe: Optional OHLCV dataframe for adapters that need it
        adapters: Override adapter list (default: ALL_ADAPTERS)

    Returns:
        List of non-None signals
    """
    active = adapters or ALL_ADAPTERS
    signals = []
    for adapter in active:
        try:
            sig = adapter.fetch_signal(symbol, dataframe=dataframe)
            if sig is not None:
                signals.append(sig)
                logger.info("Signal from %s: %s (conf=%.2f)", adapter.source_name, sig.bias.value, sig.confidence)
        except Exception as e:
            logger.warning("Adapter %s failed: %s", adapter.source_name, e)
    return signals
