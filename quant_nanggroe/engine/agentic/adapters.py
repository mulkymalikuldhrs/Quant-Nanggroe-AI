"""
External Signal Adapters — bridge E:\\trading signal providers into QNA.

Each adapter wraps an external tool/project and returns a standardized Signal
that can be fed into the SignalVotingSystem.

Adapters:
- WyckoffAdapter: Wyckoff Volume Spread Analysis
- AIHFAdapter: ai-hedge-fund multi-agent (E:/ai-hedge-fund)
- HiddenRegimeAdapter: Hidden Regime detector (E:/hidden-regime)
- TradingAgentsAdapter: TradingAgents multi-agent (E:/tradingagents)
- AITraderAdapter: AI-Trader social/agent signals (E:/AI-Trader)
- LangAlphaAdapter: LangAlpha fundamental/macro/analysis (E:/LangAlpha)
- MultiTimeframeAdapter: QNA's own MTF analysis
"""
from __future__ import annotations

import importlib
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quant_nanggroe.engine.agentic.voting import Bias, Signal

logger = logging.getLogger(__name__)

# External project paths — auto-detect via env vars, fallback to known locations
import pathlib as _pl

_REPO = _pl.Path(__file__).resolve().parent.parent.parent.parent

def _ext(name: str, fallback: str) -> str:
    return os.environ.get(f"QNA_EXT_{name.upper()}", fallback)

E_TRADING = _ext("trading", str(_REPO))
E_AI_HEDGE_FUND = _ext("ai_hedge_fund", "E:/ai-hedge-fund")
E_HIDDEN_REGIME = _ext("hidden_regime", "E:/hidden-regime")
E_TRADING_AGENTS = _ext("trading_agents", "E:/tradingagents")
E_AI_TRADER = _ext("ai_trader", "E:/AI-Trader")
E_LANG_ALPHA = _ext("lang_alpha", "E:/LangAlpha")


class SignalAdapter:
    """Base class for external signal adapters."""

    source_name: str = "base"
    timeout: int = 15

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        """Fetch signal from external source. Returns None on failure."""
        raise NotImplementedError  # intentional: abstract — subclasses implement per-source logic

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
            from quant_nanggroe.engine.strategies.base import SignalDirection, StrategyParameters
            from quant_nanggroe.engine.strategies.wyckoff import WyckoffStrategy
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
    """Hidden Regime detector — HMM-based regime classification via hidden_regime_mcp.detect_regime.

    Uses the correct pipeline API:
      create_financial_pipeline(ticker=..., include_report=False)
      pipeline.update()  # trains HMM
      pipeline.interpreter_output.iloc[-1]  # latest regime data
    """
    source_name = "hidden_regime"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            # First try the MCP server's detect_regime (async → asyncio.run)
            mod = self._safe_import(E_HIDDEN_REGIME, "hidden_regime_mcp.tools", "detect_regime")
            if mod is not None:
                import asyncio
                result = asyncio.run(mod(ticker=symbol, n_states=3))
                regime = result.get("current_regime", "neutral")
                confidence = result.get("confidence", 0.3)
                regime_map = {"bullish": Bias.BUY, "bearish": Bias.SELL, "crisis": Bias.SELL}
                bias = regime_map.get(regime, Bias.NEUTRAL)
                return Signal(bias, confidence, self.source_name)

            # Fallback: direct pipeline import (synchronous)
            create_fn = self._safe_import(E_HIDDEN_REGIME, "hidden_regime", "create_financial_pipeline")
            if create_fn is None:
                return None
            pipeline = create_fn(ticker=symbol, n_states=3, include_report=False)
            pipeline.update()  # returns markdown string, but interpreter_output has the data
            latest = pipeline.interpreter_output.iloc[-1]
            regime_label = str(latest.get("regime_label", latest.get("regime_name", "neutral"))).lower()
            confidence = float(latest.get("confidence", 0.3))
            # Normalise labels: "bull" → "bullish", "bear" → "bearish"
            label_map = {"bull": "bullish", "bear": "bearish"}
            regime = label_map.get(regime_label, regime_label)
            regime_map = {"bullish": Bias.BUY, "bearish": Bias.SELL, "crisis": Bias.SELL}
            bias = regime_map.get(regime, Bias.NEUTRAL)
            return Signal(bias, min(confidence, 1.0), self.source_name)
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
    TradingAgents signal. It does NOT join the pooled vote — it only CONFIRMS,
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
    """QNA's own multi-timeframe analysis — delegates to registered
    MultiTimeframeStrategy (core ensemble path).  Also kept as external
    adapter for backward compatibility."""
    source_name = "mtf"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            from quant_nanggroe.engine.strategies.base import (
                SignalDirection,
            )
            from quant_nanggroe.engine.strategies.multi_timeframe_strategy import (
                MultiTimeframeStrategy,
            )
            df = kwargs.get("dataframe")
            if df is None or (hasattr(df, 'empty') and df.empty):
                return None
            if hasattr(df, 'iloc') and len(df) < 55:
                return None
            strat = MultiTimeframeStrategy()
            signal = strat.generate_signal(df, symbol=symbol)
            if signal.direction == SignalDirection.BUY:
                return Signal(Bias.BUY, signal.confidence, self.source_name)
            if signal.direction == SignalDirection.SELL:
                return Signal(Bias.SELL, signal.confidence, self.source_name)
            return Signal(Bias.NEUTRAL, 0.0, self.source_name)
        except Exception as e:
            logger.debug("MTF adapter failed: %s", e)
            return None


