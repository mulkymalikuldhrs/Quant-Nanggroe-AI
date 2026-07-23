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
from dataclasses import dataclass
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
            from quant_nanggroe.engine.strategies.wyckoff import WyckoffStrategy
            from quant_nanggroe.engine.strategies.base import StrategyParameters, SignalDirection
            df = kwargs.get("dataframe")
            if df is None or len(df) < 60:
                return None
            strat = WyckoffStrategy(parameters=StrategyParameters(params={"lookback": 50, "volume_threshold": 1.3}))
            signal = strat.generate_signal(df)
            if signal.direction == SignalDirection.BUY:
                return Signal(Bias.BUY, signal.confidence or 0.65, self.source_name)
            if signal.direction == SignalDirection.SELL:
                return Signal(Bias.SELL, signal.confidence or 0.65, self.source_name)
            return Signal(Bias.NEUTRAL, 0.0, self.source_name)
        except Exception as e:
            logger.debug("Wyckoff failed: %s", e)
            return None


class AIHFAdapter(SignalAdapter):
    """AI Hedge Fund — multi-agent analysis via run_hedge_fund()."""
    source_name = "aihf"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            mod = self._safe_import(E_AI_HEDGE_FUND, "src.main", "run_hedge_fund")
            if mod is None:
                return None
            from datetime import datetime, timedelta

            end = datetime.now()
            start = end - timedelta(days=365)
            result = mod(
                tickers=[symbol],
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
                portfolio={"cash": 100000},
            )
            # result: {"decisions": {ticker: {action, quantity, confidence, reasoning}}, "analyst_signals": ...}
            decisions = result.get("decisions", {})
            ticker_dec = decisions.get(symbol, {})
            action = ticker_dec.get("action", "hold")
            confidence = ticker_dec.get("confidence", 50) / 100.0  # 0-100 → 0-1
            if action == "hold":
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)
            bias = Bias.BUY if action in ("buy",) else Bias.SELL
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


# ── TradingAgents rating mapping & cost-guard ──────────────────────────────
# propagate() returns (final_state, rating_string) where rating_string is the
# 5-tier scale produced by process_signal → parse_rating:
#   Buy / Overweight / Hold / Underweight / Sell
# NOTE: it is a STRING, not a dict. The old code did decision.get("action") on a
# str → AttributeError every call → swallowed → always NEUTRAL (dead adapter).
_TA_RATING_TO_BIAS: dict[str, Bias] = {
    "buy": Bias.BUY,
    "overweight": Bias.BUY,
    "hold": Bias.NEUTRAL,
    "underweight": Bias.SELL,
    "sell": Bias.SELL,
}


def _map_ta_rating(rating: Any) -> tuple[Bias, float]:
    """Map a TradingAgents 5-tier rating string to (Bias, confidence)."""
    if not isinstance(rating, str):
        return Bias.NEUTRAL, 0.0
    bias = _TA_RATING_TO_BIAS.get(rating.strip().lower(), Bias.NEUTRAL)
    # Directional calls get a firm confidence; Hold maps to NEUTRAL/0.0.
    return bias, (0.5 if bias != Bias.NEUTRAL else 0.0)


# Providers treated as FREE (self-hosted / local / open). Everything else is
# treated as PAID and blocked unless explicitly opted in — fail-closed.
_TA_FREE_PROVIDERS = {"ollama", "local", "huggingface", "vllm", "litellm"}


def _ta_should_block(config: dict[str, Any] | None) -> bool:
    """Return True if TradingAgents would bill a paid LLM and we must NOT call it.

    Fail-closed: only an explicit FREE provider is allowed; any cloud/unknown
    provider is treated as paid unless the operator opts in via
    QNA_ALLOW_PAID_LLM=1/true/yes.
    """
    if os.environ.get("QNA_ALLOW_PAID_LLM", "").strip().lower() in {"1", "true", "yes"}:
        return False
    provider = (config or {}).get("llm_provider", "openai")
    return provider not in _TA_FREE_PROVIDERS


class TradingAgentsAdapter(SignalAdapter):
    """TradingAgents — LangGraph multi-agent decision (2nd-opinion source)."""

    source_name = "tradingagents"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            mod = self._safe_import(E_TRADING_AGENTS, "tradingagents.graph.trading_graph", "TradingAgentsGraph")
            config_mod = self._safe_import(E_TRADING_AGENTS, "tradingagents.default_config", "DEFAULT_CONFIG")
            if mod is None or config_mod is None:
                return None
            cfg = config_mod.copy()
            # No-paid-API guard: never silently bill a cloud LLM.
            if _ta_should_block(cfg):
                logger.info(
                    "TradingAgentsAdapter disabled: paid LLM provider '%s' blocked by QNA_ALLOW_PAID_LLM guard",
                    cfg.get("llm_provider"),
                )
                return None
            today = datetime.now().strftime("%Y-%m-%d")
            ta = mod(debug=False, config=cfg)
            # propagate() returns (final_state, rating_string) — NOT a dict.
            result = ta.propagate(symbol.replace("EURUSD", "EURUSD=X"), today)
            rating = result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else result
            bias, conf = _map_ta_rating(rating)
            if bias == Bias.NEUTRAL:
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)
            return Signal(bias, conf, self.source_name)
        except Exception as e:
            logger.debug("TradingAgents failed: %s", e)
            return None


@dataclass
class ValidationVerdict:
    """Outcome of the 2nd-opinion cross-check."""

    status: str  # confirm | contradict | neutral | abstain
    signal: "Signal | None"
    reason: str


class TradingAgentsValidator:
    """2nd-opinion arbitrator.

    Cross-checks the primary consensus (VoteResult) against the independent
    TradingAgents signal. It does NOT join the pooled vote — it only CONFIRMs,
    CONTRADICTs, or ABSTAINS. This guarantees a broken/disabled external model
    can never silently swing a trade: worst case it abstains.
    """

    source_name = "tradingagents"

    def __init__(self, adapter: SignalAdapter | None = None):
        self.adapter = adapter or TradingAgentsAdapter()

    def evaluate(self, primary: "VoteResult", symbol: str) -> ValidationVerdict:
        sig = self.adapter.fetch_signal(symbol)
        if sig is None:
            return ValidationVerdict(
                "abstain", None, "tradingagents unavailable/disabled (paid-LLM guard or import failure)"
            )
        if sig.bias == Bias.NEUTRAL:
            return ValidationVerdict("neutral", sig, "tradingagents neutral")
        if sig.bias == primary.final_bias:
            return ValidationVerdict("confirm", sig, f"agreement with primary {primary.final_bias.value}")
        return ValidationVerdict(
            "contradict", sig, f"disagreement: ext={sig.bias.value} primary={primary.final_bias.value}"
        )


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
