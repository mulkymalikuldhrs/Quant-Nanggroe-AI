"""Autonomous Agent System — LLM-routed, self-correcting, auto-discovering.

Integrates with the existing QNAI infrastructure:
  - LLMRouter (engine/llm_router.py) — extended with free providers
  - Strategy registry (engine/strategy/strategies/) — auto-discovered
  - Agentic trading (engine/agentic_trading.py) — consensus engine
  - Strategy lifecycle (engine/strategy_lifecycle.py) — darwinian management
  - TradeLifecycleManager (engine/agentic/trade_lifecycle.py) — closed trade → eval → evolve
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
from typing import Any

from quant_nanggroe.engine.self_aware import Reflection, SelfAware, SelfState

# Module-level import degradation tracker
import_warnings: list[str] = []

try:
    from quant_nanggroe.engine.registry import AutoRegistry
    _HAS_AUTO_REGISTRY = True
except ImportError:
    AutoRegistry = None
    _HAS_AUTO_REGISTRY = False
    import_warnings.append("AutoRegistry unavailable — auto-discovery disabled")

import asyncio

import numpy as np

logger = logging.getLogger(__name__)

try:
    from quant_nanggroe.engine.strategies.self_finetune import SelfFineTuner
    from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
    _HAS_STRATEGY_EVOLVER = True
except Exception as _evolve_err:
    StrategyEvolver = None
    SelfFineTuner = None
    _HAS_STRATEGY_EVOLVER = False
    logger.debug("StrategyEvolver import failed: %s", _evolve_err)
    import_warnings.append("StrategyEvolver/SelfFineTuner unavailable — strategy evolution disabled")


# ---------------------------------------------------------------------------
# Module-level try/except for optional QNA Core Components
# ---------------------------------------------------------------------------
# These flags + local imports prevent ImportError when components are missing.

try:
    from quant_nanggroe.engine.agentic.final_decider import FinalDecider
    _HAS_FINAL_DECIDER = True
except ImportError:
    FinalDecider = None
    _HAS_FINAL_DECIDER = False
    import_warnings.append("FinalDecider unavailable — final decision layer disabled")

try:
    from quant_nanggroe.engine.analytics.strategy_logger import StrategyLogger
    _HAS_STRATEGY_LOGGER = True
except ImportError:
    StrategyLogger = None
    _HAS_STRATEGY_LOGGER = False
    import_warnings.append("StrategyLogger unavailable — strategy logging disabled")

try:
    from quant_nanggroe.engine.analytics.pnl_evaluator import PnLEvaluator
    _HAS_PNL_EVALUATOR = True
except ImportError:
    PnLEvaluator = None
    _HAS_PNL_EVALUATOR = False
    import_warnings.append("PnLEvaluator unavailable — PnL evaluation disabled")

try:
    from quant_nanggroe.engine.regime.strategy_filter import RegimeStrategyFilter
    _HAS_REGIME_FILTER = True
except ImportError:
    RegimeStrategyFilter = None
    _HAS_REGIME_FILTER = False
    import_warnings.append("RegimeStrategyFilter unavailable — regime filtering disabled")

try:
    from quant_nanggroe.engine.strategies.gene_loader import GeneLoader
    _HAS_GENE_LOADER = True
except ImportError:
    GeneLoader = None
    _HAS_GENE_LOADER = False
    import_warnings.append("GeneLoader unavailable — MUE-X gene loading disabled")

# ── ClosedTrade for PnLEvaluator ──
ClosedTrade = None
try:
    from quant_nanggroe.engine.analytics.pnl_evaluator import ClosedTrade as _CT
    ClosedTrade = _CT
except ImportError:
    import_warnings.append("ClosedTrade unavailable — trade lifecycle PnL tracking disabled")

# ── TradeLifecycleManager ──
_TradeLifecycleManager = None
try:
    from quant_nanggroe.engine.agentic.trade_lifecycle import TradeLifecycleManager as _TLM
    _TradeLifecycleManager = _TLM
except ImportError:
    import_warnings.append("TradeLifecycleManager unavailable — closed trade evaluation loop disabled")

# ── AIHF Override Threshold ──
AIHF_OVERRIDE_THRESHOLD = 0.6

try:
    from quant_nanggroe.agents.aihf_bridge import AIHFBridge, AIHFSignal
    _HAS_AIHF_BRIDGE = True
except ImportError:
    AIHFBridge = None
    AIHFSignal = None
    _HAS_AIHF_BRIDGE = False
    import_warnings.append("AIHFBridge unavailable — AI hedge fund signals disabled")

try:
    from quant_nanggroe.agents.hedge_fund_bridge import HedgeFundBridge, get_hf_signal
    _HAS_HF_BRIDGE = True
except ImportError:
    HedgeFundBridge = None
    get_hf_signal = None
    _HAS_HF_BRIDGE = False
    import_warnings.append("HedgeFundBridge unavailable — hedge fund vote signals disabled")

# Log all import degradations collected at module load time
for _warn in import_warnings:
    logger.warning("Import degradation: %s", _warn)


def verify_critical_imports() -> list[str]:
    """Verify critical QNA modules are importable. Logs ERROR for failures."""
    _CRITICAL_MODULES: list[tuple[str, str]] = [
        ("quant_nanggroe.engine.strategy_lifecycle", "StrategyLifecycleManager"),
        ("quant_nanggroe.engine.llm_router", "get_llm_router"),
        ("quant_nanggroe.engine.execution.builder", "build_execution_manager"),
    ]
    _SEMI_CRITICAL_MODULES: list[tuple[str, str, str]] = [
        ("quant_nanggroe.engine.agentic.final_decider", "FinalDecider", "FinalDecider"),
        ("quant_nanggroe.engine.analytics.pnl_evaluator", "PnLEvaluator", "PnLEvaluator"),
        ("quant_nanggroe.engine.agentic.trade_lifecycle", "TradeLifecycleManager", "TradeLifecycleManager"),
    ]
    failures: list[str] = []
    for mod_path, attrs in _CRITICAL_MODULES:
        try:
            importlib.import_module(mod_path)
        except ImportError as exc:
            logger.error("CRITICAL import failed: %s.%s — %s", mod_path, attrs, exc)
            failures.append(f"{mod_path}.{attrs}")
    for mod_path, class_name, label in _SEMI_CRITICAL_MODULES:
        try:
            importlib.import_module(mod_path)
        except ImportError as exc:
            logger.warning("Semi-critical import failed: %s.%s — %s", mod_path, class_name, exc)
            failures.append(f"{mod_path}.{class_name}")
    if failures:
        logger.warning("verify_critical_imports: %d module(s) unavailable — pipeline will run with degraded functionality", len(failures))
    else:
        logger.info("verify_critical_imports: all critical modules OK")
    return failures


# Run immediately at module load time
verify_critical_imports()

# ---------------------------------------------------------------------------
# 1. FREE LLM PROVIDER CONFIGS
# ---------------------------------------------------------------------------

FREE_PROVIDERS: dict[str, dict[str, Any]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": {"deep_thinking": "llama-3.3-70b-versatile", "standard": "llama3-70b-8192", "quick": "llama3-8b-8192"},
        "api_key_env": "GROQ_API_KEY",
        "priority": 10,
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
    "9router": {
        "base_url": "http://localhost:20128/v1",
        "models": {"deep_thinking": "combo", "standard": "combo", "quick": "combo"},
        "api_key_env": "N9ROUTER_API_KEY",  # Optional — localhost endpoint can use empty key
        "priority": 1,
    },
}


def register_free_providers(router) -> None:
    """Register free LLM providers into an existing LLMRouter instance.
    Localhost endpoints (9router) are registered even without an API key.
    """
    from quant_nanggroe.engine.llm_router import LLMProvider, ModelTier, ProviderConfig
    for name, cfg in FREE_PROVIDERS.items():
        api_key = os.environ.get(cfg["api_key_env"], "")
        is_localhost = "localhost" in cfg["base_url"] or "127.0.0.1" in cfg["base_url"]
        if not api_key and not is_localhost:
            logger.info("Skipping free provider %s: no %s env var", name, cfg["api_key_env"])
            continue
        try:
            provider_enum = LLMProvider(name.upper())
        except ValueError:
            provider_enum = None
        models_map = {}
        for tier_str, model_name in cfg["models"].items():
            tier = ModelTier(tier_str)
            models_map[tier] = model_name
        config_kwargs = {
            "provider": provider_enum or name,
            "base_url": cfg["base_url"],
            "models": models_map,
            "priority": cfg["priority"],
            "enabled": True,
        }
        if api_key:
            config_kwargs["api_key"] = api_key
        config = ProviderConfig(**config_kwargs)
        router.add_provider(config)
        logger.info("Registered free provider: %s (key ends with ...%s)", name, api_key[-4:])


# ---------------------------------------------------------------------------
# 2. STRATEGY AUTO-DISCOVERY
# ---------------------------------------------------------------------------

def discover_strategies(
    directory: str | None = None,
    base_class: type | None = None,
) -> dict[str, type]:
    """Auto-discover strategy classes from a directory."""
    if directory is None:
        dir_path = Path(__file__).resolve().parent.parent / "strategies"
    else:
        dir_path = Path(directory)
    if not dir_path.is_dir():
        logger.warning("Strategy directory not found: %s — trying legacy path", dir_path)
        legacy_path = Path(__file__).resolve().parent.parent / "strategy" / "strategies"
        if legacy_path.is_dir():
            dir_path = legacy_path
            logger.info("Falling back to canonical strategy dir: %s", legacy_path)
        else:
            logger.warning("No strategy directory found at either location")
            return {}
    discovered: dict[str, type] = {}
    for fpath in sorted(dir_path.iterdir()):
        if fpath.suffix != ".py" or fpath.name == "__init__.py":
            continue
        mod_name = fpath.stem
        try:
            mod = importlib.import_module(f"quant_nanggroe.engine.strategies.{mod_name}")
        except Exception as exc:
            logger.debug("Skipping %s: %s", mod_name, exc)
            continue
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ != mod.__name__:
                continue
            if base_class is not None and not issubclass(obj, base_class):
                continue
            if base_class is None and not name.endswith("Strategy"):
                continue
            snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")
            discovered[snake] = obj
    logger.info("Auto-discovered %d strategies from %s", len(discovered), dir_path)
    return discovered


# ---------------------------------------------------------------------------
# 3. SELF-CORRECTION
# ---------------------------------------------------------------------------

class LessonSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Lesson:
    id: str = ""
    category: str = ""
    severity: LessonSeverity = LessonSeverity.INFO
    summary: str = ""
    detail: str = ""
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
    """Record, retrieve, and learn from lessons."""

    def __init__(self, lesson_path: str | None = None):
        if lesson_path is None:
            base = Path(__file__).resolve().parent.parent.parent
            self._path = base / "data" / "lessons.json"
        else:
            self._path = Path(lesson_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lessons: list[Lesson] = []
        self._load()

    def record(self, category: str, summary: str, detail: str = "", severity: LessonSeverity = LessonSeverity.INFO, context: dict[str, Any] | None = None) -> Lesson:
        lesson = Lesson(category=category, severity=severity, summary=summary, detail=detail, context=context or {})
        self._lessons.append(lesson)
        self._save()
        return lesson

    def get_prompt(self, max_lessons: int = 5, severity_min: LessonSeverity = LessonSeverity.WARNING) -> str:
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
        for l in self._lessons:
            if l.id == lesson_id:
                l.resolved = True
                l.resolution = resolution or "resolved"
                self._save()
                return True
        return False

    def list_lessons(self, category: str | None = None, unresolved_only: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        items = self._lessons
        if category:
            items = [l for l in items if l.category == category]
        if unresolved_only:
            items = [l for l in items if not l.resolved]
        items.sort(key=lambda l: l.occurred_at, reverse=True)
        return [{"id": l.id, "category": l.category, "severity": l.severity.value if isinstance(l.severity, LessonSeverity) else l.severity,
                 "summary": l.summary, "detail": l.detail[:200], "occurred_at": l.occurred_at, "resolved": l.resolved}
                for l in items[:limit]]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._lessons)
        resolved = sum(1 for l in self._lessons if l.resolved)
        by_category: dict[str, int] = {}
        for l in self._lessons:
            by_category[l.category] = by_category.get(l.category, 0) + 1
        # SLA metrics
        now = datetime.now(timezone.utc)
        sla_breached = 0
        total_cycle_time = 0.0
        cycle_count = 0
        oldest_age_hours = 0.0
        for l in self._lessons:
            if not l.occurred_at:
                continue
            try:
                occurred = datetime.fromisoformat(l.occurred_at)
                age_hours = (now - occurred).total_seconds() / 3600
            except Exception:
                continue
            # Track oldest unresolved age
            if not l.resolved:
                if age_hours > oldest_age_hours:
                    oldest_age_hours = age_hours
                if age_hours > 24:  # SLA breach: unresolved > 24h
                    sla_breached += 1
            # Track cycle time from resolved lessons
            if l.resolved and l.context and 'eval_duration_ms' in l.context:
                total_cycle_time += l.context.get('eval_duration_ms', 0)
                cycle_count += 1
        avg_cycle_time = total_cycle_time / cycle_count if cycle_count > 0 else 0
        return {
            "total": total, "resolved": resolved, "unresolved": total - resolved,
            "by_category": by_category,
            "sla": {
                "total_breaches": sla_breached,
                "avg_cycle_time_ms": round(avg_cycle_time, 2),
                "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 0.0,
                "unresolved_aging_hours": round(oldest_age_hours, 1),
            },
        }

    def _load(self) -> None:
        if not self._path.exists():
            self._lessons = []
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._lessons = [Lesson(**item) for item in raw]
            for l in self._lessons:
                if isinstance(l.severity, str):
                    l.severity = LessonSeverity(l.severity)
        except Exception as exc:
            logger.warning("Failed to load lessons: %s", exc)
            self._lessons = []

    def _save(self) -> None:
        raw = [{"id": l.id, "category": l.category, "severity": l.severity.value if isinstance(l.severity, LessonSeverity) else l.severity,
                "summary": l.summary, "detail": l.detail, "context": {**l.context, "_sla_tracked": True},
                "occurred_at": l.occurred_at, "resolved": l.resolved, "resolution": l.resolution}
               for l in self._lessons]
        self._path.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# 4. AUTONOMOUS TRADING PIPELINE
# ---------------------------------------------------------------------------

@dataclass
class PipelineStep:
    name: str
    status: str = "pending"
    duration_ms: float = 0.0
    result: Any = None
    error: str = ""


@dataclass
class SlaMetrics:
    total_duration_ms: float = 0.0
    data_to_signal_ms: float = 0.0
    signal_to_risk_ms: float = 0.0
    risk_to_exec_ms: float = 0.0
    closed_trade_to_eval_ms: float = 0.0
    eval_to_evolve_ms: float = 0.0
    cycle_time_ms: float = 0.0
    trades_evaluated: int = 0
    evolutions_triggered: int = 0
    lessons_recorded: int = 0
    avg_eval_time_ms: float = 0.0
    sla_breached: bool = False
    sla_threshold_ms: float = 300000.0  # 5 min default


@dataclass
class PipelineResult:
    symbol: str
    success: bool
    signal: str = "hold"
    confidence: float = 0.0
    reason: str = ""
    strategy: str = ""
    self_reflection: Any = None
    steps: list[PipelineStep] = field(default_factory=list)
    decision: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    sla: SlaMetrics = field(default_factory=SlaMetrics)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class AutonomousPipeline:
    """End-to-end autonomous trading pipeline."""

    def __init__(self, self_correction: SelfCorrection | None = None):
        self.correction = self_correction or SelfCorrection()
        self._strategies: dict[str, type] = {}
        self._lifecycle: Any = None
        self._llm_router: Any = None
        self._last_result: PipelineResult | None = None
        self._data_manager: Any = None
        self._data_monitor: Any = None
        self._run_lock = asyncio.Lock()
        # P0: Self-Aware capability (user's #1 dream — was ABSENT).
        self._self_aware = SelfAware()
        self._position_tracker: dict[str, dict] = {}
        self._init_services()

    def _pipeline_self_state(self) -> "SelfState":
        """State provider for the SelfAware module — reflects THIS pipeline's
        real internal state so the organism can reason about itself."""
        from quant_nanggroe.engine.self_aware import SelfState
        rm = getattr(self._risk_manager, "state", None) if hasattr(self, "_risk_manager") else None

        # GATE-3 wiring (2026-08-22): feed closed-trade awareness into the
        # organism's self-model so reflect() reasons over REAL trade outcomes
        # and lessons, not just risk counters. Fail-closed: never crash.
        awareness_summary = {}
        try:
            from quant_nanggroe.engine.analytics.trade_awareness import explain_journal
            items = explain_journal(limit=25)
            if items:
                goods = [i for i in items if i["severity"] == "good"]
                bads = [i for i in items if i["severity"] == "bad"]
                bad_strats: dict[str, int] = {}
                for b in bads:
                    bad_strats[b["strategy"]] = bad_strats.get(b["strategy"], 0) + 1
                worst = max(bad_strats, key=bad_strats.get) if bad_strats else ""
                awareness_summary = {
                    "recent_closed": len(items),
                    "wins": len(goods),
                    "losses": len(bads),
                    "worst_strategy": worst,
                    "top_lesson": (bads[0]["lesson"] if bads else
                                   (goods[0]["lesson"] if goods else "")),
                }
        except Exception as exc:  # noqa: BLE001
            logger.debug("awareness feed skipped: %s", exc)

        return SelfState(
            equity=getattr(rm, "current_equity", 0.0) or 0.0,
            peak_equity=getattr(rm, "peak_equity", 0.0) or 0.0,
            daily_pnl=getattr(rm, "daily_pnl", 0.0) or 0.0,
            total_trades=getattr(rm, "trade_count_today", 0) or 0,
            open_positions=len(getattr(rm, "active_positions", []) or []),
            veto_count=getattr(self._risk_manager, "_veto_count", 0) if hasattr(self, "_risk_manager") else 0,
            approval_count=getattr(self._risk_manager, "_approval_count", 0) if hasattr(self, "_risk_manager") else 0,
            losing_streak=self._self_aware._history[-1].losing_streak if self._self_aware._history else 0,
            last_strategy=self._last_result.strategy if self._last_result else "",
            last_symbol=self._last_result.symbol if self._last_result else "",
            last_run_ts=time.time(),
            extra={"pipeline": "AutonomousPipeline",
                   "trade_awareness": awareness_summary},
        )

    def reflect_self(self) -> "Reflection":
        """Expose self-reflection. Safe to call anytime; returns structured
        'I am X because Y' reasoning about the pipeline's own performance."""
        try:
            self._self_aware.set_state_provider(self._pipeline_self_state)
            return self._self_aware.reflect()
        except Exception as e:  # self-awareness must never crash the pipeline
            from quant_nanggroe.engine.self_aware import Reflection
            return Reflection(verdict="UNKNOWN", statements=[f"self-reflection unavailable: {e}"], metrics={}, anomalies=[])

    def _ensure_data_manager(self) -> Any:
        if self._data_manager is not None:
            return self._data_manager
        try:
            from quant_nanggroe.data.manager import DataProviderManager
            from quant_nanggroe.data.providers.yahoo import YahooFinanceProvider
            dm = DataProviderManager(default_cache_ttl=300.0)
            dm.register(YahooFinanceProvider(), markets=["stocks", "forex", "crypto"])
            for _module_name, _market in (
                ("binance", "crypto"), ("finnhub_provider", "stocks"), ("fred", "macro"),
                ("alpaca", "stocks"), ("polygon", "stocks"), ("alpha_vantage", "stocks"), ("twelvedata", "stocks"),
            ):
                try:
                    mod = __import__(f"quant_nanggroe.data.providers.{_module_name}", fromlist=["__all__"])
                    from quant_nanggroe.data.providers.base import DataProvider
                    for _attr in dir(mod):
                        obj = getattr(mod, _attr)
                        if isinstance(obj, type) and issubclass(obj, DataProvider) and obj is not DataProvider and not _attr.startswith("_"):
                            try:
                                dm.register(obj(), markets=[_market])
                            except Exception:
                                continue
                            break
                except Exception:
                    continue
            self._data_manager = dm
        except Exception as exc:
            logger.warning("DataProviderManager init failed (%s) — falling back to yfinance", exc)
            self._data_manager = None
        return self._data_manager

    def _init_services(self) -> None:
        """Lazy-init core services and QNA components."""
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

        # ── QNA Core Components ──
        self._final_decider = None
        self._strategy_logger = None
        self._pnl_evaluator = None
        self._regime_filter = None
        self._gene_loader = None
        self._aihf_bridge = None
        self._hf_bridge = None
        self._trade_lifecycle = None
        self._trailing_stop = None

        # Init TrailingStopManager
        try:
            from quant_nanggroe.engine.risk.trailing_stop import TrailingStopManager
            self._trailing_stop = TrailingStopManager()
            logger.info("TrailingStopManager initialized")
        except ImportError:
            self._trailing_stop = None

        if _HAS_FINAL_DECIDER:
            try:
                self._final_decider = FinalDecider(min_confidence_threshold=0.60, min_regime_compatibility=0.35, risk_per_trade=0.015, min_rr_ratio=3.5)  # Phase5 grid 2026-08-28
                logger.info("FinalDecider initialized")
            except Exception as exc:
                logger.warning("FinalDecider init failed: %s", exc)

        if _HAS_STRATEGY_LOGGER:
            try:
                self._strategy_logger = StrategyLogger(log_dir="data")
                logger.info("StrategyLogger initialized")
            except Exception as exc:
                logger.warning("StrategyLogger init failed: %s", exc)

        if _HAS_PNL_EVALUATOR:
            try:
                self._pnl_evaluator = PnLEvaluator(stats_dir="data/strategy_stats")
                logger.info("PnLEvaluator initialized")
            except Exception as exc:
                logger.warning("PnLEvaluator init failed: %s", exc)

        # StrategyEvolver — validation gate for MUE-X mutations
        if _HAS_STRATEGY_EVOLVER:
            try:
                self._strategy_evolver = StrategyEvolver()
                logger.info("StrategyEvolver initialized (mutation validation gate active)")
                try:
                    self._self_finetuner = SelfFineTuner()
                    logger.info("SelfFineTuner initialized (auto-optimize active)")
                except Exception:
                    self._self_finetuner = None
            except Exception as exc:
                self._strategy_evolver = None
                logger.warning("StrategyEvolver init failed: %s", exc)
        else:
            self._strategy_evolver = None

        # TradeLifecycleManager — closed trade → evaluation → evolution loop
        # Wired with evolve_callback for auto-evolve on recommendation==evolve
        if _TradeLifecycleManager is not None:
            try:
                self._trade_lifecycle = _TradeLifecycleManager(
                    pnl_evaluator=self._pnl_evaluator,
                    self_correction=self.correction,
                    sla_threshold_ms=300000.0,
                    evolve_callback=self._trigger_evolution,
                )
                logger.info("TradeLifecycleManager initialized (auto-evolve wired: recommendation=evolve → _trigger_evolution)")
            except Exception as exc:
                logger.warning("TradeLifecycleManager init failed: %s", exc)

        if _HAS_REGIME_FILTER:
            try:
                self._regime_filter = RegimeStrategyFilter()
                logger.info("RegimeStrategyFilter initialized")
            except Exception as exc:
                logger.warning("RegimeFilter init failed: %s", exc)

        if _HAS_GENE_LOADER:
            try:
                self._gene_loader = GeneLoader()
                logger.info("GeneLoader initialized")
            except Exception as exc:
                logger.warning("GeneLoader init failed: %s", exc)

        # AutoRegistry — self-discovery of all components (no manual __all__)
        if _HAS_AUTO_REGISTRY:
            try:
                self._auto_registry = AutoRegistry()
                # Auto-generate __init__.py for dirs missing one
                base = Path(__file__).resolve().parent.parent.parent
                inits = self._auto_registry.ensure_init_files(base)
                if inits:
                    logger.info("Auto-generated %d __init__.py files", inits)
                # Scan ALL directories WITHOUT base_class filter
                discovered = self._auto_registry.scan_all()
                total = self._auto_registry.count()
                logger.info("AutoRegistry discovered %d components across %d dirs", total, len(discovered))
                # Health check
                health = self._auto_registry.health_check()
                if health["stale_count"]:
                    logger.warning("AutoRegistry: %d stale entries cleaned", health["stale_count"])
                if health["missing_init_count"]:
                    logger.warning("AutoRegistry: %d dirs still missing __init__.py", health["missing_init_count"])
            except Exception as exc:
                self._auto_registry = None
                logger.warning("AutoRegistry init failed: %s", exc)
        else:
            self._auto_registry = None

        if _HAS_AIHF_BRIDGE:
            try:
                self._aihf_bridge = AIHFBridge()
                logger.info("AIHFBridge initialized with 20 agents")
            except Exception as exc:
                logger.warning("AIHFBridge init failed: %s", exc)

        if _HAS_HF_BRIDGE:
            try:
                self._hf_bridge = HedgeFundBridge()
                logger.info("HedgeFundBridge initialized")
            except Exception as exc:
                logger.warning("HedgeFundBridge init failed: %s", exc)

    def _compute_atr(self, df: Any, period: int = 14) -> float:
        """Compute ATR from OHLCV. Returns 0.0 if data insufficient."""
        if df is None or not hasattr(df, 'columns') or len(df) < period + 1:
            return 0.0
        try:
            high = df['high'].values if 'high' in df.columns else None
            low = df['low'].values if 'low' in df.columns else None
            close = df['close'].values if 'close' in df.columns else None
            if high is None or low is None or close is None:
                return 0.0
            tr = np.maximum(
                high[1:] - low[1:],
                np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
            )
            atr = float(np.mean(tr[-period:])) if len(tr) >= period else float(np.mean(tr))
            return atr if atr > 0 else 0.0
        except Exception:
            return 0.0

    def load_strategies(self, directory: str | None = None, base_class: type | None = None) -> int:
        """Auto-discover and register strategy classes + MUE-X genes."""
        self._strategies = discover_strategies(directory, base_class)
        count = len(self._strategies)
        if self._lifecycle:
            for name in self._strategies:
                self._lifecycle.register_strategy(name)
        genes_loaded = 0
        if self._gene_loader is not None:
            try:
                genes_discovered = self._gene_loader.discover_genes()
                if genes_discovered > 0:
                    genes_loaded = self._gene_loader.register_all()
                    if self._lifecycle:
                        for gname in self._gene_loader.get_all_gene_names():
                            self._lifecycle.register_strategy(gname)
            except Exception as exc:
                logger.warning("MUE-X gene loading failed: %s", exc)
        total = count + genes_loaded
        logger.info("Loaded %d strategies (%d canonical + %d genes)", total, count, genes_loaded)
        return total

    def list_available_strategies(self) -> list[str]:
        """Return list of available strategy names."""
        return list(self._strategies.keys())

    async def run(self, symbol: str, strategy_name: str | None = None, use_llm: bool = False, data: Any = None, timeframe: str = "D1") -> PipelineResult:
        await self._run_lock.acquire()
        try:
            steps: list[PipelineStep] = []
            result = PipelineResult(symbol=symbol, success=False, decision={})

            # ── Step 1: Data ────────────────────────────────────────────
            s1 = PipelineStep(name="data_fetch")
            try:
                s1.status = "running"
                t0 = time.perf_counter()
                df = await self._fetch_data(symbol, data, timeframe=timeframe)
                s1.duration_ms = (time.perf_counter() - t0) * 1000
                if df is None or (hasattr(df, 'empty') and df.empty):
                    raise ValueError("No data returned")
                s1.status = "passed"
                s1.result = f"{len(df)} bars"
                latest_price = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
                self._feed_price_to_paper(symbol, latest_price)
            except Exception as exc:
                s1.status = "failed"
                s1.error = str(exc)
                self.correction.record("data_fetch", f"Data fetch failed for {symbol}", str(exc), LessonSeverity.ERROR)
            steps.append(s1)
            if s1.status == "failed":
                result.reason = f"Data fetch failed: {s1.error}"
                result.steps = steps
                return result

            current_price = float(df['close'].iloc[-1]) if hasattr(df, 'iloc') else 0.0

            # R2 hotfix: regime must exist BEFORE the trailing-stop monitor —
            # its exit path passes regime into _make_decision; referencing the
            # not-yet-assigned local raised UnboundLocalError (swallowed), so
            # every GATE-7 protective exit died silently.
            regime = "unknown"

            # ── Step 1.2b: Trailing-stop / Breakeven monitor ────────────
            # GATE-7 fix (2026-08-22): TrailingStopManager.update() was NEVER
            # called on the live path — positions were tracked but no price
            # ever fed in, so breakeven/ATR trailing were dead code. Now every
            # cycle feeds the current price (+ATR when available) per symbol.
            if self._trailing_stop is not None:
                try:
                    atr_val = None
                    try:
                        if all(c in df.columns for c in ("high", "low", "close")) and len(df) >= 15:
                            h, l, c = df["high"], df["low"], df["close"]
                            pc = c.shift(1)
                            tr = pd.concat([
                                (h - l),
                                (h - pc).abs(),
                                (l - pc).abs(),
                            ], axis=1).max(axis=1)
                            atr_val = float(tr.rolling(14).mean().iloc[-1])
                    except Exception:
                        atr_val = None
                    fired = self._trailing_stop.update(symbol, current_price, atr=atr_val)
                    if fired:
                        logger.info(
                            "TrailingStop FIRED for %s @ %.2f — closing position",
                            symbol, current_price,
                        )
                        s_ts = PipelineStep(name="trailing_stop_exit")
                        try:
                            exit_sig = "sell"  # tracked entries are longs
                            await self._make_decision(
                                symbol=symbol, signal=exit_sig, confidence=0.0,
                                current_price=current_price,
                                regime=regime,
                                decision={"strategy_name": "trailing_stop",
                                          "reason": "trailing_stop_exit"},
                                reduce_only=True,
                            )
                            s_ts.status = "passed"
                            s_ts.result = f"exit executed @ {current_price:.2f}"
                        except Exception as exc:
                            s_ts.status = "failed"
                            s_ts.error = str(exc)
                        steps.append(s_ts)
                except Exception as exc:
                    logger.debug("TrailingStop update skipped for %s: %s", symbol, exc)
            regime_confidence = 0.0
            try:
                from quant_nanggroe.engine.regime.enhanced_regime import (
                    detect_enhanced_regime,
                )
                er = detect_enhanced_regime(df)
                regime = er.regime
                regime_confidence = er.confidence
                result.decision["regime"] = {
                    "regime": regime,
                    "confidence": regime_confidence,
                    "scores": er.scores,
                }
                logger.debug("Enhanced regime %s: %s conf=%.2f",
                             symbol, regime, regime_confidence)
            except Exception as exc:
                logger.warning("Enhanced regime failed, falling back: %s", exc)
                # Fallback to legacy detector
                try:
                    from quant_nanggroe.engine.autoswitch import REGIME_STRATEGY_MAP, StrategyType
                    from quant_nanggroe.engine.market_state import MarketRegimeDetector
                    closes = df["close"].tolist() if "close" in df.columns else []
                    volumes = df["volume"].tolist() if "volume" in df.columns else None
                    detector = MarketRegimeDetector()
                    regime_result = detector.detect(closes, volumes, symbol)
                    regime = regime_result.regime.value if hasattr(regime_result, "regime") else "unknown"
                    regime_confidence = regime_result.confidence if hasattr(regime_result, "confidence") else 0.0
                    strategy_type = REGIME_STRATEGY_MAP.get(regime_result.regime, StrategyType.PAUSED)
                    result.decision["regime"] = {"regime": regime, "confidence": regime_confidence, "strategy_type": strategy_type.value}
                except Exception as exc2:
                    logger.warning("Legacy regime also failed: %s", exc2)

            # ── AIHF Bridge Signals (before council/ensemble) ──────────
            aihf_signal_override = None
            if self._aihf_bridge is not None:
                try:
                    aihf_signals = await self._aihf_bridge.get_all_signals(symbol)
                    if aihf_signals and len(aihf_signals) > 0:
                        total_conf = sum(s.confidence for s in aihf_signals)
                        buy_conf = sum(s.confidence for s in aihf_signals if s.action.value.lower() == "buy")
                        sell_conf = sum(s.confidence for s in aihf_signals if s.action.value.lower() == "sell")
                        if total_conf > 0:
                            buy_pct = buy_conf / total_conf
                            sell_pct = sell_conf / total_conf
                            if buy_pct > sell_pct and buy_pct > 0.3:
                                aihf_signal_override = ("buy", buy_pct)
                            elif sell_pct > buy_pct and sell_pct > 0.3:
                                aihf_signal_override = ("sell", sell_pct)
                        result.decision["aihf"] = {"agents_contributing": len(aihf_signals), "buy_confidence": buy_conf, "sell_confidence": sell_conf}
                        logger.info("AIHF Bridge: %d agents contributed signals for %s", len(aihf_signals), symbol)
                except Exception as exc:
                    logger.warning("AIHF Bridge signals failed: %s", exc)

            # ── Hedge Fund Bridge — get weighted vote from hedge_fund providers
            hf_signal_override = None
            if self._hf_bridge is not None and _HAS_HF_BRIDGE:
                try:
                    hf_result = self._hf_bridge.get_signal(symbol)
                    if hf_result.get("bias") in ("buy", "sell"):
                        hf_conf = hf_result["confidence"]
                        hf_bias = hf_result["bias"]
                        hf_signal_override = (hf_bias, hf_conf)
                        result.decision["hedge_fund"] = {
                            "bias": hf_bias,
                            "confidence": hf_conf,
                            "providers": len(hf_result.get("votes", [])),
                            "source": hf_result.get("source", "hf_vote"),
                        }
                        logger.info(
                            "HedgeFundBridge: vote=%s @ %.2f from %d providers",
                            hf_bias, hf_conf, len(hf_result.get("votes", [])),
                        )
                except Exception as exc:
                    logger.warning("HedgeFundBridge signal failed: %s", exc)

            # ── Step 2: Signal ──────────────────────────────────────────
            s2 = PipelineStep(name="signal_generation")
            try:
                s2.status = "running"
                t0 = time.perf_counter()

                compatible_strategies = None
                if self._regime_filter is not None and regime != "unknown":
                    try:
                        all_strat_names = list(self._strategies.keys())
                        if self._gene_loader:
                            all_strat_names.extend(self._gene_loader.get_all_gene_names())
                        filtered = self._regime_filter.filter_strategies(
                            strategy_names=all_strat_names,
                            regime=regime,
                            min_compat=0.35,
                        )
                        compatible_strategies = [s[0] for s in filtered]
                        logger.info("RegimeFilter: %d/%d strategies compatible with %s regime", len(compatible_strategies), len(all_strat_names), regime)
                    except Exception as exc:
                        logger.warning("RegimeFilter failed (proceeding with all strategies): %s", exc)

                signal_type, confidence, reason = self._generate_signal(symbol, strategy_name, df, regime=regime, compatible_strategies=compatible_strategies)

                if aihf_signal_override is not None and confidence < AIHF_OVERRIDE_THRESHOLD:
                    if aihf_signal_override[1] > confidence:
                        signal_type = aihf_signal_override[0]
                        confidence = aihf_signal_override[1]
                        reason = f"AIHF consensus override: {signal_type} @ {confidence:.2f}"

                if hf_signal_override is not None and confidence < AIHF_OVERRIDE_THRESHOLD:
                    if hf_signal_override[1] > confidence:
                        signal_type = hf_signal_override[0]
                        confidence = hf_signal_override[1]

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

            # ── Step 2.25: Ensemble Voting ──────────────────────────────
            s225 = PipelineStep(name="ensemble_voting")
            try:
                s225.status = "running"
                t0 = time.perf_counter()
                from quant_nanggroe.engine.agentic.ensemble import EnsembleVoter
                voter = EnsembleVoter()
                voted_bias, voted_conf, vote_meta = voter.run(symbol, signal_type, confidence, dataframe=df)
                s225.duration_ms = (time.perf_counter() - t0) * 1000
                s225.status = "passed"
                s225.result = f"{voted_bias} @ {voted_conf:.2f} (consensus={vote_meta.get('consensus_strength', 0):.2f})"
                result.decision["ensemble"] = vote_meta
                if voted_bias != "neutral" and vote_meta.get("consensus_strength", 0) > 0.6:
                    signal_type = voted_bias
                    confidence = voted_conf
                    result.signal = signal_type
                    result.confidence = confidence
            except Exception as exc:
                s225.status = "skipped"
                s225.error = str(exc)
            steps.append(s225)

            # ── Step 2.5: Council Debate ────────────────────────────────
            s25 = PipelineStep(name="council_debate")
            try:
                s25.status = "running"
                t0 = time.perf_counter()
                from quant_nanggroe.engine.agentic.council import DEBATE_THRESHOLD, convene_council
                if confidence < DEBATE_THRESHOLD:
                    debate = convene_council(symbol=symbol, proposed_signal=signal_type, proposed_confidence=confidence, price=current_price, regime=regime)
                    s25.duration_ms = (time.perf_counter() - t0) * 1000
                    if debate.debate_held:
                        signal_type = debate.signal
                        confidence = debate.confidence
                        s25.result = f"Council: {signal_type} @ {confidence:.2f} — {debate.summary}"
                        result.decision["council"] = {"debate_held": True, "votes": debate.votes, "summary": debate.summary, "original_signal": result.signal, "original_confidence": result.confidence}
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
            steps.append(s25)

            # ── Step 2.6: Committee Per-Pair Debate ─────────────────────
            s26 = PipelineStep(name="committee_debate")
            try:
                s26.status = "running"
                t0 = time.perf_counter()
                from quant_nanggroe.engine.agentic.committee import VoteChamber
                chamber = VoteChamber()
                _atr_for_comm = self._compute_atr(df) if df is not None else 0.0
                portfolio_state = {}
                try:
                    rm_state = self._em._risk_manager.state if self._em and hasattr(self._em, '_risk_manager') else None
                    portfolio_state = {
                        "equity": rm_state.current_equity if rm_state else 0,
                        "daily_pnl": rm_state.daily_pnl if rm_state else 0,
                        "open_positions": rm_state.open_positions if rm_state else 0,
                        "max_drawdown": rm_state.max_drawdown if rm_state else 0,
                    }
                except Exception:
                    pass
                committee_vote = chamber.convene(
                    symbol, df,
                    entry_price=current_price,
                    atr=_atr_for_comm,
                    regime=regime,
                    timeframe=timeframe,
                    lot_size=risk_metrics.get("lot_size", 0.01) if 'risk_metrics' in dir() else 0.01,
                    portfolio_state=portfolio_state)
                s26.duration_ms = (time.perf_counter() - t0) * 1000
                if committee_vote.risk_vetoed:
                    s26.result = f"VETOED: {committee_vote.risk_reason}"
                    s26.status = "failed"
                elif committee_vote.final_action != "hold" and committee_vote.consensus_strength > 0.1:
                    signal_type = committee_vote.final_action
                    confidence = committee_vote.final_confidence
                    result.signal = signal_type
                    result.confidence = confidence
                    s26.result = f"{signal_type} @ {confidence:.2f} (consensus={committee_vote.consensus_strength:.2f})"
                    s26.status = "passed"
                else:
                    # committee HOLD does not veto ensemble — ensemble's buy/sell remains unless committee has strong opposite
                    s26.result = f"HOLD (consensus={committee_vote.consensus_strength:.2f}) — ensemble {signal_type} preserved"
                    s26.status = "passed"
                result.decision["committee"] = committee_vote.to_dict()
            except Exception as exc:
                s26.status = "skipped"
                s26.error = str(exc)
            steps.append(s26)

            # ── Step 2.75: Compute ATR early (used by risk + TP/SL) ─────
            _atr_for_risk = self._compute_atr(df) if df is not None else 0.0
            if _atr_for_risk <= 0 and current_price > 0:
                # Per-asset-class ATR fallback (GAP-15 fix)
                if "XAU" in symbol:
                    _atr_for_risk = current_price * 0.003  # Gold: 0.3%
                elif "BTC" in symbol or "ETH" in symbol:
                    _atr_for_risk = current_price * 0.02   # Crypto: 2%
                else:
                    _atr_for_risk = current_price * 0.002  # FX: 0.2% (~20 pips)

            # ── Step 3: Risk Check ──────────────────────────────────────
            s3 = PipelineStep(name="risk_check")
            try:
                s3.status = "running"
                t0 = time.perf_counter()
                risk_ok, risk_reason, risk_metrics = self._check_risk(symbol, signal_type, confidence, current_price=current_price, atr_value=_atr_for_risk, timeframe=timeframe)
                s3.duration_ms = (time.perf_counter() - t0) * 1000
                s3.status = "passed" if risk_ok else "failed"
                s3.result = risk_reason
            except Exception as exc:
                s3.status = "failed"
                s3.error = str(exc)
            steps.append(s3)
            if s3.status == "failed":
                result.reason = f"Risk check blocked: {s3.error}"
                result.steps = steps
                return result

            # ── Step 3.5: Macro/News Context Gate (event-risk veto) ─────
            try:
                from quant_nanggroe.engine.agentic.context_gate import check_event_risk
                ctx = check_event_risk()
                result.decision["context_gate"] = {"vetoed": ctx["vetoed"], "reason": ctx["reason"]}
                if ctx["vetoed"] and signal_type != "hold":
                    s35 = PipelineStep(name="context_gate")
                    s35.status = "failed"
                    s35.result = ctx["reason"]
                    steps.append(s35)
                    result.reason = f"Context gate blocked: {ctx['reason']}"
                    result.steps = steps
                    return result
            except Exception as gate_exc:
                logger.warning("Context gate skipped: %s", gate_exc)

            # ── Step 4: LLM Reasoning ───────────────────────────────────
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

            # ── Step 4.6: Vector Manifold (Klip 00:09-00:23) — observability + boost ──
            try:
                from quant_nanggroe.engine.currency_graph import build_graph_from_mt5
                from quant_nanggroe.engine.vector_manifold import build_manifold
                from quant_nanggroe.engine.euclidean_mispricing import scan_all
                g = build_graph_from_mt5(all_pairs=False)
                rates = g.rates
                if rates:
                    manifold = build_manifold(rates)
                    # P0 as rolling mean approximation: use manifold itself as P0 for now (distance 0 until history)
                    p0 = {k: v.to_array() for k, v in manifold.items()}
                    mis = scan_all(manifold, p0, sigma=0.05)
                    result.decision["vector"] = {
                        "manifold": {k: v.to_array().tolist() for k, v in manifold.items()},
                        "mispricing": {k: {"d": m.d, "threshold": m.threshold, "is_trigger": m.is_trigger} for k, m in mis.items()},
                    }
                    # Optional boost: if any YEN/CHF/CAD trigger and symbol is in its pair, boost confidence 0.1
                    triggers = [k for k, m in mis.items() if m.is_trigger]
                    if triggers and symbol in ("USDJPY", "EURJPY", "USDJPY.vx", "EURJPY.vx", "USDCHF", "EURCHF.vx", "USDCAD", "EURCAD.vx", "EURUSD", "EURUSD.vx"):
                        # do not override, just annotate — live trading still ensemble-driven
                        result.decision["vector"]["boost"] = triggers
            except Exception as vec_exc:
                logger.debug("Vector manifold skipped: %s", vec_exc)

            # ── Step 4.5: Final Decider ─────────────────────────────────
            if self._final_decider is not None and current_price > 0:
                try:
                    from quant_nanggroe.engine.agentic.final_decider import (
                        Action,
                        PortfolioState,
                        RegimeState,
                        RiskState,
                        StrategySignal,
                    )
                    regime_state = RegimeState(regime=regime if regime != "unknown" else "neutral", confidence=regime_confidence)
                    agg_signal = StrategySignal(
                        strategy_name="ensemble", symbol=symbol,
                        action=Action.BUY if signal_type == "buy" else (Action.SELL if signal_type == "sell" else Action.HOLD),
                        confidence=confidence, regime_compatibility=0.5,
                    )
                    rm_state = getattr(getattr(self._em, '_risk_manager', None), 'state', None)
                    portfolio_state = PortfolioState(
                        total_exposure=0.0, max_exposure=3.0,
                        available_balance=rm_state.current_equity if rm_state else 1000.0,
                    )
                    _daily_loss_pct = (abs(min(0, rm_state.daily_pnl)) / rm_state.peak_equity) if rm_state and rm_state.peak_equity > 0 else 0.0
                    _weekly_loss_pct = (abs(min(0, rm_state.weekly_pnl)) / rm_state.peak_equity) if rm_state and rm_state.peak_equity > 0 else 0.0
                    risk_state = RiskState(
                        kill_switch_active=getattr(getattr(self._em, '_kill_switch', None), 'status', lambda: {})().get('is_active', False) if self._em else False,
                        daily_loss_pct=_daily_loss_pct, weekly_loss_pct=_weekly_loss_pct,
                    )
                    atr_val = self._compute_atr(df)
                    final_decision = self._final_decider.decide(
                        signals=[agg_signal], regime=regime_state, portfolio=portfolio_state,
                        risk=risk_state, atr=atr_val if atr_val > 0 else None, current_price=current_price,
                    )
                    if final_decision.action != Action.HOLD:
                        signal_type = final_decision.action.value
                        confidence = final_decision.confidence
                        result.decision["final_decider"] = {
                            "action": final_decision.action.value, "strategy": final_decision.strategy_name,
                            "confidence": final_decision.confidence, "kelly": final_decision.kelly_fraction, "reason": final_decision.reason,
                        }
                except Exception as exc:
                    logger.warning("FinalDecider skipped: %s", exc)

            # ── Step 5: Execution + StrategyLogger + PnLEvaluator + TradeLifecycle ──
            s5 = PipelineStep(name="execution")
            try:
                s5.status = "running"
                t0 = time.perf_counter()
                _atr_for_exec = self._compute_atr(df) if df is not None else 0.0
                exec_decision = await self._make_decision(symbol, signal_type, confidence, current_price=current_price, regime=regime, decision=result.decision, df=df, atr_value=_atr_for_exec, timeframe=timeframe, risk_lot_size=risk_metrics.get("lot_size", 0.0))
                s5.duration_ms = (time.perf_counter() - t0) * 1000
                if exec_decision.get("error"):
                    s5.status = "failed"
                    s5.error = exec_decision["error"]
                elif exec_decision.get("execution") == "rejected":
                    # R3 hotfix: a REJECTED order must not report success —
                    # downstream scheduler derived traded=True from success and
                    # sent fake "TRADE EXECUTED" Telegram alerts.
                    s5.status = "failed"
                    s5.error = f"rejected: {exec_decision.get('reason', 'no fill')}"
                else:
                    s5.status = "passed"
                s5.result = exec_decision.get("action", "hold")
                result.decision["execution"] = exec_decision

                trigger_strategy = "ensemble"
                if result.decision.get("final_decider"):
                    trigger_strategy = result.decision["final_decider"].get("strategy", "ensemble")
                atr_value = self._compute_atr(df)

                if self._strategy_logger is not None and exec_decision.get("action") in ("buy", "sell"):
                    try:
                        log_entry = {
                            "symbol": symbol, "action": exec_decision["action"],
                            "strategy_name": trigger_strategy, "confidence": confidence,
                            "market_regime": regime, "entry_price": current_price,
                            "volume": exec_decision.get("position_size_pct", 0.01),
                            "sl": exec_decision.get("sl", current_price - atr_value * 1.5 if exec_decision.get("action") == "buy" else current_price + atr_value * 1.5),
                            "tp": exec_decision.get("tp", current_price + atr_value * 3.0 if exec_decision.get("action") == "buy" else current_price - atr_value * 3.0),
                            "atr": atr_value,
                        }
                        self._strategy_logger.log_trigger(log_entry)
                    except Exception as exc:
                        logger.warning("StrategyLogger failed: %s", exc)

                # Record signal context for journal_sync linking (always, not just when logger loaded)
                if exec_decision.get("action") in ("buy", "sell"):
                    try:
                        from quant_nanggroe.engine.journal_sync import record_signal_context
                        _sl = exec_decision.get("sl", 0.0)
                        _tp = exec_decision.get("tp", 0.0)
                        _lot = risk_metrics.get("lot_size", 0.01)
                        record_signal_context(
                            symbol=symbol, strategy=trigger_strategy,
                            entry_price=current_price, sl=_sl, tp=_tp,
                            confidence=confidence, atr=atr_value, lot_size=_lot)
                    except Exception:
                        pass
                    # Wire to strategy_evaluator for auto-disable tracking
                    try:
                        from quant_nanggroe.engine.agentic.strategy_evaluator import StrategyEvaluator
                        _ticket = exec_decision.get("ticket", 0)
                        if _ticket:
                            StrategyEvaluator().record_signal(
                                trigger_strategy, symbol, _ticket, current_price)
                    except Exception:
                        pass

                # ── Notification: send Telegram alert on trade execution ──
                if exec_decision.get("action") in ("buy", "sell") and exec_decision.get("execution") == "filled":
                    try:
                        from quant_nanggroe.notifier import send_telegram
                        _emoji = "🟢" if exec_decision["action"] == "buy" else "🔴"
                        _msg = (
                            f"{_emoji} *QNA Trade Executed*\n"
                            f"*{symbol}* | `{exec_decision['action'].upper()}`\n"
                            f"Price: `{exec_decision.get('fill_price', current_price):.5f}`\n"
                            f"Confidence: `{confidence:.0%}` | Regime: {regime}\n"
                            f"Strategy: {trigger_strategy}\n"
                            f"Time: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
                        )
                        send_telegram(_msg)
                    except Exception as _notify_err:
                        logger.debug("Trade notification failed: %s", _notify_err)

                # ── NEW: TradeLifecycleManager — closed trade → eval → evolve ──
                if self._trade_lifecycle is not None and ClosedTrade is not None:
                    try:
                        action = exec_decision.get("action", "hold")
                        if action in ("buy", "sell") and exec_decision.get("execution") == "filled":
                            fill_price = exec_decision.get("fill_price", current_price)
                            tracked = self._position_tracker.get(symbol)
                            pnl = exec_decision.get("pnl", 0.0)
                            entry_price = fill_price
                            exit_price = 0.0
                            if tracked and tracked["side"] != action:
                                entry_price = tracked["entry_price"]
                                exit_price = fill_price
                                if action == "sell":
                                    pnl = (exit_price - entry_price) * tracked["qty"]
                                else:
                                    pnl = (entry_price - exit_price) * tracked["qty"]
                                self._position_tracker.pop(symbol, None)
                            else:
                                self._position_tracker[symbol] = {"entry_price": fill_price, "qty": exec_decision.get("position_size_pct", 0.01), "side": action}
                            trade = ClosedTrade(
                                trade_id=exec_decision.get("order_id", str(uuid.uuid4())[:12]),
                                strategy_name=trigger_strategy,
                                symbol=symbol,
                                entry_price=entry_price,
                                exit_price=exit_price,
                                volume=exec_decision.get("position_size_pct", 0.01),
                                side=action,
                                entry_time=exec_decision.get("timestamp", result.timestamp),
                                exit_time=exec_decision.get("exit_time", ""),
                                pnl=pnl,
                                regime_at_entry=regime,
                                confidence_at_entry=confidence,
                            )
                            lifecycle_context = {
                                "symbol": symbol,
                                "confidence": confidence,
                                "regime": regime,
                                "pipeline_duration_ms": sum(s.duration_ms for s in steps),
                            }
                            lifecycle_record = self._trade_lifecycle.process_closed_trade(
                                trade, lifecycle_context
                            )
                            result.decision["trade_lifecycle"] = lifecycle_record.to_dict()

                            # Populate SLA lifecycle metrics
                            self._trade_lifecycle.populate_sla_metrics(
                                result.sla, [lifecycle_record]
                            )

                            if lifecycle_record.lesson_id:
                                result.decision["lifecycle_lesson"] = {
                                    "id": lifecycle_record.lesson_id,
                                    "sla_breached": lifecycle_record.sla_breached,
                                    "closed_trade_to_eval_ms": lifecycle_record.closed_trade_to_eval_ms,
                                    "eval_to_evolve_ms": lifecycle_record.eval_to_evolve_ms,
                                }
                    except Exception as exc:
                        logger.warning("TradeLifecycleManager processing failed: %s", exc)

            except Exception as exc:
                s5.status = "failed"
                s5.error = str(exc)
            steps.append(s5)

            result.success = s5.status != "failed"
            result.reason = f"Pipeline complete: {signal_type} @ {confidence:.1%}"
            result.steps = steps

            # ── Populate SLA metrics ────────────────────────────────────
            total_ms = sum(s.duration_ms for s in steps)
            result.sla.total_duration_ms = total_ms
            if len(steps) >= 2:
                pass  # data_to_signal_ms now set with dynamic lookup below
            if len(steps) >= 4:
                result.sla.signal_to_risk_ms = sum(s.duration_ms for s in steps[2:4])
                # Dynamic step lookup: find 'execution' step by name (handles use_llm=True shifting indices)
                exec_step = next((s for s in steps if s.name == 'execution'), None)
                result.sla.risk_to_exec_ms = (exec_step.duration_ms if exec_step else 0.0)
                result.sla.data_to_signal_ms = sum(s.duration_ms for s in steps[:2])
            result.sla.lessons_recorded = len(self.correction._lessons)
            result.sla.sla_breached = total_ms > result.sla.sla_threshold_ms
            self._last_result = result
            # P0: Self-Aware — reflect on own performance after every run.
            try:
                result.self_reflection = self.reflect_self()
            except Exception:
                pass
            return result
        finally:
            self._run_lock.release()

    def _generate_signal(self, symbol: str, strategy_name: str | None, df: Any, regime: str = "unknown", compatible_strategies: list[str] | None = None) -> tuple[str, float, str]:
        """Generate signal via ensemble. If compatible_strategies provided, filters by regime."""
        if strategy_name:
            # Evaluator gate: check if strategy is disabled
            try:
                from quant_nanggroe.engine.agentic.strategy_evaluator import StrategyEvaluator
                evaluator = StrategyEvaluator()
                if not evaluator.is_strategy_enabled(strategy_name, symbol):
                    return "hold", 0.0, f"Strategy {strategy_name} auto-disabled by evaluator"
            except Exception:
                pass
            try:
                from quant_nanggroe.engine.strategies import create_strategy
                strategy = create_strategy(strategy_name, lifecycle=self._lifecycle)
            except (ImportError, ValueError) as exc:
                return "hold", 0.0, f"Strategy not found: {exc}"
            result = strategy.generate_signal(df) if hasattr(strategy, 'generate_signal') else None
            return self._extract_signal(result, strategy_name)
        return self._ensemble_signal(symbol, df, regime, compatible_strategies)

    def _ensemble_signal(self, symbol: str, df: Any, regime: str, compatible_strategies: list[str] | None = None) -> tuple[str, float, str]:
        """Run top strategies + MUE-X genes, aggregate via regime-weighted voting."""
        regime_weights = {
            "trending_up": {"momentum": 1.5, "trend": 1.5, "mean_reversion": 0.5, "volatility": 0.8, "pattern": 0.3},
            "trending_down": {"momentum": 1.5, "trend": 1.5, "mean_reversion": 0.5, "volatility": 0.8, "pattern": 0.3},
            "ranging": {"momentum": 0.5, "trend": 0.5, "mean_reversion": 1.5, "volatility": 1.0, "pattern": 0.5},
            "volatile": {"momentum": 0.8, "trend": 0.7, "mean_reversion": 1.0, "volatility": 1.5, "pattern": 0.3},
            "crisis": {"momentum": 0.3, "trend": 0.5, "mean_reversion": 1.5, "volatility": 1.2, "pattern": 0.2},
            "recovery": {"momentum": 1.2, "trend": 1.0, "mean_reversion": 0.8, "volatility": 0.7, "pattern": 0.3},
            "unknown": {"momentum": 1.0, "trend": 1.0, "mean_reversion": 1.0, "volatility": 1.0, "pattern": 0.5},
        }
        weights = regime_weights.get(regime, regime_weights["unknown"])

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
            return "momentum"

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
            from quant_nanggroe.engine.strategies import create_strategy, list_strategies
            all_names = list_strategies()
            if self._lifecycle:
                active = set(self._lifecycle.get_active_strategies())
                if active:
                    filtered = [n for n in all_names if n in active]
                    if filtered:
                        all_names = filtered
                    else:
                        logger.warning(
                            "Lifecycle active set (%s) has no overlap with registry — "
                            "using all %d strategies", active, len(all_names))
            # CANONICAL §15.6 per-symbol CPCV allocation: admit only strategies
            # with proven combo-profit-share on THIS symbol's asset class.
            # Fail-closed: evidence missing -> None -> keep lifecycle behavior;
            # evidence present but nothing qualifies -> no unproven trading.
            try:
                from quant_nanggroe.engine.strategy_allocation import admitted_for_symbol
                admitted = admitted_for_symbol(symbol, all_strategies=all_names)
                if admitted is not None:
                    all_names = admitted
                    logger.info("CPCV allocation narrowed %s candidates to %d",
                             symbol, len(all_names))
            except Exception as alloc_exc:
                logger.debug("strategy allocation skipped: %s", alloc_exc)
        except (ImportError, ValueError):
            return "hold", 0.0, "Cannot load strategy registry"

        if self._gene_loader:
            try:
                gene_names = self._gene_loader.get_all_gene_names()
                all_names.extend(gene_names)
            except Exception:
                pass

        if compatible_strategies is not None:
            all_names = [n for n in all_names if n in compatible_strategies]
            if not all_names:
                return "hold", 0.0, f"No strategies compatible with {regime} regime"

        candidates = []
        for name in priority:
            if name in all_names and name not in candidates:
                candidates.append(name)
        for name in all_names:
            if name not in candidates and len(candidates) < 15:
                candidates.append(name)

        # ── Strategy Evaluator: filter out auto-disabled strategies ──
        try:
            from quant_nanggroe.engine.agentic.strategy_evaluator import StrategyEvaluator
            evaluator = StrategyEvaluator()
            candidates = [n for n in candidates if evaluator.is_strategy_enabled(n, symbol)]
            if len(candidates) < len(all_names):
                logger.info("Evaluator filtered %d disabled strategies for %s",
                         len(all_names) - len(candidates), symbol)
        except Exception as eval_exc:
            logger.debug("StrategyEvaluator skipped: %s", eval_exc)

        signals: list[tuple[str, float, str, str]] = []
        signals_named: list[tuple[str, float, str, str, str]] = []
        for name in candidates:
            try:
                strat = create_strategy(name, lifecycle=self._lifecycle)
                # Per-symbol tuned params (CANONICAL 15.6 → tuning_results):
                try:
                    from quant_nanggroe.engine.strategy_allocation import best_params_for
                    tuned = best_params_for(name, symbol)
                    if tuned and hasattr(strat, "_parameters"):
                        for k, v in tuned.items():
                            strat._parameters.set(k, v)
                        logger.debug("Injected tuned params for %s on %s: %s",
                                     name, symbol, tuned)
                except Exception:
                    pass  # tuning is additive — never block signal generation
                result = strat.generate_signal(df)
                sig, conf, reason = self._extract_signal(result, name)
                cat = _classify(name)
                if sig != "hold" and conf > 0.0:
                    signals.append((sig, conf, reason, cat))
                    signals_named.append((sig, conf, reason, cat, name))
            except Exception:
                continue

        self._record_strategy_signals(symbol, df, signals)

        if not signals:
            return "hold", 0.0, "No strategy produced a signal"

        # ── Signal Aggregation Engine (v8.0) ────────────────────────
        try:
            from quant_nanggroe.engine.execution.signal_aggregator import (
                SignalAggregator,
                StrategyVote,
            )
            agg = SignalAggregator(min_conviction=0.30, risk_per_symbol=0.005)

            votes: list[StrategyVote] = []
            for sig, conf, reason, cat, sname in signals_named:
                from quant_nanggroe.engine.strategy_allocation import best_params_for
                tuned = best_params_for(sname, symbol)
                w = 1.2 if tuned else 1.0  # boosted weight for tuned strategies
                votes.append(StrategyVote(
                    strategy_name=sname or cat,
                    direction=sig,
                    confidence=conf,
                    weight=w,
                    tuned_params=tuned or {},
                ))

            aggregated = agg.aggregate(symbol, votes)

            if not aggregated.should_trade:
                return ("hold", aggregated.conviction,
                        f"Signal aggregation: conviction={aggregated.conviction:.2f} "
                        f"< threshold ({aggregated.direction}, "
                        f"buy_w={aggregated.buy_weight:.2f} sell_w={aggregated.sell_weight:.2f})")

            return (
                aggregated.direction,
                min(aggregated.conviction, 1.0),
                f"Aggregated [{aggregated.direction}] conviction="
                f"{aggregated.conviction:.2f} contributors="
                f"{aggregated.contributors} opposers={aggregated.opposers}",
            )
        except ImportError:
            pass  # fallback to legacy below

        # Legacy ensemble voting (kept as fallback if aggregator import fails)
        total_weight = sum(weights.get(cat, 1.0) for _, _, _, cat in signals)
        buy_weight = sum(c * weights.get(cat, 1.0) for sig, c, _, cat in signals if sig == "buy")
        sell_weight = sum(c * weights.get(cat, 1.0) for sig, c, _, cat in signals if sig == "sell")

        if total_weight == 0:
            return "hold", 0.0, "All signals zero weight"

        buy_pct = buy_weight / total_weight
        sell_pct = sell_weight / total_weight

        if buy_pct > sell_pct and buy_pct > 0.3:
            return "buy", min(buy_pct, 1.0), f"Ensemble: buy={buy_pct:.0%} sell={sell_pct:.0%}"
        elif sell_pct > buy_pct and sell_pct > 0.3:
            return "sell", min(sell_pct, 1.0), f"Ensemble: buy={buy_pct:.0%} sell={sell_pct:.0%}"
        else:
            return "hold", 0.0, f"No consensus: buy={buy_pct:.0%} sell={sell_pct:.0%}"

    def _extract_signal(self, result: Any, strategy_name: str) -> tuple[str, float, str]:
        if result is None:
            return "hold", 0.0, "No signal"
        if hasattr(result, 'signal_type'):
            sig = result.signal_type.value
            conf = getattr(result, 'confidence', 0.5)
            reason = getattr(result, 'reasoning', '') or f"{strategy_name} -> {sig}"
            return sig, min(float(conf), 1.0), reason
        import pandas as pd
        if isinstance(result, pd.Series) and len(result) > 0:
            last = result.iloc[-1]
            sig = "buy" if last > 0 else "sell" if last < 0 else "hold"
            conf = abs(float(last))
            return sig, min(conf, 1.0), f"{strategy_name}: {last:.4f}"
        return "hold", 0.0, f"Unknown result: {type(result).__name__}"

    def _record_strategy_signals(self, symbol: str, df: Any, signals: list[tuple[str, float, str, str]]) -> None:
        if df is None or len(df) < 2:
            return
        current_price = float(df['close'].iloc[-1]) if hasattr(df, 'close') else 0.0
        if current_price == 0:
            return
        path = Path(__file__).resolve().parent.parent.parent / "data" / "strategy_signals.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        previous: list[dict] = []
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                previous = []
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
                is_win = (prev_signal == "buy" and price_change > 0.01) or (prev_signal == "sell" and price_change < -0.01)
                try:
                    self._lifecycle.update_strategy(name=strat_name, pnl=price_change, is_win=is_win)
                except Exception:
                    pass
            previous = still_pending
        timenow = datetime.now(timezone.utc).isoformat()
        for sig, conf, reason, cat in signals:
            if sig != "hold":
                previous.append({"symbol": symbol, "strategy": cat, "signal": sig, "price": current_price, "confidence": conf, "timestamp": timenow})
        if len(previous) > 1000:
            previous = previous[-1000:]
        try:
            path.write_text(json.dumps(previous, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    def _check_risk(self, symbol: str, signal: str, confidence: float, current_price: float = 0.0, atr_value: float = 0.0, timeframe: str = "H1") -> tuple[bool, str, dict]:
        metrics = {"max_drawdown": 0.0, "daily_pnl": 0.0, "price": current_price}
        em = self._em
        # FAIL-CLOSED: no execution manager / risk gates wired => BLOCK.
        if em is None or getattr(em, "_risk_manager", None) is None or getattr(em, "_kill_switch", None) is None:
            return False, "FAIL-CLOSED: execution manager / risk gates not wired", metrics
        try:
            ks_status = em._kill_switch.status()
            if ks_status.get("is_active") or ks_status.get("active"):
                return False, "Kill switch active", metrics
            from quant_nanggroe.engine.risk.constants import MAX_RISK_PER_TRADE
            balance = em._risk_manager.state.current_equity
            risk_amount = balance * MAX_RISK_PER_TRADE

            # ATR-based SL via TradingProfile (scalp/day/swing)
            try:
                from quant_nanggroe.engine.risk.trading_profile import compute_sl_tp, detect_profile
                profile = detect_profile(timeframe)
                _atr = atr_value if atr_value > 0 else current_price * 0.005
                sltp = compute_sl_tp(side=signal, entry_price=current_price, atr_value=_atr, timeframe=timeframe)
                stop_loss = sltp["sl"]
            except Exception:
                stop_loss = current_price * (0.985 if signal == "buy" else 1.015)

            stop_distance = abs(current_price - stop_loss)

            # Position sizing: risk$ / (sl_pips × pip_value_per_lot)
            _contract_size = 100000.0
            _pip_value = 10.0
            try:
                # Route through broker handle for thread-safety
                _broker = next(iter(self._em._brokers.values()), None) if self._em else None
                _mt5_handle = getattr(_broker, '_mt5', None)
                if _mt5_handle:
                    _si = _mt5_handle.symbol_info(symbol)
                    if _si:
                        _contract_size = float(getattr(_si, "trade_contract_size", 100000))
                        _tv = float(getattr(_si, "trade_tick_value", 0))
                        _ts = float(getattr(_si, "trade_tick_size", 0.0001))
                        if _tv > 0 and _ts > 0:
                            _pip_value = _tv * (0.0001 / _ts)
            except Exception:
                pass

            _pip_size = 0.0001
            sl_pips = stop_distance / _pip_size if stop_distance > 0 else 1
            lot_size = max(0.01, round(risk_amount / (sl_pips * _pip_value), 2)) if sl_pips > 0 and _pip_value > 0 else 0.01

            # Cap at MAX_POSITION_SIZE_PCT (10%) of equity
            max_notional = balance * 0.10
            max_lots = max_notional / (_contract_size * current_price) if current_price > 0 and _contract_size > 0 else lot_size
            lot_size = min(lot_size, max(0.01, round(max_lots, 2)))

            verdict = em._risk_manager.check_trade(symbol=symbol, direction=signal.upper() if signal != "hold" else "HOLD", lot_size=lot_size, entry=current_price, stop_loss=stop_loss, account_balance=balance)
            if verdict.get("verdict") == "VETOED":
                return False, f"RiskManager vetoed: {verdict.get('reason','?')}", {**metrics, "risk_verdict": "VETOED", "checkpoints": verdict.get("checkpoints", {})}
            metrics.update({"risk_verdict": "APPROVED", "lot_size": lot_size, "stop_loss": stop_loss, "balance": balance, "atr": atr_value, "sl_dist": stop_distance, "pip_value": _pip_value})
        except Exception as exc:
            return False, f"FAIL-CLOSED: risk check error: {exc}", metrics
        if confidence < 0.08:
            return False, f"Confidence {confidence:.2f} below 0.08 floor", metrics
        if signal == "hold":
            return False, "Signal is HOLD", metrics
        return True, f"Risk passed: {signal} @ {confidence:.1%} | lot={lot_size} SL={stop_loss:.5f} ATR={atr_value:.5f}", metrics

    async def _llm_reason(self, symbol: str, signal: str, confidence: float) -> dict[str, Any]:
        """Use 9router combo mode for LLM reasoning. Falls back to standard routing if combo unavailable."""
        prompt = f"Symbol: {symbol}\nTechnical Signal: {signal}\nConfidence: {confidence:.1%}\n\nEvaluate this trade. Provide JSON: {{\"action\":\"buy/sell/hold\",\"reason\":\"...\",\"confidence\":0.0-1.0}}"
        import json as _json
        try:
            response = await asyncio.wait_for(
                self._llm_router.chat(prompt, tier=None, temperature=0.3),
                timeout=15.0  # 9router timeout
            )
            content = response.content.strip()
            if "{" in content:
                json_str = content[content.index("{"):content.rindex("}") + 1]
                parsed = _json.loads(json_str)
                parsed["model"] = "9router-routed"
                return parsed
            return {"action": signal, "reason": content[:200], "confidence": confidence, "model": "raw"}
        except Exception as exc:
            return {"action": signal, "reason": f"LLM unavailable: {exc}", "confidence": confidence, "model": "none"}

    async def _fetch_data(self, symbol: str, data: Any = None, timeframe: str = "D1") -> Any:
        if data is not None:
            return data
        import asyncio

        import pandas as pd
        dm = self._ensure_data_manager()
        if dm is not None:
            try:
                from quant_nanggroe.types.market import TimeFrame
                # Map timeframe string to TimeFrame enum
                _tf_str_map = {"M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
                               "H1": "H1", "H4": "H4", "D1": "D1"}
                _tf_name = _tf_str_map.get(timeframe.upper(), "D1")
                _tf_enum = getattr(TimeFrame, _tf_name, TimeFrame.D1)
                ohlcv_list = await dm.get_ohlcv(symbol, timeframe=_tf_enum, limit=500)
                if ohlcv_list and len(ohlcv_list) >= 50:
                    rows = [{"open": float(c.open), "high": float(c.high), "low": float(c.low), "close": float(c.close), "volume": float(c.volume)} for c in ohlcv_list]
                    df = pd.DataFrame(rows, index=pd.DatetimeIndex([c.timestamp for c in ohlcv_list]))
                    if self._data_monitor is not None:
                        try:
                            self._data_monitor.record_fetch(symbol, _tf_enum)
                        except Exception:
                            pass
                    return self._reject_stale(self._validate_ohlcv(df, symbol), symbol, timeframe)
            except Exception as exc:
                logger.warning("DataProviderManager failed (%s) — falling back to MT5", exc)

        # ── PRIMARY: fetch from connected MT5 broker (real data, real suffixes) ──
        try:
            if self._em is not None:
                for b in self._em._brokers.values():
                    if hasattr(b, "_mt5") and b._mt5 and b._mt5.connected:
                        resolved = b._mt5.resolve_symbol(symbol)
                        # Map timeframe string to MT5 enum
                        _tf_map = {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
                                   "H1": 16385, "H4": 16388, "D1": 16408}
                        _tf_enum = _tf_map.get(timeframe.upper(), 16408)
                        raw = b._mt5.get_rates(resolved, _tf_enum, 500)
                        if raw is not None and len(raw) >= 50:
                            # R1 hotfix (2026-08-25): get_rates returns numpy
                            # structured records (np.void), not plain tuples.
                            # pd.DataFrame(raw, columns=[...]) on those raised
                            # "Shape of passed values is (500, 1), indices
                            # imply (500, 8)" → every live fetch failed → zero
                            # signals. Build from dtype field names instead.
                            import numpy as _np
                            recs = _np.asarray(raw)
                            if recs.dtype.names:
                                cols = {name: recs[name] for name in recs.dtype.names}
                                df = pd.DataFrame(cols)
                                if "volume" not in df.columns and "tick_volume" in df.columns:
                                    df["volume"] = df["tick_volume"]
                            else:
                                base = ["time", "open", "high", "low", "close", "volume"]
                                width = len(recs[0]) if hasattr(recs[0], "__len__") else len(base)
                                columns = base + [f"_extra_{i}" for i in range(max(0, width - len(base)))] if width > len(base) else base[:width]
                                df = pd.DataFrame([tuple(r) for r in recs], columns=columns)
                            df["time"] = pd.to_datetime(df["time"], unit="s")
                            df.set_index("time", inplace=True)
                            df = df[["open", "high", "low", "close", "volume"]].astype(float)
                            logger.info("MT5 data fetch: %s → %d bars (real broker data)", symbol, len(df))
                            return self._reject_stale(self._validate_ohlcv(df, symbol), symbol, timeframe)
        except Exception as exc:
            logger.warning("MT5 data fetch failed for %s: %s", symbol, exc)

        # ── FALLBACK: yfinance (RESEARCH/BACKTEST ONLY) ──────────────────
        # REAL-ONLY mandate: never generate live-trading signals from
        # indicative Yahoo prices and execute them on MT5 spread prices.
        # Live mode always has an EM with a connected MT5 broker (builder
        # raises RuntimeError otherwise) — reaching this branch WITH an EM
        # means MT5 data failed → FAIL CLOSED, no signal this cycle.
        if self._em is not None:
            logger.error(
                "MT5 data unavailable for %s — FAIL-CLOSED live path "
                "(yfinance forbidden for live trading signals)", symbol,
            )
            return None
        import yfinance as yf
        sym_map = {"BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD",
                    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X"}
        bare = symbol.split(".")[0] if "." in symbol else symbol
        yf_sym = sym_map.get(bare, bare)
        for attempt in range(3):
            try:
                ticker = yf.Ticker(yf_sym)
                df = ticker.history(period="6mo")
                if len(df) >= 50:
                    break
                await asyncio.sleep(5 * (attempt + 1))
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    raise
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        if len(df) < 50:
            return None
        if self._data_monitor is not None:
            try:
                from quant_nanggroe.types.market import TimeFrame as _TF
                self._data_monitor.record_fetch(symbol, _TF.D1)
            except Exception:
                pass
        return self._reject_stale(self._validate_ohlcv(df, symbol), symbol, timeframe)

    def _validate_ohlcv(self, df: Any, symbol: str) -> Any:
        if df is None or df.empty:
            return None
        initial_len = len(df)
        issues: list[str] = []
        import pandas as pd
        if len(df) >= 2:
            idx = df.index
            diffs = pd.Series(idx[1:]) - pd.Series(idx[:-1])
            median_interval = diffs.median()
            if pd.notna(median_interval) and median_interval.total_seconds() > 0:
                gap_threshold = median_interval * 2
                gaps = diffs[diffs > gap_threshold]
                if len(gaps) > 0:
                    issues.append(f"{len(gaps)} index gap(s)")
        if "close" in df.columns:
            bad_close = df["close"].isna() | ~np.isfinite(df["close"])
            nan_count = int(bad_close.sum())
            if nan_count > 0:
                issues.append(f"{nan_count} NaN/inf close")
                df = df[~bad_close]
            non_pos = df["close"] <= 0
            if int(non_pos.sum()) > 0:
                issues.append(f"{int(non_pos.sum())} close<=0")
                df = df[~non_pos]
        mask = pd.Series(True, index=df.index)
        if "high" in df.columns and "low" in df.columns:
            inv = df["high"] < df["low"]
            if int(inv.sum()) > 0:
                issues.append(f"{int(inv.sum())} high<low")
                mask = mask & ~inv
        if "open" in df.columns:
            neg = df["open"] < 0
            if int(neg.sum()) > 0:
                issues.append(f"{int(neg.sum())} open<0")
                mask = mask & ~neg
        df = df[mask]
        removed = initial_len - len(df)
        if issues:
            logger.warning("[%s] OHLCV validation: %d/%d removed — %s", symbol, removed, initial_len, "; ".join(issues))
        if len(df) < 50:
            return None
        return df

    # Bar older than 4× its interval is considered stale → FAIL-CLOSED.
    # 4× keeps weekend gaps (FX closed Fri→Mon ≈ 2 days) inside the D1 budget
    # while catching frozen feeds / corrupted rates within one session.
    STALE_BAR_MULTIPLIER: int = 4
    _TF_INTERVAL_MINUTES: dict = {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
                                  "H1": 60, "H4": 240, "D1": 1440}

    def _reject_stale(self, df: Any, symbol: str, timeframe: str) -> Any:
        """FINDING #11 fix: consume data freshness as a VETO, not a metric.

        A frozen MT5 feed (terminal claims connected, rates never update)
        previously sailed straight into signal generation. Now the newest
        bar's age is checked against 4× the timeframe interval; older data
        returns None → no signal this cycle.
        """
        if df is None or df.empty or len(df.index) == 0:
            return None
        try:
            import pandas as pd
            interval_min = self._TF_INTERVAL_MINUTES.get(
                (timeframe or "D1").upper(), 1440)
            max_age = pd.Timedelta(
                minutes=interval_min * self.STALE_BAR_MULTIPLIER)
            last_bar = df.index[-1]
            # TZ-SAFE comparison (2026-08-25 hotfix): MT5 epochs become naive
            # UTC timestamps; comparing them against naive LOCAL time inflated
            # every age by the UTC offset (WIB +7h) -> M15/H1 permanently
            # "stale" -> zero signals. Treat naive index as UTC explicitly.
            if getattr(last_bar, "tzinfo", None) is not None:
                last_bar_utc = last_bar.tz_convert("UTC")
            else:
                last_bar_utc = last_bar.tz_localize("UTC")
            age = pd.Timestamp.now(tz="UTC") - last_bar_utc
            if age > max_age:
                logger.error(
                    "STALE DATA VETO %s %s: last bar %s (age %.1f min) "
                    "exceeds %.0f min limit — FAIL-CLOSED, no signal",
                    symbol, timeframe, last_bar,
                    age.total_seconds() / 60.0, max_age.total_seconds() / 60.0,
                )
                return None
        except Exception as exc:
            # Malformed index → cannot prove freshness → FAIL CLOSED
            logger.error(
                "Staleness check failed for %s (%s) — FAIL-CLOSED",
                symbol, exc,
            )
            return None
        return df

    def _feed_price_to_paper(self, symbol: str, price: float) -> None:
        if price <= 0:
            return
        try:
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
            logger.debug("Paper price feed skipped: %s", exc)

    async def _make_decision(self, symbol: str, signal: str, confidence: float, current_price: float = 0.0, regime: str = "unknown", decision: dict | None = None, df: Any = None, atr_value: float = 0.0, timeframe: str = "H1", risk_lot_size: float = 0.0, reduce_only: bool = False) -> dict[str, Any]:
        try:
            from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderStatus, OrderType
            em = self._em
            side = OrderSide.BUY if signal == "buy" else (OrderSide.SELL if signal == "sell" else None)
            if side is None:
                return {"symbol": symbol, "action": signal, "confidence": round(confidence, 4), "position_size_pct": 0, "execution": "hold", "note": "signal=hold, no order"}
            # FIX: use risk-computed lot size if available, else ATR-based fallback
            if risk_lot_size > 0:
                qty = risk_lot_size
            else:
                # ATR-based fallback: risk 0.5% of equity, SL = 1.5 * ATR
                try:
                    _atr = self._compute_atr(df) if df is not None else 0.0
                    _equity = em._risk_manager.state.current_equity if em and hasattr(em, '_risk_manager') else 1000
                    _risk_amount = _equity * 0.005
                    if _atr > 0 and current_price > 0:
                        # Approximate pip value: 1 lot = 100000 units, 1 pip = 0.0001 for forex
                        _pip_value = 10.0  # $10 per pip for 1 lot standard forex
                        _sl_pips = (_atr * 1.5) / 0.0001 if current_price < 100 else (_atr * 1.5) / 0.01
                        qty = max(0.01, min(1.0, round(_risk_amount / (_sl_pips * _pip_value), 2)))
                    else:
                        qty = 0.01
                except Exception:
                    qty = 0.01
            if current_price > 0:
                for broker in em._brokers.values():
                    if hasattr(broker, 'set_price'):
                        broker.set_price(symbol, current_price)
            # Get SL/TP from current pipeline result's FinalDecider decision
            # Falls back to previous run or static 5%
            cur_decision = (decision or {}).get('final_decider', {})
            if cur_decision and cur_decision.get('sl', 0) > 0:
                order_sl = cur_decision['sl']
                order_tp = cur_decision['tp']
            else:
                # Fallback: try previous pipeline run's FinalDecider
                prev = getattr(self, '_last_result', None)
                prev_fd = prev.decision.get('final_decider', {}) if prev else {}
                if prev_fd and prev_fd.get('sl', 0) > 0:
                    order_sl = prev_fd['sl']
                    order_tp = prev_fd['tp']
                else:
                    # GATE: ATR + timeframe-profile adaptive SL/TP (replaces
                    # hardcoded 5% which was too wide for forex, too tight
                    # for swing BTC). Falls back to 2% if ATR unavailable.
                    try:
                        from quant_nanggroe.engine.risk.trading_profile import compute_sl_tp
                        _atr = atr_value if atr_value and atr_value > 0 else None
                        if (_atr is None or _atr <= 0) and df is not None:
                            # derive rough ATR from recent bars
                            try:
                                import pandas as _pd
                                h, l, c = df["high"], df["low"], df["close"]
                                pc = c.shift(1)
                                tr = _pd.concat([(h-l), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
                                _atr = float(tr.rolling(14).mean().iloc[-1])
                            except Exception:
                                _atr = current_price * 0.01
                        if _atr is None or _atr <= 0:
                            _atr = current_price * 0.01
                        sltp = compute_sl_tp(
                            side=signal, entry_price=current_price,
                            atr_value=_atr, timeframe=timeframe)
                        order_sl = sltp["sl"]
                        order_tp = sltp["tp"]
                        logger.info("Profile SL/TP %s %s @%.5f -> SL=%.5f TP=%.5f (%s)",
                                    signal, symbol, current_price,
                                    order_sl, order_tp, sltp["profile"])
                    except Exception as sltp_exc:
                        logger.warning("Profile SL/TP failed, using fixed 2%%: %s", sltp_exc)
                        order_sl = current_price * (0.98 if signal == "buy" else 1.02)
                        order_tp = current_price * (1.04 if signal == "buy" else 0.96)
            order = Order(
                id=str(uuid.uuid4()), symbol=symbol, side=side,
                order_type=OrderType.MARKET, quantity=qty,
                status=OrderStatus.PENDING,
                stop_loss=order_sl, take_profit=order_tp,
                metadata={"confidence": confidence,
                          "strategy_name": (decision or {}).get("strategy_name", "ensemble"),
                          "symbol": symbol,
                          "reduce_only": reduce_only},
            )
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
                logger.warning("Execution REJECTED for %s %s: %s", symbol, signal, reason)
            else:
                executed = True
                logger.info("Execution FILLED for %s %s: order=%s price=%.5f", symbol, signal, getattr(fill, 'order_id', '?'), getattr(fill, 'price', 0))
            # Wire trailing stop for filled positions
            if executed and fill and self._trailing_stop is not None:
                try:
                    self._trailing_stop.add_position(symbol, fill.price or current_price, side=side)
                    logger.info("TrailingStop: position added for %s @ %.2f", symbol, fill.price or current_price)
                except Exception as exc:
                    logger.warning("TrailingStop add_position failed: %s", exc)

            try:
                from quant_nanggroe.engine.state_writer import write_engine_snapshot as _write_snap
                if executed and fill:
                    _write_snap(engine_state={"total_value": 1648.48, "cash_balance": 0, "positions_count": 1, "daily_pnl": 0, "weekly_pnl": 0, "drawdown": 0, "regime": "ranging"}, risk_state={"kill_switch_active": False}, positions=[{"symbol": symbol, "side": signal, "qty": qty, "entry_price": fill.price if fill.price else 0, "timestamp": datetime.now(timezone.utc).isoformat()}])
            except Exception:
                pass

            # PnL is 0 at entry time - real PnL computed at position close via TradeLifecycleManager
            # Use fill price for entry tracking; exit_price/pnl populated on close
            return {
                "symbol": symbol, "action": signal, "confidence": round(confidence, 4),
                "position_size_pct": round(confidence * 0.05, 4),
                "execution": "filled" if executed else "rejected",
                "reason": reason, "order_id": fill.order_id if fill else None,
                "fill_price": fill.price if fill else None,
                "pnl": 0.0, "exit_price": 0.0, "exit_time": "",
                "trailing_stop_active": executed and self._trailing_stop is not None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            self.correction.record("execution", f"Order failed {symbol}", str(exc), LessonSeverity.ERROR)
            return {"symbol": symbol, "action": signal, "confidence": round(confidence, 4), "position_size_pct": 0, "error": str(exc)}

    # ── Auto-Evolve: triggered by TradeLifecycleManager when recommendation == 'evolve' ──
    def _trigger_evolution(self, strategy_name: str | None = None) -> dict[str, Any]:
        """Auto-trigger evolution for an underperforming strategy.

        Called by TradeLifecycleManager.process_closed_trade() when the
        PnLEvaluator recommendation is 'evolve'. No manual POST needed.

        Args:
            strategy_name: Specific strategy to evolve, or all if None.

        Returns:
            Dict with evolution results.
        """
        result: dict[str, Any] = {
            "strategies_evaluated": 0,
            "evolutions_triggered": 0,
            "lessons_reviewed": 0,
            "strategies_to_evolve": [],
        }

        # 1. Scan PnLEvaluator for underperforming strategies
        if self._pnl_evaluator is not None:
            try:
                all_stats = self._pnl_evaluator.get_all_strategy_stats()
                for sname, stats in all_stats.items():
                    if strategy_name and sname != strategy_name:
                        continue
                    result["strategies_evaluated"] += 1
                    needs_evolve = (
                        stats.get("win_rate", 1.0) < 0.4 and stats.get("total_pnl", 0) < 0
                    )
                    if needs_evolve:
                        result["strategies_to_evolve"].append({
                            "strategy": sname,
                            "win_rate": stats.get("win_rate", 0),
                            "total_pnl": stats.get("total_pnl", 0),
                            "sharpe": stats.get("sharpe", 0),
                        })
                        result["evolutions_triggered"] += 1

                        # 1b. Auto-Mutate via StrategyEvolver (self-evolve validation gate)
                        if self._strategy_evolver is not None:
                            try:
                                # Load current params from strategy gene if available
                                cur_params = {}
                                if self._gene_loader is not None:
                                    gene = self._gene_loader.get_gene(sname.lower())
                                    if gene and hasattr(gene, "PARAMS"):
                                        cur_params = dict(gene.PARAMS)
                                # Generate mutated params (jitter on numeric values)
                                mut_params = dict(cur_params)
                                import random
                                rng = random.Random(f"{sname}_{time.time()}")
                                for k, v in mut_params.items():
                                    if isinstance(v, (int, float)):
                                        jitter = rng.uniform(0.7, 1.3)  # ±30%
                                        mut_params[k] = v * jitter
                                # Run validation gate
                                attempt = self._strategy_evolver.evaluate(
                                    sname, cur_params, mut_params,
                                )
                                if attempt.accepted:
                                    logger.info(
                                        "Evolution ACCEPTED for %s: %s",
                                        sname, attempt.reason,
                                    )
                                    # 1c. Self-Fine-Tune: optimize further after accepted mutation
                                    if getattr(self, "_self_finetuner", None) is not None:
                                        try:
                                            ft_result = self._self_finetuner.optimize(
                                                sname, mut_params,
                                            )
                                            if ft_result.accepted:
                                                logger.info(
                                                    "Fine-Tune ACCEPTED for %s: %s",
                                                    sname, ft_result.reason,
                                                )
                                                result["finetune_accepted"] = result.get("finetune_accepted", 0) + 1
                                            else:
                                                logger.info(
                                                    "Fine-Tune REJECTED for %s: %s",
                                                    sname, ft_result.reason,
                                                )
                                        except Exception as ft_exc:
                                            logger.warning("Fine-tune failed for %s: %s", sname, ft_exc)
                                else:
                                    logger.info(
                                        "Evolution REJECTED for %s: %s",
                                        sname, attempt.reason,
                                    )
                                result["evolve_validated"] = result.get("evolve_validated", 0) + 1
                            except Exception as exc:
                                logger.warning("Auto-evolve mutation failed for %s: %s", sname, exc)
            except Exception as exc:
                logger.warning("Auto-evolve PnL scan failed: %s", exc)

        # 2. Resolve relevant unresolved lessons
        try:
            lessons = self.correction.list_lessons(unresolved_only=True, limit=100)
            for lesson in lessons:
                if strategy_name and strategy_name not in str(lesson.get("context", {})):
                    continue
                result["lessons_reviewed"] += 1
                if lesson.get("severity") in ("error", "critical"):
                    self.correction.resolve(
                        lesson["id"],
                        "Auto-resolved via _trigger_evolution (recommendation==evolve)",
                    )
        except Exception as exc:
            logger.warning("Auto-evolve lesson review failed: %s", exc)

        logger.info(
            "Auto-evolve complete: %d evaluated, %d triggered, %d lessons reviewed",
            result["strategies_evaluated"],
            result["evolutions_triggered"],
            result["lessons_reviewed"],
        )
        return result

    def _discover_tradable_symbols(self) -> list[str]:
        """Discover tradable FX/commodity symbols from the connected MT5 terminal.

        Scans the broker's real symbol catalog and returns internal-format
        names for every enabled FX pair + commodity. Falls back to hardcoded
        defaults only when MT5 is unavailable.
        """
        # Internal names we want to trade (base names, no suffix)
        # NOTE: XAUUSD/XAGUSD are NOT available on ValetaxIntl-Live2 cent account
        WANTED = {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD",
                  "USDCHF", "EURGBP"}
        try:
            if self._em is None:
                raise RuntimeError("no execution manager")
            for b in self._em._brokers.values():
                if hasattr(b, "_mt5") and b._mt5 and b._mt5.connected:
                    raw = b._mt5._mt5.symbols_get() or []
                    found = []
                    for s in raw:
                        # ONLY include tradeable symbols (trade_mode=0).
                        # Disabled symbols (.vxc) must be excluded.
                        if s.trade_mode != 0:
                            continue
                        base = s.name.split(".")[0] if "." in s.name else s.name
                        if base.upper() in WANTED:
                            found.append(base)
                    if found:
                        logger.info("MT5 symbol discovery: %d tradeable symbols: %s",
                                    len(found), found)
                        return found
                    # If no wanted symbols found with suffix, try bare
                    found_bare = [s.name for s in raw
                                  if s.name.upper() in WANTED]
                    if found_bare:
                        return found_bare
        except Exception as exc:
            logger.debug("MT5 symbol discovery failed: %s", exc)
        # Fallback — use bare names that are actually tradeable on this broker
        fallback = ["EURUSD", "GBPUSD", "USDJPY"]
        logger.info("Using fallback symbols: %s", fallback)
        return fallback

    async def run_batch(self, symbols: list[str] | None = None, strategy_name: str | None = None, use_llm: bool = False) -> list[PipelineResult]:
        """Run pipeline for all symbols, then trigger self-evolution loop.

        Closed loop: trade → evaluate → evolve → validate → redeploy.
        After each batch, underperforming strategies are mutated via
        StrategyEvolver, validated by AutomatedBacktestRunner walk-forward,
        and results stored in WalkForwardRegistry for next-batch filtering.
        """
        if symbols is None:
            symbols = self._discover_tradable_symbols()
        results = []
        for sym in symbols:
            try:
                res = await self.run(sym, strategy_name, use_llm)
                results.append(res)
            except Exception as exc:
                results.append(PipelineResult(symbol=sym, success=False, reason=str(exc)))
                self.correction.record("pipeline_batch", f"Pipeline failed for {sym}", str(exc), LessonSeverity.ERROR)

        # ── Journal sync: pull real MT5 deals into journal ──────────
        # FAZE 0 (replan): closes the feedback loop — self-evaluate and
        # self-evolve need REAL MT5 PnL data, not stale/missing journal.
        try:
            from quant_nanggroe.engine.journal_sync import sync_mt5_deals
            sync_result = sync_mt5_deals()
            if sync_result.get("inserted", 0) or sync_result.get("updated", 0):
                logger.info(
                    "Journal sync: +%d new, ~%d updated, session PnL=%.2f, "
                    "journal total=%d trades net=%.2f",
                    sync_result["inserted"], sync_result["updated"],
                    sync_result["total_pnl"],
                    sync_result.get("journal_total_trades", 0),
                    sync_result.get("journal_net_pnl", 0),
                )
        except Exception as exc:
            logger.warning("Journal sync failed (non-blocking): %s", exc)

        # ── COT Position Guard: close positions conflicting with smart money ──
        # FAZE 0+ (user mandate): on Monday (or whenever fresh COT data is
        # available), check open positions against latest COT positioning.
        # Close only if CONFLICTING + LOSING. Winning conflicts get a warning.
        try:
            from quant_nanggroe.engine.risk.cot_position_guard import (
                scan_and_close_conflicts,
            )
            cot_closed = scan_and_close_conflicts(self._em)
            if cot_closed:
                # F12 fix: `result` is undefined in run_batch scope — the
                # assignment raised NameError and the DEBUG swallow hid every
                # COT close from operators. Log at WARNING directly.
                logger.warning(
                    "COT GUARD: closed %d position(s) conflicting with COT: %s",
                    len(cot_closed),
                    [(c["symbol"], c["side"], f"${c['pnl']:.2f}") for c in cot_closed],
                )
        except Exception as exc:
            logger.debug("COT guard skipped: %s", exc)

        # ── Scorecard: real per-strategy metrics from synced journal ──
        # FAZE 2 (replan): compute REAL expectancy/PF/Sharpe per strategy,
        # transition lifecycle states based on verdicts.
        try:
            from quant_nanggroe.engine.analytics.strategy_scorecard import (
                compute_all_strategies,
            )
            from quant_nanggroe.engine.strategy_lifecycle import StrategyStatus
            scores = compute_all_strategies()
            # F12 fix: same undefined-`result` bug as cot_closes — count via log.
            logger.info("Scorecard: %d strategies scored",
                        len(scores.get("strategies", {})))
            if self._lifecycle:
                for sname, card in scores.get("strategies", {}).items():
                    if sname not in self._lifecycle.strategies:
                        continue
                    verdict = card["verdict"]
                    n = card["n_trades"]
                    exp = card["expectancy"]
                    if verdict == "NEGATIVE_EDGE" and n >= 20:
                        self._lifecycle._transition(
                            sname, StrategyStatus.KILLED,
                            f"Scorecard auto-kill: expectancy={exp}, n={n}")
                        logger.warning("SCORECARD KILL: %s (exp=%.2f, n=%d)",
                                       sname, exp, n)
                    elif verdict in ("PROVEN_GOOD", "MARGINAL_POSITIVE"):
                        if self._lifecycle.strategies[sname].state != StrategyStatus.ACTIVE:
                            self._lifecycle._transition(
                                sname, StrategyStatus.ACTIVE,
                                "Scorecard: positive edge")
                            logger.info("SCORECARD ACTIVATE: %s", sname)
        except Exception as exc:
            logger.debug("Scorecard evolution skipped: %s", exc)

        # ── Self-evolution loop (post-batch) ─────────────────────────
        try:
            self._post_batch_evolution()
        except Exception as exc:
            logger.warning("Post-batch evolution failed: %s", exc)

        # ── Strategy Evaluator Review ──────────────────────────────
        try:
            from quant_nanggroe.engine.agentic.strategy_evaluator import StrategyEvaluator
            evaluator = StrategyEvaluator()
            report = evaluator.review_all()
            disabled = [s for s in report if not s["enabled"]]
            if disabled:
                logger.warning("EVALUATOR: %d strategies auto-disabled: %s",
                               len(disabled),
                               [(s["strategy"], s["disable_reason"]) for s in disabled])
            else:
                logger.info("Evaluator: all %d tracked strategies enabled", len(report))
        except Exception as eval_exc:
            logger.debug("Evaluator review skipped: %s", eval_exc)

        return results

    # ── Self-Evolution Loop ─────────────────────────────────────────────

    def _post_batch_evolution(self) -> dict[str, Any]:
        """Closed-loop self-evolution after each batch run.

        Steps:
          1. PnLEvaluator scores recent trades per strategy.
          2. StrategyEvolver mutates underperformers (±30% jitter).
          3. AutomatedBacktestRunner validates mutations via walk-forward.
          4. WalkForwardRegistry updated — next batch auto-filters losers.

        Returns:
            Dict summarising the evolution cycle.
        """
        result: dict[str, Any] = {
            "strategies_scored": 0,
            "mutations_generated": 0,
            "mutations_validated": 0,
            "wf_records": 0,
        }

        # 1. Score recent trades via PnLEvaluator
        underperformers: list[dict[str, Any]] = []
        if self._pnl_evaluator is not None:
            try:
                all_stats = self._pnl_evaluator.get_all_strategy_stats()
                for sname, stats in all_stats.items():
                    result["strategies_scored"] += 1
                    win_rate = stats.get("win_rate", 1.0)
                    total_pnl = stats.get("total_pnl", 0)
                    if win_rate < 0.4 and total_pnl < 0:
                        underperformers.append({

                            "name": sname,
                            "win_rate": win_rate,
                            "total_pnl": total_pnl,
                            "sharpe": stats.get("sharpe", 0),
                        })
            except Exception as exc:
                logger.warning("Post-batch PnL scoring failed: %s", exc)

        if not underperformers:
            logger.debug("Post-batch: no underperformers, skipping evolution")
            return result

        # 2. Mutate underperformers via StrategyEvolver
        mutations: list[dict[str, Any]] = []
        if self._strategy_evolver is not None:
            import random
            for up in underperformers:
                sname = up["name"]
                try:
                    cur_params: dict[str, Any] = {}
                    if self._gene_loader is not None:
                        gene = self._gene_loader.get_gene(sname.lower())
                        if gene and hasattr(gene, "PARAMS"):
                            cur_params = dict(gene.PARAMS)
                    rng = random.Random(f"{sname}_{time.time()}")
                    mut_params = dict(cur_params)
                    for k, v in mut_params.items():
                        if isinstance(v, (int, float)):
                            mut_params[k] = v * rng.uniform(0.7, 1.3)
                    attempt = self._strategy_evolver.evaluate(sname, cur_params, mut_params)
                    if attempt.accepted:
                        mutations.append({"name": sname, "params": mut_params, "reason": attempt.reason})
                        result["mutations_generated"] += 1
                        logger.info("Post-batch mutation ACCEPTED: %s — %s", sname, attempt.reason)
                    else:
                        logger.debug("Post-batch mutation REJECTED: %s — %s", sname, attempt.reason)
                except Exception as exc:
                    logger.warning("Post-batch mutation failed for %s: %s", sname, exc)

        # 3. Validate mutations via AutomatedBacktestRunner walk-forward
        if mutations:
            try:
                from quant_nanggroe.engine_production_bridge import AutomatedBacktestRunner
                bt_runner = AutomatedBacktestRunner()
                wf_reg = bt_runner.wf_registry
                if wf_reg is not None:
                    # Build strategy instances with mutated params for real walk-forward
                    from quant_nanggroe.engine.strategies.registry import StrategyRegistry
                    mutated_strategies: dict[str, Any] = {}
                    for mut in mutations:
                        sname = mut["name"]
                        strat = StrategyRegistry.create(sname)
                        if strat is not None:
                            # Apply mutated params if strategy supports it
                            try:
                                if hasattr(strat, "parameters") and hasattr(strat.parameters, "update"):
                                    strat.parameters.update(mut["params"])
                            except Exception:
                                pass
                            mutated_strategies[sname] = strat
                        try:
                            wf_reg.register(sname)
                        except Exception:
                            pass  # already registered

                    # Run real walk-forward backtest if we have strategies and candles
                    if mutated_strategies and bt_runner._engine is not None:
                        try:
                            # Fetch candles for walk-forward from data provider
                            # Use actual batch symbols, not hardcoded ones
                            _batch_syms = list(self._discover_tradable_symbols())[:4] or ["EURUSD", "GBPUSD", "USDJPY", "USDCAD"]
                            candles: dict[str, list] = {}
                            for sym in _batch_syms:
                                try:
                                    import yfinance as yf
                                    yf_sym = sym if "-" not in sym else sym.replace("-", "")
                                    ticker = yf.Ticker(yf_sym)
                                    hist = ticker.history(period="6mo")
                                    if hist is not None and len(hist) >= 200:
                                        hist.columns = [c.lower() for c in hist.columns]
                                        candles[sym] = hist.to_dict("records")
                                except Exception:
                                    continue

                            if candles:
                                bt_runner.run(
                                    candles=candles,
                                    cycle=int(time.time()),
                                    force=True,
                                    strategies=mutated_strategies,
                                )
                                result["mutations_validated"] = len(mutated_strategies)
                                result["wf_records"] = len(mutated_strategies)
                                logger.info(
                                    "Post-batch WF: %d strategies validated with real backtest",
                                    len(mutated_strategies),
                                )
                            else:
                                logger.warning("Post-batch WF: no candle data available for backtest")
                        except Exception as bt_exc:
                            logger.warning("Post-batch real backtest failed: %s", bt_exc)
            except Exception as exc:
                logger.warning("Post-batch backtest validation failed: %s", exc)

        logger.info(
            "Post-batch evolution: %d scored, %d mutated, %d validated, %d WF records",
            result["strategies_scored"],
            result["mutations_generated"],
            result["mutations_validated"],
            result["wf_records"],
        )

        # 4. Auto-tune top-performing strategies (if no mutations were accepted)
        if result["mutations_generated"] == 0 and self._pnl_evaluator is not None:
            try:
                result["auto_tuned"] = self._auto_tune_top_strategies()
            except Exception as exc:
                logger.warning("Post-batch auto-tune failed: %s", exc)

        return result

    def _auto_tune_top_strategies(self) -> int:
        """Auto-tune top-performing strategies using walk-forward grid search.

        Runs after evolution if no mutations were accepted. Finds the best
        parameters for strategies with positive PnL but suboptimal Sharpe.

        Returns:
            Number of strategies tuned.
        """
        if self._pnl_evaluator is None:
            return 0

        try:
            import pandas as pd
            import yfinance as yf

            from quant_nanggroe.engine.backtest.auto_tune import AutoTuner, ParameterGrid
            from quant_nanggroe.engine.strategies import create_strategy

            all_stats = self._pnl_evaluator.get_all_strategy_stats()
            if not all_stats:
                return 0

            # Find strategies with positive PnL but low Sharpe (< 1.0)
            candidates = []
            for sname, stats in all_stats.items():
                sharpe = stats.get("sharpe", 0.0)
                total_pnl = stats.get("total_pnl", 0.0)
                if total_pnl > 0 and 0 < sharpe < 1.0:
                    candidates.append((sname, stats))

            if not candidates:
                logger.debug("Auto-tune: no candidates (need positive PnL + Sharpe 0-1)")
                return 0

            # Fetch data once for all candidates — use first tradable symbol
            try:
                _tune_sym = next(iter(self._discover_tradable_symbols()), "EURUSD")
                df = yf.Ticker(_tune_sym).history(period="6mo")
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [c.lower() for c in df.columns]
                if len(df) < 200:
                    return 0
            except Exception:
                return 0

            tuned_count = 0
            for sname, stats in candidates[:3]:  # Tune top 3 candidates
                try:
                    strategy = create_strategy(sname)
                    if strategy is None:
                        continue

                    # Get current params and build a search grid
                    cur_params = {}
                    if hasattr(strategy, "parameters"):
                        cur_params = dict(strategy.parameters) if strategy.parameters else {}

                    # Build param grid: ±20% around current values for numeric params
                    param_grid = {}
                    for k, v in cur_params.items():
                        if isinstance(v, int) and 5 <= v <= 200:
                            param_grid[k] = [max(1, int(v * 0.8)), int(v * 1.2)]
                        elif isinstance(v, float) and 0.01 <= v <= 10.0:
                            param_grid[k] = [round(v * 0.8, 3), round(v * 1.2, 3)]

                    if not param_grid:
                        continue

                    # Run auto-tuning
                    tuner = AutoTuner(
                        strategy_name=sname,
                        param_grid=ParameterGrid(param_grid),
                        data=df,
                        n_windows=3,
                    )
                    results = tuner.tune(top_n=1, verbose=False)

                    if results and results[0].sharpe > stats.get("sharpe", 0.0):
                        logger.info(
                            "Auto-tune: %s improved Sharpe %.3f → %.3f with params %s",
                            sname, stats.get("sharpe", 0.0), results[0].sharpe, results[0].params,
                        )
                        # Apply tuned params if strategy supports it
                        try:
                            if hasattr(strategy, "parameters") and hasattr(strategy.parameters, "update"):
                                strategy.parameters.update(results[0].params)
                        except Exception:
                            pass
                        tuned_count += 1
                except Exception as exc:
                    logger.debug("Auto-tune failed for %s: %s", sname, exc)
                    continue

            if tuned_count > 0:
                logger.info("Auto-tune: %d strategies tuned", tuned_count)
            return tuned_count
        except Exception as exc:
            logger.warning("Auto-tune top strategies failed: %s", exc)
            return 0


# Module-level singleton
_default_pipeline: AutonomousPipeline | None = None


def get_autonomous_pipeline() -> AutonomousPipeline:
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = AutonomousPipeline()
    return _default_pipeline


__all__ = [
    "FREE_PROVIDERS", "register_free_providers",
    "discover_strategies",
    "Lesson", "LessonSeverity", "SelfCorrection",
    "PipelineStep", "PipelineResult", "SlaMetrics", "AutonomousPipeline", "get_autonomous_pipeline",
]
