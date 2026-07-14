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

        # Lazy-init lifecylce and router
        self._init_services()

    def _init_services(self) -> None:
        """Lazy-init lifecycle manager and LLM router."""
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

    # ── strategy management ─────────────────────────────────────────

    def load_strategies(self, directory: str | None = None, base_class: type | None = None) -> int:
        """Auto-discover and register strategy classes."""
        self._strategies = discover_strategies(directory, base_class)
        count = len(self._strategies)
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
        except Exception as exc:
            s1.status = "failed"
            s1.error = str(exc)
            self.correction.record("data_fetch", f"Data fetch failed for {symbol}", str(exc), LessonSeverity.ERROR)

        steps.append(s1)
        if s1.status == "failed":
            result.reason = f"Data fetch failed: {s1.error}"
            result.steps = steps
            return result

        # ── Step 2: Signal ──────────────────────────────────────────
        s2 = PipelineStep(name="signal_generation")
        try:
            s2.status = "running"
            t0 = time.perf_counter()
            signal_type, confidence, reason = self._generate_signal(symbol, strategy_name, df)
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

        # ── Step 3: Risk check ──────────────────────────────────────
        s3 = PipelineStep(name="risk_check")
        try:
            s3.status = "running"
            t0 = time.perf_counter()
            risk_ok, risk_reason, risk_metrics = self._check_risk(symbol, signal_type, confidence)
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
            exec_decision = self._make_decision(symbol, signal_type, confidence)
            s5.duration_ms = (time.perf_counter() - t0) * 1000
            s5.status = "passed"
            s5.result = exec_decision.get("action", "hold")
            result.decision["execution"] = exec_decision
        except Exception as exc:
            s5.status = "failed"
            s5.error = str(exc)

        steps.append(s5)

        result.success = True
        result.reason = f"Pipeline complete: {signal_type} @ {confidence:.1%}"
        result.steps = steps
        return result

    # ── pipeline internals ──────────────────────────────────────────

    async def _fetch_data(self, symbol: str, data: Any = None) -> Any:
        """Fetch OHLCV for *symbol*. Accepts pre-loaded data."""
        if data is not None:
            return data

        import pandas as pd
        import yfinance as yf

        # Symbol map for Yahoo Finance
        sym_map = {
            "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        }
        yf_sym = sym_map.get(symbol, symbol)
        ticker = yf.Ticker(yf_sym)
        df = ticker.history(period="6mo")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        if len(df) < 50:
            logger.warning("Insufficient data for %s: %d bars", symbol, len(df))
            return None
        return df

    def _generate_signal(self, symbol: str, strategy_name: str | None, df: Any) -> tuple[str, float, str]:
        """Generate a trading signal from a strategy.

        Returns:
            (signal_type, confidence, reason)
        """
        import pandas as pd

        # If no strategies loaded, try the existing create_strategy
        if strategy_name:
            try:
                from quant_nanggroe.engine.strategy.strategies import create_strategy
                strategy = create_strategy(strategy_name)
            except (ImportError, ValueError) as exc:
                logger.warning("Strategy %s not found: %s", strategy_name, exc)
                return "hold", 0.0, f"Strategy not found: {exc}"
        elif self._strategies:
            # Use first auto-discovered strategy
            name = next(iter(self._strategies))
            cls = self._strategies[name]
            strategy = cls()
            strategy_name = name
        else:
            # Fallback to existing registry
            try:
                from quant_nanggroe.engine.strategy.strategies import list_strategies, create_strategy
                names = list_strategies()
                if not names:
                    return "hold", 0.0, "No strategies available"
                strategy = create_strategy(names[0])
                strategy_name = names[0]
            except (ImportError, ValueError) as exc:
                return "hold", 0.0, f"Cannot load strategy: {exc}"

        # Generate signal
        result = strategy.generate_signal(df) if hasattr(strategy, 'generate_signal') else None

        if result is None:
            return "hold", 0.0, "No signal generated"

        # Handle different return types
        if hasattr(result, 'signal_type'):
            sig = result.signal_type.value
            conf = getattr(result, 'confidence', 0.5)
            reason = getattr(result, 'reasoning', '')
        elif isinstance(result, pd.Series) and len(result) > 0:
            last = result.iloc[-1]
            sig = "buy" if last > 0 else "sell" if last < 0 else "hold"
            conf = abs(float(last))
            reason = f"Signal value: {last:.4f}"
        else:
            sig = "hold"
            conf = 0.0
            reason = f"Unknown result type: {type(result).__name__}"

        return sig, min(float(conf), 1.0), reason or f"{strategy_name} -> {sig}"

    def _check_risk(self, symbol: str, signal: str, confidence: float) -> tuple[bool, str, dict]:
        """Check risk constraints. Returns (ok: bool, reason: str, metrics: dict).

        Integrates with lifecycle manager if available.
        """
        metrics = {"max_drawdown": 0.0, "daily_pnl": 0.0}
        if self._lifecycle:
            report = self._lifecycle.get_strategy_report()
            metrics["active_strategies"] = report.get("active", 0)
            metrics["killed_strategies"] = report.get("killed", 0)

        # ponytail: basic risk gates — confidence floor, no-trade avoidance
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

    def _make_decision(self, symbol: str, signal: str, confidence: float) -> dict[str, Any]:
        """Final decision synthesis."""
        return {
            "symbol": symbol,
            "action": signal,
            "confidence": round(confidence, 4),
            "position_size_pct": round(confidence * 0.05, 4),  # 5% max scaled by confidence
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

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
