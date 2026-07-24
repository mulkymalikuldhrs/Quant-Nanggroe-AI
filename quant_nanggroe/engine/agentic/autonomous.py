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
from typing import Any, Callable, Optional

from quant_nanggroe.engine.self_aware import SelfAware, SelfState, Reflection

try:
    from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
    _HAS_STRATEGY_EVOLVER = True
except ImportError:
    StrategyEvolver = None
    _HAS_STRATEGY_EVOLVER = False

import asyncio
import numpy as np

logger = logging.getLogger(__name__)

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

try:
    from quant_nanggroe.engine.analytics.strategy_logger import StrategyLogger
    _HAS_STRATEGY_LOGGER = True
except ImportError:
    StrategyLogger = None
    _HAS_STRATEGY_LOGGER = False

try:
    from quant_nanggroe.engine.analytics.pnl_evaluator import PnLEvaluator
    _HAS_PNL_EVALUATOR = True
except ImportError:
    PnLEvaluator = None
    _HAS_PNL_EVALUATOR = False

try:
    from quant_nanggroe.engine.regime.strategy_filter import RegimeStrategyFilter
    _HAS_REGIME_FILTER = True
except ImportError:
    RegimeStrategyFilter = None
    _HAS_REGIME_FILTER = False

try:
    from quant_nanggroe.engine.strategies.gene_loader import GeneLoader
    _HAS_GENE_LOADER = True
except ImportError:
    GeneLoader = None
    _HAS_GENE_LOADER = False

# ── ClosedTrade for PnLEvaluator ──
ClosedTrade = None
try:
    from quant_nanggroe.engine.analytics.pnl_evaluator import ClosedTrade as _CT
    ClosedTrade = _CT
except ImportError:
    pass

# ── TradeLifecycleManager ──
_TradeLifecycleManager = None
try:
    from quant_nanggroe.engine.agentic.trade_lifecycle import TradeLifecycleManager as _TLM
    _TradeLifecycleManager = _TLM
except ImportError:
    pass

# ── AIHF Override Threshold ──
AIHF_OVERRIDE_THRESHOLD = 0.6

try:
    from quant_nanggroe.agents.aihf_bridge import AIHFBridge, AIHFSignal
    _HAS_AIHF_BRIDGE = True
except ImportError:
    AIHFBridge = None
    AIHFSignal = None
    _HAS_AIHF_BRIDGE = False

try:
    from quant_nanggroe.agents.hedge_fund_bridge import HedgeFundBridge, get_hf_signal
    _HAS_HF_BRIDGE = True
