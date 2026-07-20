"""Autonomous Agent System — LLM-routed, self-correcting, auto-discovering.

Integrates with the existing QNAI infrastructure:
  - LLMRouter (engine/llm_router.py) — extended with free providers
  - Strategy registry (engine/strategy/strategies/) — auto-discovered
  - Agentic trading (engine/agentic_trading.py) — consensus engine
  - Strategy lifecycle (engine/strategy_lifecycle.py) — darwinian management
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. FREE LLM PROVIDER CONFIGS — extend the existing LLMRouter
# ---------------------------------------------------------------------------
# All OpenAI-compatible, so we reuse ChatOpenAI with custom base_url.
# ponytail: reuse the router's _call_openai path via ChatOpenAI.

FREE_PROVIDERS: dict[str, dict[str, Any]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": {"deep_thinking": "llama-3.3-70b-versatile", "standard": "llama3-70b-8192", "quick": "llama3-8b-8192"},
        "api_key_env": "GROQ_API_KEY",
        "priority": 10,  # lower = tried first
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "models": {"deep_thinking": "deepseek-chat", "standard": "deepseek-chat", "quick": "deepseek-chat"},
        "api_key_env": "DEEPSEEK_API_KEY",
        "priority": 20,
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/v1",
        "models": {"deep_thinking": "meta-llama/Meta-Llama-3-70B-Instruct", "standard": "Qwen/Qwen2.5-72B-Instruct", "quick": "microsoft/Phi-3-mini-4k-instruct"},
        "api_key_env": "HUGGINGFACE_API_KEY",
        "priority": 30,
    },
    "nous": {
        "base_url": "https://api.nousresearch.com/v1",
        "models": {"deep_thinking": "hermes-3-llama-3.1-70b", "standard": "hermes-3-llama-3.1-70b", "quick": "hermes-3-llama-3.1-8b"},
        "api_key_env": "NOUS_API_KEY",
        "priority": 40,
    },
}


def register_free_providers(router) -> None:
    """Register free LLM providers into an existing LLMRouter instance.

    Only registers providers whose API key is available (env var or empty for
    services that work without one). Reuses the router's ProviderConfig model.

    Usage:
        from quant_nanggroe.engine.llm_router import get_llm_router
        router = get_llm_router()
        register_free_providers(router)
    """
    from quant_nanggroe.engine.llm_router import LLMProvider, ModelTier, ProviderConfig

    for name, cfg in FREE_PROVIDERS.items():
        api_key = os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            logger.info("Skipping free provider %s: no %s env var", name, cfg["api_key_env"])
            continue

        try:
            provider_enum = LLMProvider(name.upper())
        except ValueError:
            # Create a string-based provider; router dispatches via ChatOpenAI
            # ponytail: we handle this in the chat call by using _call_openai path
            provider_enum = None

        models_map = {}
        for tier_str, model_name in cfg["models"].items():
            tier = ModelTier(tier_str)
            models_map[tier] = model_name

        config = ProviderConfig(
            provider=provider_enum or name,
            api_key=api_key,
            base_url=cfg["base_url"],
            models=models_map,
            priority=cfg["priority"],
            enabled=True,
        )
        router.add_provider(config)
        logger.info("Registered free provider: %s (key ends with ...%s)", name, api_key[-4:])


# ---------------------------------------------------------------------------
# 2. STRATEGY AUTO-DISCOVERY — scan a directory for strategy modules
# ---------------------------------------------------------------------------
# ponytail: complements the manual __init__.py + _NAME_MAP pattern.
# This discovers .py files that export a class ending in "Strategy".


def discover_strategies(
    directory: str | None = None,
    base_class: type | None = None,
) -> dict[str, type]:
    """Auto-discover strategy classes from a directory.

    Scans all .py files (except __init__.py) under *directory*, imports each,
    and collects classes that:
      - Are defined in that file (not imported)
      - End with 'Strategy' (or match *base_class*)

    Returns dict of {snake_case_name: class}.

    Args:
        directory: Path to scan. Defaults to the existing strategies dir.
        base_class: Optional base class filter.

    Returns:
        {name: class} mapping of discovered strategies.
    """
    if directory is None:
        dir_path = Path(__file__).resolve().parent.parent / "strategy" / "strategies"
    else:
        dir_path = Path(directory)

    if not dir_path.is_dir():
        logger.warning("Strategy directory not found: %s", dir_path)
        return {}

    discovered: dict[str, type] = {}

    for fpath in sorted(dir_path.iterdir()):
        if fpath.suffix != ".py" or fpath.name == "__init__.py":
            continue
        mod_name = fpath.stem
        try:
            mod = importlib.import_module(f"quant_nanggroe.engine.strategy.strategies.{mod_name}")
        except Exception as exc:
            logger.debug("Skipping %s: %s", mod_name, exc)
            continue

        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ != mod.__name__:
                continue  # only classes defined in this file
            if base_class is not None and not issubclass(obj, base_class):
                continue
            if base_class is None and not name.endswith("Strategy"):
                continue
            snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")
            discovered[snake] = obj

    logger.info("Auto-discovered %d strategies from %s", len(discovered), dir_path)
    return discovered


# ---------------------------------------------------------------------------
# 3. SELF-CORRECTION — lesson recording + reflection
# ---------------------------------------------------------------------------
# ponytail: file-based persistence, no DB dependency.

class LessonSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Lesson:
    """A recorded lesson from a system failure or observation."""
    id: str = ""
    category: str = ""           # e.g. "provider_failover", "strategy_load", "signal_gen"
    severity: LessonSeverity = LessonSeverity.INFO
    summary: str = ""            # one-line summary
    detail: str = ""             # what happened
    context: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = ""
    resolved: bool = False
    resolution: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        if not self.occurred_at:
            self.occurred_at = datetime.now(timezone.utc).isoformat()


class SelfCorrection:
    """Record, retrieve, and learn from lessons.

    Persists lessons to a JSON file. Provides:
      - record(): save a lesson
      - get_prompt(): generate a system prompt with recent failures
      - resolve(): mark a lesson as resolved
    """

    def __init__(self, lesson_path: str | None = None):
        if lesson_path is None:
            base = Path(__file__).resolve().parent.parent.parent
            self._path = base / "data" / "lessons.json"
        else:
            self._path = Path(lesson_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lessons: list[Lesson] = []
        self._load()

    # ── public API ──────────────────────────────────────────────────

    def record(
        self,
        category: str,
        summary: str,
        detail: str = "",
        severity: LessonSeverity = LessonSeverity.INFO,
        context: dict[str, Any] | None = None,
    ) -> Lesson:
        """Record a new lesson."""
        lesson = Lesson(
            category=category,
            severity=severity,
            summary=summary,
            detail=detail,
            context=context or {},
        )
        self._lessons.append(lesson)
        self._save()
        logger.info("Lesson recorded: [%s] %s — %s", lesson.category, lesson.summary, lesson.detail[:80])
        return lesson

    def get_prompt(self, max_lessons: int = 5, severity_min: LessonSeverity = LessonSeverity.WARNING) -> str:
        """Build a system-prompt snippet from recent unresolved lessons.

        Use this to inject lessons into the agent's context so it can
        avoid repeating mistakes.
        """
        # ponytail: severity order for string-safe filtering
        _SEVERITY_ORDER = {"critical": 4, "error": 3, "warning": 2, "info": 1}
        min_level = _SEVERITY_ORDER.get(severity_min.value, 2)

        unresolved = [l for l in self._lessons if not l.resolved]
        filtered = [l for l in unresolved if _SEVERITY_ORDER.get(l.severity.value if isinstance(l.severity, LessonSeverity) else l.severity, 1) >= min_level]
        recent = sorted(filtered, key=lambda l: l.occurred_at, reverse=True)[:max_lessons]

        if not recent:
            return ""

        lines = ["[SELF-CORRECTION: Lessons from previous runs]"]
        for l in recent:
            lines.append(f"- [{l.severity.value}] {l.category}: {l.summary}")
            if l.detail:
                lines.append(f"  → {l.detail[:200]}")
        lines.append("[END LESSONS]")
        return "\n".join(lines)

    def resolve(self, lesson_id: str, resolution: str = "") -> bool:
        """Mark a lesson as resolved."""
        for l in self._lessons:
            if l.id == lesson_id:
                l.resolved = True
                l.resolution = resolution or "resolved"
                self._save()
                return True
        return False

    def list_lessons(
        self,
        category: str | None = None,
        unresolved_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List lessons, newest first."""
        items = self._lessons
        if category:
            items = [l for l in items if l.category == category]
        if unresolved_only:
            items = [l for l in items if not l.resolved]
        items.sort(key=lambda l: l.occurred_at, reverse=True)
        return [{"id": l.id, "category": l.category,
                 "severity": l.severity.value if isinstance(l.severity, LessonSeverity) else l.severity,
                 "summary": l.summary, "detail": l.detail[:200],
                 "occurred_at": l.occurred_at, "resolved": l.resolved}
                for l in items[:limit]]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._lessons)
        resolved = sum(1 for l in self._lessons if l.resolved)
        by_category: dict[str, int] = {}
        for l in self._lessons:
            by_category[l.category] = by_category.get(l.category, 0) + 1
        return {"total": total, "resolved": resolved, "unresolved": total - resolved, "by_category": by_category}

    # ── persistence ─────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            self._lessons = []
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._lessons = [Lesson(**item) for item in raw]
            # Ensure severity is an enum, not a string from JSON
            for l in self._lessons:
                if isinstance(l.severity, str):
                    l.severity = LessonSeverity(l.severity)
        except Exception as exc:
            logger.warning("Failed to load lessons: %s", exc)
            self._lessons = []

    def _save(self) -> None:
        raw = [{"id": l.id, "category": l.category, "severity": l.severity.value if isinstance(l.severity, LessonSeverity) else l.severity,
                "summary": l.summary, "detail": l.detail, "context": l.context,
                "occurred_at": l.occurred_at, "resolved": l.resolved, "resolution": l.resolution}
               for l in self._lessons]
        self._path.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# 4. AUTONOMOUS TRADING PIPELINE — data → signal → risk → execute