class AITraderAdapter(SignalAdapter):
    """AI-Trader — social/agent trading signals via HTTP API.

    Connects to AI-Trader's FastAPI backend (E:/AI-Trader/service/server).
    Queries public endpoints for signal feed and trending data.
    Fallthroughed by database-level access when API is unavailable.
    """
    source_name = "aitrader"

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        # Strategy 1: HTTP calls to running AI-Trader API
        try:
            import httpx
            base_url = os.environ.get("AI_TRADER_BASE_URL", "http://localhost:8080")
            with httpx.Client(timeout=self.timeout) as client:
                # 1a: Signal feed — recent signals across all agents
                resp = client.get(f"{base_url}/api/signals/feed", params={"limit": 20})
                if resp.status_code == 200:
                    data = resp.json()
                    signals = data if isinstance(data, list) else data.get("signals", data.get("data", []))
                    for sig in signals:
                        sym = str(sig.get("symbol", "")).upper()
                        if sym == symbol.upper():
                            action = str(sig.get("action", "")).lower()
                            confidence = min(float(sig.get("confidence", 50)) / 100.0, 1.0)
                            action_map = {"buy": Bias.BUY, "sell": Bias.SELL, "short": Bias.SELL}
                            bias = action_map.get(action, Bias.NEUTRAL)
                            if bias != Bias.NEUTRAL:
                                return Signal(bias, confidence, self.source_name)

                # 1b: Trending symbols — if symbol is trending, bias direction
                resp = client.get(f"{base_url}/api/trending")
                if resp.status_code == 200:
                    trend_data = resp.json()
                    entries = trend_data if isinstance(trend_data, list) else trend_data.get("trending", [])
                    for entry in entries:
                        sym = str(entry.get("symbol", entry.get("ticker", ""))).upper()
                        if sym == symbol.upper():
                            direction = str(entry.get("direction", "")).lower()
                            score = float(entry.get("score", entry.get("confidence", 0.5)))
                            if direction in ("up", "bullish"):
                                return Signal(Bias.BUY, min(score, 0.8), self.source_name)
                            if direction in ("down", "bearish"):
                                return Signal(Bias.SELL, min(score, 0.8), self.source_name)
        except Exception:
            pass

        # Strategy 2: direct database query via AI-Trader's SQLite backend
        try:
            db_path = os.path.join(E_AI_TRADER, "service", "server", "data", "clawtrader.db")
            if os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """
                        SELECT action, confidence, created_at
                        FROM signals
                        WHERE UPPER(symbol) = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (symbol.upper(),),
                    )
                    row = cursor.fetchone()
                    if row:
                        action = str(row["action"]).lower()
                        confidence = min(float(row.get("confidence", 50)) / 100.0, 1.0)
                        action_map = {"buy": Bias.BUY, "sell": Bias.SELL, "short": Bias.SELL}
                        bias = action_map.get(action, Bias.NEUTRAL)
                        if bias != Bias.NEUTRAL:
                            return Signal(bias, confidence, self.source_name)
                except sqlite3.OperationalError:
                    # Table may not exist — AI-Trader schema may differ
                    pass
                finally:
                    conn.close()
        except Exception:
            pass

        return None


class LangAlphaAdapter(SignalAdapter):
    """LangAlpha — fundamental/macro/analysis signals via MCP servers.

    Aggregates signals from multiple LangAlpha MCP servers into a single
    weighted vote. Each source is independently caught so one failure
    never blocks the others.

    Sources:
    - yf_analysis_mcp_server: analyst recommendations consensus
    - fundamentals_mcp_server: financial ratios (PE, PB valuation)
    - macro_mcp_server: market risk premium for macro regime
    """
    source_name = "langalpha"

    def __init__(self) -> None:
        super().__init__()
        self._import_cache: dict[str, object] = {}

    def _lazy_import(self, attr: str):
        """Lazy-import an MCP tool once, cache per instance."""
        if attr in self._import_cache:
            return self._import_cache[attr]
        _MAP = {
            "get_analyst_recommendations": ("mcp_servers.yf_analysis_mcp_server", "get_analyst_recommendations"),
            "get_financial_ratios": ("mcp_servers.fundamentals_mcp_server", "get_financial_ratios"),
            "get_market_risk_premium": ("mcp_servers.macro_mcp_server", "get_market_risk_premium"),
        }
        if attr not in _MAP:
            return None
        mod_name, func_name = _MAP[attr]
        mod = self._safe_import(E_LANG_ALPHA, mod_name, func_name)
        self._import_cache[attr] = mod
        return mod

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            signals: list[tuple[Bias, float]] = []

            # ── Source 1: Analyst Recommendations ──
            try:
                fn = self._lazy_import("get_analyst_recommendations")
                if fn is not None:
                    import asyncio
                    recs = asyncio.run(fn(symbol))
                    if recs and isinstance(recs, dict):
                        # recs keyed by period string e.g. "2026-06-30"
                        periods = [k for k in recs if k != "symbol"]
                        if periods:
                            latest_key = max(periods)
                            period = recs[latest_key]
                            sb = int(period.get("strongBuy", 0))
                            b = int(period.get("buy", 0))
                            h = int(period.get("hold", 0))
                            s = int(period.get("sell", 0))
                            ss = int(period.get("strongSell", 0))
                            total = sb + b + h + s + ss
                            if total > 0:
                                net = (sb + b - s - ss) / total
                                if abs(net) > 0.1:
                                    signals.append((Bias.BUY if net > 0 else Bias.SELL, abs(net) * 0.7))
            except Exception:
                pass

            # ── Source 2: Financial Ratios / Valuation ──
            try:
                fn = self._lazy_import("get_financial_ratios")
                if fn is not None:
                    import asyncio
                    ratios = asyncio.run(fn(symbol))
                    if ratios and isinstance(ratios, dict):
                        pe = ratios.get("priceEarningsRatio")
                        pb = ratios.get("priceBookValueRatio")
                        if pe is not None and isinstance(pe, (int, float)) and pe > 0:
                            if pe > 50:
                                signals.append((Bias.SELL, 0.3))
                            elif pe < 10:
                                signals.append((Bias.BUY, 0.3))
                        if pb is not None and isinstance(pb, (int, float)) and pb > 0:
                            if pb > 10:
                                signals.append((Bias.SELL, 0.25))
                            elif pb < 1:
                                signals.append((Bias.BUY, 0.25))
            except Exception:
                pass

            # ── Source 3: Macro Risk Premium ──
            try:
                fn = self._lazy_import("get_market_risk_premium")
                if fn is not None:
                    import asyncio
                    premium = asyncio.run(fn("US"))
                    if premium is not None and isinstance(premium, (int, float)):
                        if premium > 0.05:
                            signals.append((Bias.SELL, 0.2))
            except Exception:
                pass

            # ── Aggregate ──
            if not signals:
                return None

            buy_w = sum(c for b, c in signals if b == Bias.BUY)
            sell_w = sum(c for b, c in signals if b == Bias.SELL)
            total_w = buy_w + sell_w

            if total_w < 0.15:
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)

            if buy_w > sell_w:
                return Signal(Bias.BUY, min(buy_w / total_w, 0.8), self.source_name)
            return Signal(Bias.SELL, min(sell_w / total_w, 0.8), self.source_name)

        except Exception as e:
            logger.debug("LangAlpha failed: %s", e)
            return None


class SmcAdapter(SignalAdapter):
    """SMC Agent — Smart Money Concepts detector signals.

    Uses the three core SMC detectors (OrderBlock, FairValueGap, LiquidityLevel)
    directly — no LLM needed.  Combines detector output into a signal.
    """
    source_name = "smc_agent"
    timeout = 10

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            df = kwargs.get("dataframe")
            if df is None:
                return None

            from quant_nanggroe.agents.smc.enhanced import (
                FairValueGapDetector,
                LiquidityLevelDetector,
                OrderBlockDetector,
            )

            # Build list-of-dicts format expected by SMC detectors
            if hasattr(df, "to_dict"):
                records = df.tail(60).to_dict("records")
            elif isinstance(df, dict):
                n = len(df.get("close", []))
                records = [
                    {
                        "open": float(df["open"][i]) if isinstance(df.get("open"), (list, tuple)) else 0,
                        "high": float(df["high"][i]) if isinstance(df.get("high"), (list, tuple)) else 0,
                        "low": float(df["low"][i]) if isinstance(df.get("low"), (list, tuple)) else 0,
                        "close": float(df["close"][i]),
                        "volume": float(df["volume"][i]) if isinstance(df.get("volume"), (list, tuple)) else 0,
                    }
                    for i in range(min(n, 60))
                ]
            else:
                return None

            if len(records) < 5:
                return None

            ob_detector = OrderBlockDetector()
            fvg_detector = FairValueGapDetector()
            liq_detector = LiquidityLevelDetector()

            order_blocks = ob_detector.detect(records)
            fvgs = fvg_detector.detect(records)
            liquidity = liq_detector.detect(records)

            # Aggregate patterns into bias
            bullish_count = 0.0
            bearish_count = 0.0

            for ob in order_blocks:
                if ob.ob_type == "bullish_ob":
                    bullish_count += ob.strength
                else:
                    bearish_count += ob.strength

            for fvg in fvgs:
                if fvg.fvg_type == "bullish_fvg":
                    bullish_count += 1.0
                else:
                    bearish_count += 1.0

            for liq in liquidity:
                if liq.liq_type == "sell_side":
                    bullish_count += liq.strength * 0.5
                else:
                    bearish_count += liq.strength * 0.5

            total = bullish_count + bearish_count
            if total < 0.5:
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)

            if bullish_count > bearish_count:
                confidence = min(bullish_count / total, 0.85)
                return Signal(Bias.BUY, confidence, self.source_name)
            elif bearish_count > bullish_count:
                confidence = min(bearish_count / total, 0.85)
                return Signal(Bias.SELL, confidence, self.source_name)

            return Signal(Bias.NEUTRAL, 0.0, self.source_name)

        except Exception as exc:
            logger.debug("SmcAdapter failed: %s", exc)
            return None


class TradingAdapter(SignalAdapter):
    """QNA internal strategy consensus adapter.

    Aggregates signals from registered strategies via StrategyRegistry
    to produce a consensus bias signal.
    """
    source_name = "trading"
    timeout = 15

    def fetch_signal(self, symbol: str, **kwargs) -> Signal | None:
        try:
            dataframe = kwargs.get("dataframe")
            if dataframe is None or dataframe.empty:
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)
            from quant_nanggroe.engine.strategies.registry import StrategyRegistry
            strategies = StrategyRegistry.create_all()
            if not strategies:
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)
            buy_score = 0.0
            sell_score = 0.0
            count = 0
            for strat in strategies[:20]:  # limit to avoid timeout
                try:
                    sig = strat.generate_signal(dataframe, symbol=symbol)
                    if sig is None:
                        continue
                    direction = sig.direction.value if hasattr(sig, "direction") else "hold"
                    conf = float(getattr(sig, "confidence", 0.0))
                    if direction == "buy":
                        buy_score += conf
                    elif direction == "sell":
                        sell_score += conf
                    count += 1
                except Exception:
                    continue
            if count == 0 or (buy_score == 0 and sell_score == 0):
                return Signal(Bias.NEUTRAL, 0.0, self.source_name)
            total = buy_score + sell_score
            if buy_score > sell_score:
                return Signal(Bias.BUY, min(buy_score / max(total, 1), 0.85), self.source_name)
            elif sell_score > buy_score:
                return Signal(Bias.SELL, min(sell_score / max(total, 1), 0.85), self.source_name)
            return Signal(Bias.NEUTRAL, 0.0, self.source_name)
        except Exception as exc:
            logger.debug("TradingAdapter failed: %s", exc)
            return None


# ── Registry of all adapters ──
ALL_ADAPTERS: list[SignalAdapter] = [
    WyckoffAdapter(),
    AIHFAdapter(),
    HiddenRegimeAdapter(),
    AITraderAdapter(),
    LangAlphaAdapter(),
    TradingAgentsAdapter(),
    MultiTimeframeAdapter(),
    SmcAdapter(),
    TradingAdapter(),
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