except ImportError:
    HedgeFundBridge = None
    get_hf_signal = None
    _HAS_HF_BRIDGE = False

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
        unresolved_lessons = [l for l in self._lessons if not l.resolved]
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
        self._init_services()

    def _pipeline_self_state(self) -> "SelfState":
        """State provider for the SelfAware module — reflects THIS pipeline's
        real internal state so the organism can reason about itself."""
        from quant_nanggroe.engine.self_aware import SelfState
        rm = getattr(self._risk_manager, "state", None) if hasattr(self, "_risk_manager") else None
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
            extra={"pipeline": "AutonomousPipeline"},
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
                self._final_decider = FinalDecider(min_confidence_threshold=0.60, min_regime_compatibility=0.35, risk_per_trade=0.01, min_rr_ratio=2.5)
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

    async def run(self, symbol: str, strategy_name: str | None = None, use_llm: bool = False, data: Any = None) -> PipelineResult:
        await self._run_lock.acquire()
        try:
            steps: list[PipelineStep] = []
            result = PipelineResult(symbol=symbol, success=False, decision={})

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
                result.decision["regime"] = {"regime": regime, "confidence": regime_confidence, "strategy_type": strategy_type.value}
            except Exception as exc:
                logger.warning("Regime detection failed: %s", exc)

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
                        reason = f"HedgeFund override: {signal_type} @ {confidence:.2f}"

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
                from quant_nanggroe.engine.agentic.council import convene_council, DEBATE_THRESHOLD
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

            # ── Step 3: Risk Check ──────────────────────────────────────
            s3 = PipelineStep(name="risk_check")
            try:
                s3.status = "running"
                t0 = time.perf_counter()
                risk_ok, risk_reason, risk_metrics = self._check_risk(symbol, signal_type, confidence, current_price=current_price)
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

            # ── Step 4.5: Final Decider ─────────────────────────────────
            if self._final_decider is not None and current_price > 0:
                try:
                    from quant_nanggroe.engine.agentic.final_decider import RegimeState, StrategySignal, PortfolioState, RiskState, Action
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
                    risk_state = RiskState(
                        kill_switch_active=getattr(getattr(self._em, '_kill_switch', None), 'status', lambda: {})().get('is_active', False) if self._em else False,
                        daily_loss_pct=0.0, weekly_loss_pct=0.0,
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
                exec_decision = await self._make_decision(symbol, signal_type, confidence, current_price=current_price, regime=regime, decision=result.decision)
                s5.duration_ms = (time.perf_counter() - t0) * 1000
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

                # ── NEW: TradeLifecycleManager — closed trade → eval → evolve ──
                if self._trade_lifecycle is not None and ClosedTrade is not None:
                    try:
                        action = exec_decision.get("action", "hold")
                        if action in ("buy", "sell") and exec_decision.get("execution") == "filled":
                            # Create a ClosedTrade for lifecycle processing
                            trade = ClosedTrade(
                                trade_id=exec_decision.get("order_id", str(uuid.uuid4())[:12]),
                                strategy_name=trigger_strategy,
                                symbol=symbol,
                                entry_price=exec_decision.get("fill_price", current_price),
                                exit_price=exec_decision.get("exit_price", 0.0),
                                volume=exec_decision.get("position_size_pct", 0.01),
                                side=action,
                                entry_time=exec_decision.get("timestamp", result.timestamp),
                                exit_time=exec_decision.get("exit_time", ""),
                                pnl=exec_decision.get("pnl", 0.0),
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
                risk_step = next((s for s in steps if s.name == 'risk_check'), None)
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
            try:
                from quant_nanggroe.engine.strategy.strategies import create_strategy
                strategy = create_strategy(strategy_name)
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
            from quant_nanggroe.engine.strategy.strategies import list_strategies, create_strategy
            all_names = list_strategies()
            if self._lifecycle:
                active = set(self._lifecycle.get_active_strategies())
                if active:
                    all_names = [n for n in all_names if n in active]
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

        signals: list[tuple[str, float, str, str]] = []
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

        self._record_strategy_signals(symbol, df, signals)

        if not signals:
            return "hold", 0.0, "No strategy produced a signal"

        buy_weight = sum(c * weights.get(cat, 1.0) for sig, c, _, cat in signals if sig == "buy")
        sell_weight = sum(c * weights.get(cat, 1.0) for sig, c, _, cat in signals if sig == "sell")
        total_weight = buy_weight + sell_weight

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

    def _check_risk(self, symbol: str, signal: str, confidence: float, current_price: float = 0.0) -> tuple[bool, str, dict]:
        metrics = {"max_drawdown": 0.0, "daily_pnl": 0.0, "price": current_price}
        try:
            em = self._em
            if em._kill_switch:
                ks_status = em._kill_switch.status()
                if ks_status.get("is_active") or ks_status.get("active"):
                    return False, f"Kill switch active", metrics
            if em._risk_manager:
                from quant_nanggroe.engine.risk.constants import MAX_RISK_PER_TRADE
                balance = em._risk_manager.state.current_equity
                stop_loss = current_price * 0.95 if signal == "buy" else (current_price * 1.05 if signal == "sell" else current_price)
                lot_size = max(0.01, round(balance * MAX_RISK_PER_TRADE / current_price, 4)) if current_price > 0 else 0.01
                verdict = em._risk_manager.check_trade(symbol=symbol, direction=signal.upper() if signal != "hold" else "HOLD", lot_size=lot_size, entry=current_price, stop_loss=stop_loss, account_balance=balance)
                if verdict.get("verdict") == "VETOED":
                    return False, f"RiskManager vetoed: {verdict.get('reason','?')}", {**metrics, "risk_verdict": "VETOED", "checkpoints": verdict.get("checkpoints", {})}
                metrics.update({"risk_verdict": "APPROVED", "lot_size": lot_size, "stop_loss": stop_loss, "balance": balance})
        except Exception as exc:
            logger.warning("RiskManager check failed: %s", exc)
        if confidence < 0.15:
            return False, f"Confidence {confidence:.2f} below 0.15 floor", metrics
        if signal == "hold":
            return False, "Signal is HOLD", metrics
        return True, f"Risk passed: {signal} @ {confidence:.1%}", metrics

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

    async def _fetch_data(self, symbol: str, data: Any = None) -> Any:
        if data is not None:
            return data
        import asyncio
        import pandas as pd
        dm = self._ensure_data_manager()
        if dm is not None:
            try:
                from quant_nanggroe.types.market import TimeFrame
                ohlcv_list = await dm.get_ohlcv(symbol, timeframe=TimeFrame.D1, limit=500)
                if ohlcv_list and len(ohlcv_list) >= 50:
                    rows = [{"open": float(c.open), "high": float(c.high), "low": float(c.low), "close": float(c.close), "volume": float(c.volume)} for c in ohlcv_list]
                    df = pd.DataFrame(rows, index=pd.DatetimeIndex([c.timestamp for c in ohlcv_list]))
                    if self._data_monitor is not None:
                        try:
                            from quant_nanggroe.types.market import TimeFrame as _TF
                            self._data_monitor.record_fetch(symbol, _TF.D1)
                        except Exception:
                            pass
                    return self._validate_ohlcv(df, symbol)
            except Exception as exc:
                logger.warning("DataProviderManager failed (%s) — falling back to yfinance", exc)
        import yfinance as yf
        sym_map = {"BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD", "SOL-USD": "SOL-USD", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X"}
        yf_sym = sym_map.get(symbol, symbol)
        for attempt in range(3):
            try:
                ticker = yf.Ticker(yf_sym)
                df = ticker.history(period="6mo")
                if len(df) >= 50:
                    break
                await asyncio.sleep(5 * (attempt + 1))
            except Exception as exc:
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
        return self._validate_ohlcv(df, symbol)

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

    async def _make_decision(self, symbol: str, signal: str, confidence: float, current_price: float = 0.0, regime: str = "unknown", decision: dict | None = None) -> dict[str, Any]:
        try:
            from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType, OrderStatus
            em = self._em
            side = OrderSide.BUY if signal == "buy" else (OrderSide.SELL if signal == "sell" else None)
            if side is None:
                return {"symbol": symbol, "action": signal, "confidence": round(confidence, 4), "position_size_pct": 0, "execution": "hold", "note": "signal=hold, no order"}
            qty = max(0.01, round(confidence * 0.1, 4))
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
                    order_sl = current_price * 0.95 if signal == "buy" else (current_price * 1.05 if signal == "sell" else 0.0)
                    order_tp = current_price * 1.05 if signal == "buy" else (current_price * 0.95 if signal == "sell" else 0.0)
            order = Order(
                id=str(uuid.uuid4()), symbol=symbol, side=side,
                order_type=OrderType.MARKET, quantity=qty,
                status=OrderStatus.PENDING,
                stop_loss=order_sl, take_profit=order_tp,
                metadata={"confidence": confidence},
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
            else:
                executed = True
            # Wire trailing stop for filled positions
            if executed and fill and self._trailing_stop is not None:
                try:
                    self._trailing_stop.add_position(symbol, fill.price or current_price)
                    logger.info("TrailingStop: position added for %s @ %.2f", symbol, fill.price or current_price)
                except Exception as exc:
                    logger.warning("TrailingStop add_position failed: %s", exc)

            try:
                from quant_nanggroe.engine.state_writer import write_engine_snapshot as _write_snap
                if executed and fill:
                    _write_snap(engine_state={"total_value": fill.price * qty if fill.price else 0, "cash_balance": 0, "positions_count": 1, "daily_pnl": 0, "weekly_pnl": 0, "drawdown": 0, "regime": "unknown"}, risk_state={"kill_switch_active": False}, positions=[{"symbol": symbol, "side": signal, "qty": qty, "entry_price": fill.price if fill.price else 0, "timestamp": datetime.now(timezone.utc).isoformat()}])
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

    async def run_batch(self, symbols: list[str] | None = None, strategy_name: str | None = None, use_llm: bool = False) -> list[PipelineResult]:
        if symbols is None:
            symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "EURUSD", "USDJPY"]
        results = []
        for sym in symbols:
            try:
                res = await self.run(sym, strategy_name, use_llm)
                results.append(res)
            except Exception as exc:
                results.append(PipelineResult(symbol=sym, success=False, reason=str(exc)))
                self.correction.record("pipeline_batch", f"Pipeline failed for {sym}", str(exc), LessonSeverity.ERROR)
        return results


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