# ---------------------------------------------------------------------------
# ponytail: wires existing components into one flow.

@dataclass
class PipelineStep:
    name: str
    status: str = "pending"  # pending | running | passed | failed | skipped
    duration_ms: float = 0.0
    result: Any = None
    error: str = ""


@dataclass
class PipelineResult:
    symbol: str
    success: bool
    signal: str = "hold"
    confidence: float = 0.0
    reason: str = ""
    steps: list[PipelineStep] = field(default_factory=list)
    decision: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class AutonomousPipeline:
    """End-to-end autonomous trading pipeline.

    Flow: fetch data → generate signal → check risk → execute decision.
    Each step is a discrete PipelineStep. Failures are recorded as lessons.

    Wires into existing QNAI:
      - Strategy discovery (-> engine/strategy/strategies/)
      - Agentic consensus (-> engine/agentic_trading.py ConsensusEngine)
      - Strategy lifecycle (-> engine/strategy_lifecycle.py StrategyLifecycleManager)
      - LLM routing (-> engine/llm_router.py LLMRouter)
    """

    def __init__(
        self,
        self_correction: SelfCorrection | None = None,
    ):
        self.correction = self_correction or SelfCorrection()
        self._strategies: dict[str, type] = {}
        self._lifecycle: Any = None
        self._llm_router: Any = None
        # ponytail: cache last run result for GET /last-result
        self._last_result: PipelineResult | None = None
        # ponytail: DataProviderManager (lazy-init, used by _fetch_data)
        self._data_manager: Any = None
        # Data freshness monitor — tracks staleness, triggers kill switch if needed
        self._data_monitor: Any = None

        # Lazy-init lifecylce and router
        self._init_services()

    def _ensure_data_manager(self) -> Any:
        """Lazy-init DataProviderManager with all real providers.

        The 15 data providers exist in quant_nanggroe/data/providers/ but were
        previously bypassed by _fetch_data() calling yfinance directly. Routing
        through the manager unlocks failover, caching, health scoring, and
        multi-provider support (Binance, Finnhub, FRED, Alpaca, etc.).
        """
        if self._data_manager is not None:
            return self._data_manager
        try:
            from quant_nanggroe.data.manager import DataProviderManager
            from quant_nanggroe.data.providers.yahoo import YahooFinanceProvider

            dm = DataProviderManager(default_cache_ttl=300.0)
            # Yahoo is the only provider that works with zero config — register it
            # as fallback for all markets. Other providers require API keys.
            dm.register(YahooFinanceProvider(), markets=["stocks", "forex", "crypto"])

            # Try to register additional providers if their API keys are set.
            # Each provider is optional; registration failures are non-fatal.
            import os
            for _module_name, _market in (
                ("binance", "crypto"),
                ("finnhub_provider", "stocks"),
                ("fred", "macro"),
                ("alpaca", "stocks"),
                ("polygon", "stocks"),
                ("alpha_vantage", "stocks"),
                ("twelvedata", "stocks"),
            ):
                try:
                    mod = __import__(
                        f"quant_nanggroe.data.providers.{_module_name}",
                        fromlist=["__all__"],
                    )
                    # Find the provider class (first DataProvider subclass in module)
                    from quant_nanggroe.data.providers.base import DataProvider
                    for _attr in dir(mod):
                        obj = getattr(mod, _attr)
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, DataProvider)
                            and obj is not DataProvider
                            and not _attr.startswith("_")
                        ):
                            try:
                                provider = obj()
                                dm.register(provider, markets=[_market])
                            except Exception:
                                continue  # missing API key or init failure — skip silently
                            break
                except Exception:
                    continue  # provider module not importable — skip
            self._data_manager = dm
            logger.info("DataProviderManager initialized with %d providers", len(dm._providers))
        except Exception as exc:
            logger.warning("DataProviderManager init failed (%s) — falling back to yfinance", exc)
            self._data_manager = None
        return self._data_manager

    def _init_services(self) -> None:
        """Lazy-init lifecycle manager, LLM router, and data freshness monitor."""
        try:
            from quant_nanggroe.engine.strategy_lifecycle import StrategyLifecycleManager
            self._lifecycle = StrategyLifecycleManager()
        except ImportError:
            self._lifecycle = None

        try:
            from quant_nanggroe.engine.llm_router import get_llm_router
            self._llm_router = get_llm_router()
        except ImportError:
            self._llm_router = None

        try:
            from quant_nanggroe.data.monitor import DataFreshnessMonitor
            self._data_monitor = DataFreshnessMonitor()
        except ImportError:
            self._data_monitor = None

        try:
            from quant_nanggroe.engine.execution.builder import build_execution_manager
            self._em = build_execution_manager()
        except ImportError:
            self._em = None

    # ── strategy signal tracking ────────────────────────────────────

    def _record_strategy_signals(self, symbol: str, df: Any, signals: list[tuple[str, float, str, str]]) -> None:
        """Record each strategy's signal for future win/loss evaluation.

        Persists to a JSON file so signal accuracy can be tracked
        across pipeline runs. On next run, previous signals are checked
        against actual price movement.
        """
        import json
        from pathlib import Path

        if df is None or len(df) < 2:
            return
        current_price = float(df['close'].iloc[-1]) if hasattr(df, 'close') else 0.0
        if current_price == 0:
            return

        path = Path(__file__).resolve().parent.parent.parent / "data" / "strategy_signals.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        # Load previous signals
        previous: list[dict] = []
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                previous = []

        # Evaluate previous signals for this symbol against current price
        if previous and self._lifecycle:
            still_pending = []
            for ps in previous:
                if ps.get("symbol") != symbol:
                    still_pending.append(ps)
                    continue
                prev_price = ps.get("price", 0)
                prev_signal = ps.get("signal", "hold")
                strat_name = ps.get("strategy", "unknown")
                if prev_price <= 0 or prev_signal == "hold":
                    still_pending.append(ps)
                    continue
                price_change = (current_price - prev_price) / prev_price
                is_win = (prev_signal == "buy" and price_change > 0.01) or \
                         (prev_signal == "sell" and price_change < -0.01)
                try:
                    self._lifecycle.update_strategy(
                        name=strat_name,
                        pnl=price_change,
                        is_win=is_win,
                    )
                except Exception:
                    pass
            previous = still_pending

        # Record current signals
        timenow = datetime.now(timezone.utc).isoformat()
        for sig, conf, reason, cat in signals:
            if sig != "hold":
                previous.append({
                    "symbol": symbol, "strategy": cat, "signal": sig,
                    "price": current_price, "confidence": conf,
                    "timestamp": timenow,
                })

        # Keep only last 1000 entries
        if len(previous) > 1000:
            previous = previous[-1000:]

        try:
            path.write_text(json.dumps(previous, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    # ── strategy management ─────────────────────────────────────────

    def load_strategies(self, directory: str | None = None, base_class: type | None = None) -> int:
        """Auto-discover and register strategy classes with lifecycle manager."""
        self._strategies = discover_strategies(directory, base_class)
        count = len(self._strategies)
        if self._lifecycle:
            for name in self._strategies:
                self._lifecycle.register_strategy(name)
            logger.info("Registered %d strategies with lifecycle manager", count)
        logger.info("Loaded %d strategies into autonomous pipeline", count)
        return count

    def list_available_strategies(self) -> list[str]:
        return sorted(self._strategies.keys())

    # ── pipeline execution ──────────────────────────────────────────

    async def run(
        self,
        symbol: str,
        strategy_name: str | None = None,
        use_llm: bool = False,
        data: Any = None,
    ) -> PipelineResult:
        """Run one full pipeline cycle for *symbol*.

        Args:
            symbol: Trading symbol (e.g. "BTC-USD").
            strategy_name: Specific strategy to use, or None for first available.
            use_llm: Whether to route decision through LLM.
            data: Optional pre-fetched OHLCV DataFrame.

        Returns:
            PipelineResult with all step details.
        """
        steps: list[PipelineStep] = []
        result = PipelineResult(symbol=symbol, success=False)

        # ── Step 1: Data ────────────────────────────────────────────
        s1 = PipelineStep(name="data_fetch")
        try:
            s1.status = "running"
            t0 = time.perf_counter()
            df = await self._fetch_data(symbol, data)
            s1.duration_ms = (time.perf_counter() - t0) * 1000
            if df is None or (hasattr(df, 'empty') and df.empty):
                raise ValueError("No data returned")
            s1.status = "passed"
            s1.result = f"{len(df)} bars"
            # ponytail: feed latest close to PaperBroker so submit_order()
            # doesn't reject with "No price data available". This was a silent
            # failure — paper trades always rejected before this fix.
            try:
                latest_price = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
                self._feed_price_to_paper(symbol, latest_price)
            except Exception:
                pass  # non-fatal — paper trading is best-effort
        except Exception as exc:
            s1.status = "failed"
            s1.error = str(exc)
            self.correction.record("data_fetch", f"Data fetch failed for {symbol}", str(exc), LessonSeverity.ERROR)

        steps.append(s1)
        if s1.status == "failed":
            result.reason = f"Data fetch failed: {s1.error}"
            result.steps = steps
            return result

        # ── Step 1.5: Regime Detection ──────────────────────────────
        regime = "unknown"
        regime_confidence = 0.0
        try:
            from quant_nanggroe.engine.market_state import MarketRegimeDetector
            from quant_nanggroe.engine.autoswitch import REGIME_STRATEGY_MAP, StrategyType
            closes = df["close"].tolist() if "close" in df.columns else []
            volumes = df["volume"].tolist() if "volume" in df.columns else None
            detector = MarketRegimeDetector()
            regime_result = detector.detect(closes, volumes, symbol)
            regime = regime_result.regime.value if hasattr(regime_result, "regime") else "unknown"
            regime_confidence = regime_result.confidence if hasattr(regime_result, "confidence") else 0.0
            strategy_type = REGIME_STRATEGY_MAP.get(regime_result.regime, StrategyType.PAUSED)
            logger.info("Regime detected: %s (conf=%.2f) → strategy type: %s", regime, regime_confidence, strategy_type.value)
            # Write regime to result for API consumers
            result.decision["regime"] = {
                "regime": regime,
                "confidence": regime_confidence,
                "strategy_type": strategy_type.value,
            }
        except Exception as exc:
            logger.warning("Regime detection failed: %s — falling back to naive strategy selection", exc)

        # ── Step 2: Signal ──────────────────────────────────────────
        s2 = PipelineStep(name="signal_generation")
        try:
            s2.status = "running"
            t0 = time.perf_counter()
            signal_type, confidence, reason = self._generate_signal(symbol, strategy_name, df, regime=regime)
            s2.duration_ms = (time.perf_counter() - t0) * 1000
            s2.status = "passed"
            s2.result = f"{signal_type} @ {confidence:.2f}"
        except Exception as exc:
            s2.status = "failed"
            s2.error = str(exc)
            self.correction.record("signal_gen", f"Signal gen failed for {symbol}", str(exc), LessonSeverity.ERROR)

        steps.append(s2)
        if s2.status == "failed":
            result.reason = f"Signal generation failed: {s2.error}"
            result.steps = steps
            return result

        result.signal = signal_type
        result.confidence = confidence

        # ── Step 2.25: Ensemble Voting (multi-source consensus) ────
        s225 = PipelineStep(name="ensemble_voting")
        try:
            s225.status = "running"
            t0 = time.perf_counter()
            from quant_nanggroe.engine.agentic.ensemble import EnsembleVoter
            voter = EnsembleVoter()
            voted_bias, voted_conf, vote_meta = voter.run(
                symbol, signal_type, confidence, dataframe=df,
            )
            s225.duration_ms = (time.perf_counter() - t0) * 1000
            s225.status = "passed"
            s225.result = f"{voted_bias} @ {voted_conf:.2f} (consensus={vote_meta.get('consensus_strength', 0):.2f})"
            result.decision["ensemble"] = vote_meta
            # Only override if ensemble has stronger consensus
            if voted_bias != "neutral" and vote_meta.get("consensus_strength", 0) > 0.6:
                signal_type = voted_bias
                confidence = voted_conf
                result.signal = signal_type
                result.confidence = confidence
        except Exception as exc:
            s225.status = "skipped"
            s225.error = str(exc)
            logger.debug("Ensemble voting skipped for %s: %s", symbol, exc)

        steps.append(s225)

        # ── Step 2.5: Council debate (low-confidence signals only) ───
        current_price = float(df['close'].iloc[-1]) if hasattr(df, 'iloc') else 0.0
        s25 = PipelineStep(name="council_debate")
        try:
            s25.status = "running"
            t0 = time.perf_counter()
            from quant_nanggroe.engine.agentic.council import convene_council, DEBATE_THRESHOLD
            if confidence < DEBATE_THRESHOLD:
                debate = convene_council(
                    symbol=symbol,
                    proposed_signal=signal_type,
                    proposed_confidence=confidence,
                    price=current_price,
                    regime=regime,
                )
                s25.duration_ms = (time.perf_counter() - t0) * 1000
                if debate.debate_held:
                    signal_type = debate.signal
                    confidence = debate.confidence
                    s25.result = f"Council: {signal_type} @ {confidence:.2f} — {debate.summary}"
                    result.decision["council"] = {
                        "debate_held": True,
                        "votes": debate.votes,
                        "summary": debate.summary,
                        "original_signal": result.signal,
                        "original_confidence": result.confidence,
                    }
                    result.signal = signal_type
                    result.confidence = confidence
                else:
                    s25.result = f"No debate needed ({debate.summary})"
            else:
                s25.duration_ms = (time.perf_counter() - t0) * 1000
                s25.result = f"Skipped (confidence {confidence:.2%} >= {DEBATE_THRESHOLD:.0%})"
            s25.status = "passed"
        except Exception as exc:
            s25.status = "skipped"
            s25.error = str(exc)
            logger.warning("Council debate skipped for %s: %s", symbol, exc)

        steps.append(s25)

        # ── Step 3: Risk check (via real RiskManager + kill switch) ─
        s3 = PipelineStep(name="risk_check")
        try:
            s3.status = "running"
            t0 = time.perf_counter()
            current_price = float(df['close'].iloc[-1]) if hasattr(df, 'iloc') else 0.0
            risk_ok, risk_reason, risk_metrics = self._check_risk(
                symbol, signal_type, confidence, current_price=current_price
            )
            s3.duration_ms = (time.perf_counter() - t0) * 1000
            s3.status = "passed" if risk_ok else "failed"
            s3.result = risk_reason
        except Exception as exc:
            s3.status = "failed"
            s3.error = str(exc)

        steps.append(s3)
        if s3.status == "failed":
            result.reason = f"Risk check blocked: {risk_reason if 'risk_reason' in dir() else s3.error}"
            result.steps = steps
            return result

        # ── Step 4: LLM reasoning (optional) ────────────────────────
        if use_llm and self._llm_router:
            s4 = PipelineStep(name="llm_reasoning")
            try:
                s4.status = "running"
                t0 = time.perf_counter()
                llm_decision = await self._llm_reason(symbol, signal_type, confidence)
                s4.duration_ms = (time.perf_counter() - t0) * 1000
                s4.status = "passed"
                s4.result = llm_decision.get("action", "hold")
                result.decision["llm"] = llm_decision
            except Exception as exc:
                s4.status = "skipped"
                s4.error = str(exc)
                self.correction.record("llm_reasoning", f"LLM reasoning failed for {symbol}", str(exc), LessonSeverity.WARNING)
            steps.append(s4)

        # ── Step 5: Execution decision ──────────────────────────────
        s5 = PipelineStep(name="execution")
        try:
            s5.status = "running"
            t0 = time.perf_counter()
            exec_decision = await self._make_decision(symbol, signal_type, confidence, current_price=current_price, regime=regime)
            s5.duration_ms = (time.perf_counter() - t0) * 1000
            s5.status = "passed"
            s5.result = exec_decision.get("action", "hold")
            result.decision["execution"] = exec_decision
        except Exception as exc:
            s5.status = "failed"
            s5.error = str(exc)

        steps.append(s5)

        result.success = s5.status != "failed"
        result.reason = f"Pipeline complete: {signal_type} @ {confidence:.1%}"
        result.steps = steps
        self._last_result = result  # ponytail: cache for GET /last-result
        return result

    # ── pipeline internals ──────────────────────────────────────────

    async def _fetch_data(self, symbol: str, data: Any = None) -> Any:
        """Fetch OHLCV for *symbol*. Accepts pre-loaded data.

        Routes through DataProviderManager first (failover, caching, health
        scoring, multi-provider) and falls back to direct yfinance if the
        manager is unavailable. Previously bypassed 15 registered providers
        by calling yfinance directly.
        """
        if data is not None:
            return data

        import asyncio
        import pandas as pd

        # ── Primary path: DataProviderManager ────────────────────────
        dm = self._ensure_data_manager()
        if dm is not None:
            try:
                from quant_nanggroe.types.market import TimeFrame
                ohlcv_list = await dm.get_ohlcv(symbol, timeframe=TimeFrame.D1, limit=500)
                if ohlcv_list and len(ohlcv_list) >= 50:
                    rows = [
                        {
                            "open": float(c.open),
                            "high": float(c.high),
                            "low": float(c.low),
                            "close": float(c.close),
                            "volume": float(c.volume),
                        }
                        for c in ohlcv_list
                    ]
                    df = pd.DataFrame(rows, index=pd.DatetimeIndex([c.timestamp for c in ohlcv_list]))
                    logger.debug("DataProviderManager returned %d bars for %s", len(df), symbol)
                    # Record successful fetch for staleness monitoring
                    if self._data_monitor is not None:
                        try:
                            from quant_nanggroe.types.market import TimeFrame as _TF
                            self._data_monitor.record_fetch(symbol, _TF.D1)
                        except Exception:
                            pass
                    df = self._validate_ohlcv(df, symbol)
                    return df
            except Exception as exc:
                logger.warning("DataProviderManager fetch failed for %s (%s) — falling back to yfinance", symbol, exc)

        # ── Fallback path: direct yfinance ───────────────────────────
        import yfinance as yf

        # Symbol map for Yahoo Finance
        sym_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        }
        yf_sym = sym_map.get(symbol, symbol)

        # Retry with delay to handle Yahoo Finance rate limiting
        for attempt in range(3):
            try:
                ticker = yf.Ticker(yf_sym)
                df = ticker.history(period="6mo")
                if len(df) >= 50:
                    break
                if attempt < 2:
                    logger.info("yfinance returned %d bars for %s, retrying in %ds...", len(df), symbol, 5 * (attempt + 1))
                    await asyncio.sleep(5 * (attempt + 1))
            except Exception as exc:
                if attempt < 2:
                    logger.info("yfinance attempt %d failed for %s: %s, retrying...", attempt + 1, symbol, exc)
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    raise

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        if len(df) < 50:
            logger.warning("Insufficient data for %s: %d bars", symbol, len(df))
            return None
        # Record successful fetch for staleness monitoring
        if self._data_monitor is not None:
            try:
                from quant_nanggroe.types.market import TimeFrame as _TF
                self._data_monitor.record_fetch(symbol, _TF.D1)
            except Exception:
                pass
        return self._validate_ohlcv(df, symbol)

    def _feed_price_to_paper(self, symbol: str, price: float) -> None:
        """Feed latest close price to PaperBroker.

        PaperBroker.submit_order() rejects orders if set_price() has never
        been called for the symbol ("No price data available"). Without this,
        paper trading silently never executes. Must be called after every
        data fetch so the broker has a current quote to fill against.
        """
        if price <= 0:
            return
        try:
            # Lazy-import to avoid circular dependency
            from quant_nanggroe.engine.execution.builder import build_execution_manager
            # The singleton execution manager is shared across the pipeline.
            # Look up via the global accessor; if not built yet, skip silently.
            import quant_nanggroe.engine.execution.builder as _builder
            # Most callers attach an ExecutionManager to the pipeline; we
            # opportunistically scan the singleton if present.
            for _attr in ("_execution_manager", "_em", "execution_manager"):
                em = getattr(self, _attr, None)
                if em is None:
                    continue
                for broker in getattr(em, "_brokers", {}).values():
                    set_price = getattr(broker, "set_price", None)
                    if callable(set_price):
                        set_price(symbol, price)
                return
        except Exception as exc:
            logger.debug("Paper price feed skipped for %s: %s", symbol, exc)

    def _validate_ohlcv(self, df: Any, symbol: str) -> Any:
        """Validate and clean OHLCV data before strategy consumption.

        Checks for:
          1. Gaps in datetime index (> 2× expected interval)
          2. NaN / inf values in the close column
          3. Non-positive close prices
          4. Impossible bars (high < low or open < 0)

        Returns the cleaned DataFrame, or None if fewer than 50 bars survive.
        """
        import numpy as np
        import pandas as pd

        if df is None or df.empty:
            logger.warning("[%s] OHLCV validation: empty DataFrame", symbol)
            return None

        initial_len = len(df)
        issues: list[str] = []

        # ── 1. Gap detection ────────────────────────────────────────
        if len(df) >= 2:
            idx = df.index
            diffs = pd.Series(idx[1:]) - pd.Series(idx[:-1])
            median_interval = diffs.median()
            if pd.notna(median_interval) and median_interval.total_seconds() > 0:
                gap_threshold = median_interval * 2
                gaps = diffs[diffs > gap_threshold]
                if len(gaps) > 0:
                    issues.append(
                        f"{len(gaps)} index gap(s) > 2× expected interval "
                        f"(max gap={gaps.max()}, median interval={median_interval})"
                    )

        # ── 2. NaN / inf in close ───────────────────────────────────
        if "close" in df.columns:
            bad_close = df["close"].isna() | ~np.isfinite(df["close"])
            nan_count = int(bad_close.sum())
            if nan_count > 0:
                issues.append(f"{nan_count} row(s) with NaN/inf close")
                df = df[~bad_close]

        # ── 3. Non-positive close ───────────────────────────────────
        if "close" in df.columns:
            non_pos = df["close"] <= 0
            non_pos_count = int(non_pos.sum())
            if non_pos_count > 0:
                issues.append(f"{non_pos_count} row(s) with close <= 0")
                df = df[~non_pos]

        # ── 4. Impossible bars ──────────────────────────────────────
        mask = pd.Series(True, index=df.index)
        if "high" in df.columns and "low" in df.columns:
            inv = df["high"] < df["low"]
            inv_count = int(inv.sum())
            if inv_count > 0:
                issues.append(f"{inv_count} row(s) with high < low")
                mask = mask & ~inv
        if "open" in df.columns:
            neg_open = df["open"] < 0
            neg_count = int(neg_open.sum())
            if neg_count > 0:
                issues.append(f"{neg_count} row(s) with open < 0")
                mask = mask & ~neg_open
        df = df[mask]

        # ── Log and decide ──────────────────────────────────────────
        removed = initial_len - len(df)
        if issues:
            logger.warning(
                "[%s] OHLCV validation: %d/%d rows removed — %s",
                symbol, removed, initial_len, "; ".join(issues),
            )
        else:
            logger.debug("[%s] OHLCV validation passed (%d bars)", symbol, len(df))

        if len(df) < 50:
            logger.warning("[%s] OHLCV validation: only %d bars remain (< 50 threshold) — returning None", symbol, len(df))
            return None

        return df

    def _generate_signal(self, symbol: str, strategy_name: str | None, df: Any, regime: str = "unknown") -> tuple[str, float, str]:
        """Generate a trading signal via ensemble aggregation.

        Runs multiple strategies, collects signals, and produces a
        regime-weighted aggregate signal. Falls back to single-strategy
        when a specific strategy_name is provided.

        Returns:
            (signal_type, confidence, reason)
        """
        import pandas as pd

        # If a specific strategy is named, use it directly
        if strategy_name:
            try:
                from quant_nanggroe.engine.strategy.strategies import create_strategy
                strategy = create_strategy(strategy_name)
            except (ImportError, ValueError) as exc:
                logger.warning("Strategy %s not found: %s", strategy_name, exc)
                return "hold", 0.0, f"Strategy not found: {exc}"
            result = strategy.generate_signal(df) if hasattr(strategy, 'generate_signal') else None
            return self._extract_signal(result, strategy_name)

        # Ensemble: run top strategies and aggregate
        return self._ensemble_signal(symbol, df, regime)

    def _ensemble_signal(self, symbol: str, df: Any, regime: str) -> tuple[str, float, str]:
        """Run top strategies and aggregate via regime-weighted voting.

        Strategy categories and their regime weights:
          - momentum/trend: high weight in trending regimes
          - mean_reversion: high weight in ranging regimes
          - volatility: high weight in volatile regimes
          - pattern: low weight everywhere (statistically weak)
        """
        import pandas as pd

        # Regime → strategy category weights
        regime_weights = {
            "trending_up":   {"momentum": 1.5, "trend": 1.5, "mean_reversion": 0.5, "volatility": 0.8, "pattern": 0.3},
            "trending_down": {"momentum": 1.5, "trend": 1.5, "mean_reversion": 0.5, "volatility": 0.8, "pattern": 0.3},
            "ranging":       {"momentum": 0.5, "trend": 0.5, "mean_reversion": 1.5, "volatility": 1.0, "pattern": 0.5},
            "volatile":      {"momentum": 0.8, "trend": 0.7, "mean_reversion": 1.0, "volatility": 1.5, "pattern": 0.3},
            "crisis":        {"momentum": 0.3, "trend": 0.5, "mean_reversion": 1.5, "volatility": 1.2, "pattern": 0.2},
            "recovery":      {"momentum": 1.2, "trend": 1.0, "mean_reversion": 0.8, "volatility": 0.7, "pattern": 0.3},
            "unknown":       {"momentum": 1.0, "trend": 1.0, "mean_reversion": 1.0, "volatility": 1.0, "pattern": 0.5},
        }
        weights = regime_weights.get(regime, regime_weights["unknown"])

        # Classify strategy by name keywords
        def _classify(name: str) -> str:
            n = name.lower()
            if any(k in n for k in ["momentum", "trend", "aroon", "parabolic", "hull", "dual_ma"]):
                return "momentum"
            if any(k in n for k in ["mean_reversion", "bollinger", "fibonacci", "rsi_", "stochastic", "pairs"]):
                return "mean_reversion"
            if any(k in n for k in ["vol", "entropy", "kalman", "garch"]):
                return "volatility"
            if any(k in n for k in ["engulfing", "doji", "hammer", "pattern", "candle"]):
                return "pattern"
            return "momentum"  # default

        # Run top 15 strategies (regime-specific first, then fill)
        regime_priority = {
            "trending_up": ["momentum", "trend_following_cta", "parabolic_sar", "aroon_strategy", "hull_ma", "dual_ma_crossover"],
            "trending_down": ["momentum", "trend_following_cta", "hull_ma", "parabolic_sar"],
            "ranging": ["mean_reversion", "bollinger_squeeze", "rsi_momentum", "fibonacci_arc", "pairs_trading"],
            "volatile": ["bollinger_squeeze", "entropy_strategy", "kalman_filter", "garch_vol"],
            "crisis": ["mean_reversion", "momentum_crash_filter"],
            "recovery": ["momentum", "aroon_strategy"],
            "unknown": ["momentum", "mean_reversion", "bollinger_squeeze", "kalman_filter", "rsi_momentum"],
        }
        priority = regime_priority.get(regime, regime_priority["unknown"])

        try:
            from quant_nanggroe.engine.strategy.strategies import list_strategies, create_strategy
            all_names = list_strategies()
            # Filter through lifecycle manager — exclude killed/hibernating
            if self._lifecycle:
                active = set(self._lifecycle.get_active_strategies())
                if active:
                    all_names = [n for n in all_names if n in active]
                    logger.debug("Lifecycle gate: %d/%d strategies active", len(all_names), len(list_strategies()))
        except (ImportError, ValueError):
            return "hold", 0.0, "Cannot load strategy registry"

        # Build candidate list: priority first, then fill to 15
        candidates = []
        for name in priority:
            if name in all_names and name not in candidates:
                candidates.append(name)
        for name in all_names:
            if name not in candidates and len(candidates) < 15:
                candidates.append(name)

        # Run all candidates
        signals: list[tuple[str, float, str, str]] = []  # (signal, confidence, reason, category)
        for name in candidates:
            try:
                strat = create_strategy(name)
                result = strat.generate_signal(df)
                sig, conf, reason = self._extract_signal(result, name)
                if sig != "hold" and conf > 0.0:
                    cat = _classify(name)
                    signals.append((sig, conf, reason, cat))
            except Exception:
                continue

        # Record signals for win/loss tracking
        self._record_strategy_signals(symbol, df, signals)

        if not signals:
            return "hold", 0.0, "No strategy produced a signal"

        # Aggregate: weighted vote
        buy_weight = 0.0
        sell_weight = 0.0
        total_weight = 0.0
        reasons = []

        for sig, conf, reason, cat in signals:
            w = conf * weights.get(cat, 1.0)
            if sig == "buy":
                buy_weight += w
            elif sig == "sell":
                sell_weight += w
            total_weight += w
            if reason:
                reasons.append(f"{cat}({sig}:{conf:.0%})")

        if total_weight == 0:
            return "hold", 0.0, "All signals zero weight"

        # Normalize and decide
        buy_pct = buy_weight / total_weight
        sell_pct = sell_weight / total_weight

        if buy_pct > sell_pct and buy_pct > 0.3:
            confidence = min(buy_pct, 1.0)
            return "buy", confidence, f"Ensemble: {', '.join(reasons[:5])}"
        elif sell_pct > buy_pct and sell_pct > 0.3:
            confidence = min(sell_pct, 1.0)
            return "sell", confidence, f"Ensemble: {', '.join(reasons[:5])}"
        else:
            return "hold", 0.0, f"No consensus: buy={buy_pct:.0%} sell={sell_pct:.0%}"

    def _extract_signal(self, result: Any, strategy_name: str) -> tuple[str, float, str]:
        """Extract (signal, confidence, reason) from a strategy result."""
        import pandas as pd
        if result is None:
            return "hold", 0.0, "No signal"
        if hasattr(result, 'signal_type'):
            sig = result.signal_type.value
            conf = getattr(result, 'confidence', 0.5)
            reason = getattr(result, 'reasoning', '') or f"{strategy_name} -> {sig}"
            return sig, min(float(conf), 1.0), reason
        if isinstance(result, pd.Series) and len(result) > 0:
            last = result.iloc[-1]
            sig = "buy" if last > 0 else "sell" if last < 0 else "hold"
            conf = abs(float(last))
            return sig, min(conf, 1.0), f"{strategy_name}: {last:.4f}"
        return "hold", 0.0, f"Unknown result: {type(result).__name__}"

    def _check_risk(
        self, symbol: str, signal: str, confidence: float,
        current_price: float = 0.0,
    ) -> tuple[bool, str, dict]:
        """Check risk constraints via real RiskManager + kill switch.

        Uses the shared ExecutionManager's RiskManager for constitutional limit
        enforcement (VaR, Kelly, drawdown, 9-gate). Falls back to confidence floor
        when RiskManager is unavailable.

        Args:
            symbol: Trading symbol.
            signal: buy/sell/hold.
            confidence: Signal confidence 0-1.
            current_price: Current market price from OHLCV data.

        Returns:
            (ok: bool, reason: str, metrics: dict)
        """
        metrics = {"max_drawdown": 0.0, "daily_pnl": 0.0, "price": current_price}

        try:
            em = self._em

            # Check kill switch first — hard block if active
            if em._kill_switch:
                ks_status = em._kill_switch.status()
                if ks_status.get("is_active") or ks_status.get("active"):
                    level = ks_status.get("level", "?")
                    return False, f"Kill switch active (level={level})", metrics

            # Full RiskManager 9-checkpoint gate with real values
            if em._risk_manager:
                from quant_nanggroe.engine.risk.constants import MAX_RISK_PER_TRADE
                balance = em._risk_manager.state.current_equity
                stop_loss = current_price * 0.95 if signal == "buy" else (
                    current_price * 1.05 if signal == "sell" else current_price
                )
                lot_size = max(
                    0.01,
                    round(balance * MAX_RISK_PER_TRADE / current_price, 4)
                ) if current_price > 0 else 0.01

                verdict = em._risk_manager.check_trade(
                    symbol=symbol,
                    direction=signal.upper() if signal != "hold" else "HOLD",
                    lot_size=lot_size,
                    entry=current_price,
                    stop_loss=stop_loss,
                    account_balance=balance,
                )
                if verdict.get("verdict") == "VETOED":
                    return False, f"RiskManager vetoed: {verdict.get('reason','?')}", {
                        **metrics, "risk_verdict": "VETOED", "checkpoints": verdict.get("checkpoints", {})
                    }
                metrics.update({
                    "risk_verdict": "APPROVED",
                    "lot_size": lot_size,
                    "stop_loss": stop_loss,
                    "balance": balance,
                })
        except Exception as exc:
            logger.warning("RiskManager check failed (non-fatal, using confidence gate): %s", exc)

        # Fallback confidence gate when RiskManager unavailable
        if confidence < 0.15:
            return False, f"Confidence {confidence:.2f} below 0.15 floor", metrics
        if signal == "hold":
            return False, "Signal is HOLD — no trade", metrics

        return True, f"Risk passed: {signal} @ {confidence:.1%}", metrics

    async def _llm_reason(self, symbol: str, signal: str, confidence: float) -> dict[str, Any]:
        """Route decision through LLM for reasoning."""
        prompt = (
            f"Symbol: {symbol}\n"
            f"Technical Signal: {signal}\n"
            f"Confidence: {confidence:.1%}\n\n"
            "Evaluate this trade. Consider market conditions and risk. "
            "Respond with a single JSON: {\"action\": \"buy|sell|hold\", \"reason\": \"...\", \"confidence\": 0.0-1.0}"
        )
        try:
            response = await self._llm_router.chat(prompt, tier=None, temperature=0.3)
            content = response.content.strip()
            # Try to extract JSON from the response
            if "{" in content:
                json_str = content[content.index("{"):content.rindex("}") + 1]
                import json as _json
                return _json.loads(json_str)
            return {"action": signal, "reason": content[:200], "confidence": confidence}
        except Exception as exc:
            logger.warning("LLM reasoning failed: %s", exc)
            return {"action": signal, "reason": f"LLM unavailable: {exc}", "confidence": confidence}

    async def _make_decision(self, symbol: str, signal: str, confidence: float, current_price: float = 0.0, regime: str = "unknown") -> dict[str, Any]:
        """Execute signal via ExecutionManager → live or paper broker.
        Paper default, MT5 when QNA_LIVE_TRADING=1."""
        try:
            from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType, OrderStatus
            import uuid
            em = self._em
            side = OrderSide.BUY if signal == "buy" else (OrderSide.SELL if signal == "sell" else None)
            if side is None:
                return {"symbol": symbol, "action": signal, "confidence": round(confidence, 4),
                        "position_size_pct": 0, "execution": "hold", "note": "signal=hold, no order"}
            qty = max(0.01, round(confidence * 0.1, 4))

            # Feed current market price to paper broker so it can execute
            if current_price > 0:
                for broker in em._brokers.values():
                    if hasattr(broker, 'set_price'):
                        broker.set_price(symbol, current_price)
                        logger.info("Fed price %.2f to broker %s for %s", current_price, getattr(broker, 'name', '?'), symbol)
            order = Order(id=str(uuid.uuid4()), symbol=symbol, side=side,
                          order_type=OrderType.MARKET, quantity=qty,
                          status=OrderStatus.PENDING, metadata={"confidence": confidence})
            fill = await em.execute_order(order)
            reason = "filled"
            executed = False
            if fill is None:
                log = em.get_audit_log()
                if log:
                    last = log[-1]
                    reason = last.get("action", "rejected") + ": " + last.get("reason", last.get("guard", "unknown"))
                else:
                    reason = "rejected: no broker connected or guard blocked"
            else:
                executed = True

            # Write state snapshot to paper_state/ for dashboard
            try:
                from quant_nanggroe.engine.state_writer import write_engine_snapshot as _write_snap
                if executed and fill:
                    _write_snap(
                        engine_state={"total_value": fill.price * qty if fill.price else 0,
                                      "cash_balance": 0, "positions_count": 1,
                                      "daily_pnl": 0, "weekly_pnl": 0, "drawdown": 0, "regime": "unknown"},
                        risk_state={"kill_switch_active": False},
                        positions=[{"symbol": symbol, "side": signal, "qty": qty,
                                    "entry_price": fill.price if fill.price else 0,
                                    "timestamp": datetime.now(timezone.utc).isoformat()}],
                    )
            except Exception as _wexc:
                logger.debug("State write skipped: %s", _wexc)

            return {
                "symbol": symbol, "action": signal, "confidence": round(confidence, 4),
                "position_size_pct": round(confidence * 0.05, 4),
                "execution": "filled" if executed else "rejected",
                "reason": reason,
                "order_id": fill.order_id if fill else None,
                "fill_price": fill.price if fill else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            self.correction.record("execution", f"Order failed {symbol}", str(exc), LessonSeverity.ERROR)
            return {"symbol": symbol, "action": signal, "confidence": round(confidence, 4),
                    "position_size_pct": 0, "error": str(exc)}

    # ── batch pipeline ──────────────────────────────────────────────

    async def run_batch(
        self,
        symbols: list[str] | None = None,
        strategy_name: str | None = None,
        use_llm: bool = False,
    ) -> list[PipelineResult]:
        """Run pipeline across multiple symbols."""
        if symbols is None:
            symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "EURUSD", "USDJPY"]

        results = []
        for sym in symbols:
            try:
                res = await self.run(sym, strategy_name, use_llm)
                results.append(res)
                logger.info("Pipeline %s: %s @ %.1f%%", sym, res.signal, res.confidence * 100)
            except Exception as exc:
                results.append(PipelineResult(symbol=sym, success=False, reason=str(exc)))
                self.correction.record("pipeline_batch", f"Pipeline failed for {sym}", str(exc), LessonSeverity.ERROR)
        return results


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_pipeline: AutonomousPipeline | None = None


def get_autonomous_pipeline() -> AutonomousPipeline:
    """Get or create the default AutonomousPipeline."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = AutonomousPipeline()
    return _default_pipeline


__all__ = [
    "FREE_PROVIDERS", "register_free_providers",
    "discover_strategies",
    "Lesson", "LessonSeverity", "SelfCorrection",
    "PipelineStep", "PipelineResult", "AutonomousPipeline", "get_autonomous_pipeline",
]
