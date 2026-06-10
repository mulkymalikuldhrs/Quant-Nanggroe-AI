"""
DSPy Prompt Optimizer for Trading Agents
==========================================
Implements DSPy-based prompt optimization for trading agent signatures.
Uses lazy imports so the module degrades gracefully when ``dspy`` is not
installed — callers can still access the fallback optimiser path.

Architecture:
    - ``TradingSignature``  — dspy.Signature describing the trading task
    - ``BacktestMetric``    — dspy.Metric scoring candidate prompts via backtest
    - ``DSPyOptimizer``     — Main orchestrator that compiles / optimises prompts
    - ``OptimizationResult``— Structured result returned to callers

Graceful degradation:
    If ``dspy`` is not importable, ``DSPyOptimizer.optimize_agent_prompt()``
    returns a :class:`FallbackResult` with the original prompt unchanged and
    a diagnostic message, instead of raising ``ImportError``.

References:
    Khattab, O., et al. (2023). "DSPy: Compiling Declarative Language
    Model Calls into Self-Improving Pipelines." arXiv:2310.03714.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# DSPy AVAILABILITY CHECK
# ══════════════════════════════════════════════════════════════════════

_DSPY_AVAILABLE: bool | None = None


def is_dspy_available() -> bool:
    """Check whether the ``dspy`` package is importable.

    Result is cached after the first call.
    """
    global _DSPY_AVAILABLE
    if _DSPY_AVAILABLE is None:
        try:
            import dspy  # noqa: F401 — side-effect import
            _DSPY_AVAILABLE = True
            logger.info("dspy %s detected", getattr(dspy, "__version__", "unknown"))
        except ImportError:
            _DSPY_AVAILABLE = False
            logger.info("dspy not installed — prompt optimisation will use fallback")
    return _DSPY_AVAILABLE


# ══════════════════════════════════════════════════════════════════════
# PROTOCOLS — typed interfaces independent of dspy
# ══════════════════════════════════════════════════════════════════════


class SignalDirection(str, Enum):
    """Trading signal direction."""

    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@runtime_checkable
class BacktestRunner(Protocol):
    """Protocol for backtest runners used by :class:`BacktestMetric`."""

    def run(
        self,
        signal_direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        context: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """Execute a backtest and return metrics.

        Returns:
            Dict with at least ``sharpe``, ``max_drawdown``, ``win_rate``,
            ``total_return`` keys.
        """
        ...


@dataclass(frozen=True, slots=True)
class AgentPromptCandidate:
    """A candidate prompt for optimisation.

    Attributes:
        system_prompt: The system-level instruction to the trading agent.
        instruction: Additional task-level instruction appended to the
            system prompt.
        metadata: Arbitrary metadata (e.g. generation round, parent hash).
    """

    system_prompt: str
    instruction: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ══════════════════════════════════════════════════════════════════════


class OptimizationStatus(str, Enum):
    """Status of an optimisation run."""

    SUCCESS = "SUCCESS"
    FALLBACK = "FALLBACK"        # dspy not available — returned unchanged
    NO_IMPROVEMENT = "NO_IMPROVEMENT"  # Ran but couldn't beat baseline
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Structured result from :meth:`DSPyOptimizer.optimize_agent_prompt`.

    Attributes:
        status: Outcome of the optimisation.
        best_prompt: The winning prompt candidate.
        baseline_score: Metric score of the original prompt.
        best_score: Metric score of the best prompt found.
        improvement_pct: Percentage improvement over baseline.
            ``0.0`` if no improvement or fallback.
        iterations: Number of optimisation iterations completed.
        candidates_evaluated: Total candidates evaluated.
        elapsed_seconds: Wall-clock time for the optimisation.
        history: List of (candidate, score) tuples for introspection.
        message: Human-readable diagnostic message.
    """

    status: OptimizationStatus
    best_prompt: AgentPromptCandidate
    baseline_score: float
    best_score: float
    improvement_pct: float
    iterations: int
    candidates_evaluated: int
    elapsed_seconds: float
    history: list[tuple[str, float]] = field(default_factory=list)
    message: str = ""


# ══════════════════════════════════════════════════════════════════════
# DSPy SIGNATURE (lazy — only defined when dspy is available)
# ══════════════════════════════════════════════════════════════════════

_TradingSignature: Any = None


def get_trading_signature() -> Any:
    """Return the DSPy ``Signature`` class for trading (lazy creation).

    The signature describes the input/output contract:

        Inputs:
            market_context  — recent market data summary
            regime          — current market regime classification
            technical_data  — technical indicator values
            sentiment       — sentiment score and direction

        Outputs:
            signal_direction — LONG / SHORT / NEUTRAL
            confidence       — 0.0 to 1.0
            rationale        — chain-of-thought reasoning
    """
    global _TradingSignature
    if _TradingSignature is not None:
        return _TradingSignature

    if not is_dspy_available():
        return None

    import dspy

    class TradingSignature(dspy.Signature):  # type: ignore[misc]
        """Analyze market data and produce a trading signal with reasoning."""

        market_context: str = dspy.InputField(
            desc="Summary of recent market conditions, price action, and volume"
        )
        regime: str = dspy.InputField(
            desc="Current market regime: TRENDING_UP, TRENDING_DOWN, RANGE, etc."
        )
        technical_data: str = dspy.InputField(
            desc="Technical indicator values: RSI, MACD, EMA alignment, ATR, etc."
        )
        sentiment: str = dspy.InputField(
            desc="Sentiment analysis: score from -1.0 to 1.0, news events, uncertainty"
        )

        signal_direction: str = dspy.OutputField(
            desc="Trading signal: LONG, SHORT, or NEUTRAL"
        )
        confidence: str = dspy.OutputField(
            desc="Signal confidence from 0.0 to 1.0"
        )
        rationale: str = dspy.OutputField(
            desc="Step-by-step reasoning for the trading signal"
        )

    _TradingSignature = TradingSignature
    return _TradingSignature


# ══════════════════════════════════════════════════════════════════════
# BACKTEST METRIC (lazy — only defined when dspy is available)
# ══════════════════════════════════════════════════════════════════════

_BacktestMetric: Any = None


def get_backtest_metric_class() -> Any:
    """Return the DSPy ``Metric`` class for backtest scoring (lazy).

    Returns ``None`` if dspy is not available.
    """
    global _BacktestMetric
    if _BacktestMetric is not None:
        return _BacktestMetric

    if not is_dspy_available():
        return None

    import dspy

    class BacktestMetric(dspy.Metric):  # type: ignore[misc]
        """Score a candidate prompt by running its signals through a backtest.

        The metric combines Sharpe ratio, win rate, max drawdown, and
        total return into a single composite score:

            score = 0.4 * sharpe + 0.25 * win_rate + 0.15 * total_return
                    - 0.2 * max_drawdown

        All components are normalised to [0, 1] before weighting.
        """

        def __init__(
            self,
            backtest_runner: BacktestRunner | None = None,
            sharpe_weight: float = 0.4,
            win_rate_weight: float = 0.25,
            return_weight: float = 0.15,
            drawdown_weight: float = 0.2,
        ) -> None:
            super().__init__()
            self._runner = backtest_runner
            self._weights = {
                "sharpe": sharpe_weight,
                "win_rate": win_rate_weight,
                "return": return_weight,
                "drawdown": drawdown_weight,
            }

        def __call__(self, example, prediction, trace=None) -> float:  # type: ignore[override]
            """Compute the composite backtest score.

            Args:
                example: DSPy example (ground truth).
                prediction: DSPy prediction from the candidate module.
                trace: Optional trace for debugging.

            Returns:
                Float score in [0, 1]. Returns 0.0 on any error.
            """
            if self._runner is None:
                logger.warning("No backtest runner configured — returning neutral score")
                return 0.5

            try:
                signal_dir = getattr(prediction, "signal_direction", "NEUTRAL")
                confidence = float(getattr(prediction, "confidence", "0.5"))
                confidence = max(0.0, min(1.0, confidence))

                # Default position sizing parameters
                entry = 100.0
                sl = entry * (0.98 if signal_dir == "LONG" else 1.02)
                tp = entry * (1.04 if signal_dir == "LONG" else 0.96)

                results = self._runner.run(
                    signal_direction=signal_dir,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    confidence=confidence,
                )

                # Normalise components
                sharpe = max(min(results.get("sharpe", 0.0) / 3.0, 1.0), 0.0)
                win_rate = max(min(results.get("win_rate", 0.0), 1.0), 0.0)
                total_return = max(min(results.get("total_return", 0.0) / 0.5, 1.0), 0.0)
                max_dd = max(min(results.get("max_drawdown", 0.5), 1.0), 0.0)

                score = (
                    self._weights["sharpe"] * sharpe
                    + self._weights["win_rate"] * win_rate
                    + self._weights["return"] * total_return
                    - self._weights["drawdown"] * max_dd
                )
                return max(0.0, min(1.0, score))

            except Exception as exc:
                logger.warning("BacktestMetric error: %s", exc)
                return 0.0

    _BacktestMetric = BacktestMetric
    return _BacktestMetric


# ══════════════════════════════════════════════════════════════════════
# FALLBACK METRIC (no dspy required)
# ══════════════════════════════════════════════════════════════════════


def _heuristic_score_prompt(candidate: AgentPromptCandidate) -> float:
    """Score a prompt candidate using heuristic rules (no dspy / no LLM).

    This is the fallback scoring method when dspy is not available.
    It applies simple heuristic checks:

    - Longer, more detailed prompts score higher (up to a point)
    - Prompts mentioning risk management, position sizing, stop-loss
      score higher
    - Prompts with clear output format instructions score higher
    - Very short prompts (<50 chars) score lower
    """
    prompt = candidate.system_prompt + " " + candidate.instruction
    score = 0.3  # Base score

    # Length bonus (diminishing returns)
    length = len(prompt)
    if length < 50:
        score -= 0.1
    elif length < 200:
        score += 0.1
    elif length < 1000:
        score += 0.15
    else:
        score += 0.2

    # Risk management keywords
    risk_keywords = [
        "stop loss", "stop-loss", "risk", "drawdown", "position size",
        "capital", "exposure", "leverage", "volatility",
    ]
    prompt_lower = prompt.lower()
    risk_hits = sum(1 for kw in risk_keywords if kw in prompt_lower)
    score += min(risk_hits * 0.04, 0.2)

    # Structure keywords (clear output format)
    structure_keywords = [
        "output", "format", "json", "return", "must", "always", "never",
        "ensure", "validate", "signal", "confidence",
    ]
    structure_hits = sum(1 for kw in structure_keywords if kw in prompt_lower)
    score += min(structure_hits * 0.03, 0.15)

    # Penalty for vague language
    vague_keywords = ["maybe", "perhaps", "might", "could", "sometimes"]
    vague_hits = sum(1 for kw in vague_keywords if kw in prompt_lower)
    score -= min(vague_hits * 0.03, 0.1)

    return max(0.0, min(1.0, score))


# ══════════════════════════════════════════════════════════════════════
# PROMPT MUTATION (used by fallback optimizer)
# ══════════════════════════════════════════════════════════════════════


def _mutate_prompt(
    candidate: AgentPromptCandidate,
    strategy: str = "append_risk",
) -> AgentPromptCandidate:
    """Generate a variant of a prompt candidate.

    Args:
        candidate: The base prompt to mutate.
        strategy: Mutation strategy. Options:
            - ``append_risk``: Append a risk management clause
            - ``append_structure``: Append output format instructions
            - ``append_regime``: Append regime-awareness instruction
            - ``strengthen``: Replace vague language with firm directives

    Returns:
        A new :class:`AgentPromptCandidate` with the mutation applied.
    """
    base = candidate.system_prompt
    instruction = candidate.instruction

    if strategy == "append_risk":
        risk_clause = (
            "\n\nRISK MANAGEMENT REQUIREMENTS:\n"
            "- Always specify stop-loss and take-profit levels\n"
            "- Never risk more than 1% of capital on a single trade\n"
            "- Consider current volatility regime before sizing\n"
            "- If confidence is below 0.4, output NEUTRAL"
        )
        return AgentPromptCandidate(
            system_prompt=base + risk_clause,
            instruction=instruction,
            metadata={**candidate.metadata, "mutation": "append_risk"},
        )

    elif strategy == "append_structure":
        structure_clause = (
            "\n\nOUTPUT FORMAT:\n"
            "- signal_direction: Must be exactly 'LONG', 'SHORT', or 'NEUTRAL'\n"
            "- confidence: Float between 0.0 and 1.0\n"
            "- rationale: Step-by-step reasoning with evidence"
        )
        return AgentPromptCandidate(
            system_prompt=base + structure_clause,
            instruction=instruction,
            metadata={**candidate.metadata, "mutation": "append_structure"},
        )

    elif strategy == "append_regime":
        regime_clause = (
            "\n\nREGIME AWARENESS:\n"
            "- Adapt signal aggressiveness to the market regime\n"
            "- In TRENDING regimes: favour trend-following signals\n"
            "- In RANGE regimes: favour mean-reversion signals\n"
            "- In PANIC/RISK_OFF regimes: default to NEUTRAL\n"
            "- Always consider the regime before generating a signal"
        )
        return AgentPromptCandidate(
            system_prompt=base + regime_clause,
            instruction=instruction,
            metadata={**candidate.metadata, "mutation": "append_regime"},
        )

    elif strategy == "strengthen":
        replacements = {
            "maybe": "must consider",
            "perhaps": "decisively",
            "might want to": "shall",
            "could consider": "must evaluate",
            "sometimes": "when applicable",
        }
        new_prompt = base
        for old, new in replacements.items():
            new_prompt = new_prompt.replace(old, new)
        return AgentPromptCandidate(
            system_prompt=new_prompt,
            instruction=instruction,
            metadata={**candidate.metadata, "mutation": "strengthen"},
        )

    else:
        return candidate


# ══════════════════════════════════════════════════════════════════════
# MAIN OPTIMIZER
# ══════════════════════════════════════════════════════════════════════


class DSPyOptimizer:
    """DSPy-based prompt optimiser for trading agents.

    When dspy is installed, uses DSPy's optimisation pipeline
    (BootstrapFewShot / MIPROv2) to compile and optimise agent prompts
    against a backtest metric.

    When dspy is **not** installed, falls back to a heuristic prompt
    mutation strategy that appends risk/structure/regime clauses and
    scores them with :func:`_heuristic_score_prompt`.

    Args:
        llm_model: DSPy-compatible LLM identifier (e.g. ``"openai/gpt-4o"``).
            Ignored in fallback mode.
        backtest_runner: An object satisfying the :class:`BacktestRunner`
            protocol. Required for meaningful metric scoring.
        max_iterations: Maximum optimisation iterations. Default 5.
        num_candidates: Number of candidate prompts per iteration. Default 4.
        optimiser_type: DSPy optimiser type: ``"bootstrap"`` or ``"mipro"``.
            Ignored in fallback mode.

    Example::

        optimizer = DSPyOptimizer(
            llm_model="openai/gpt-4o",
            backtest_runner=my_runner,
            max_iterations=3,
        )
        result = optimizer.optimize_agent_prompt(
            initial_prompt="You are a trading agent. Analyze the market and give signals.",
        )
        print(result.best_prompt.system_prompt)
        print(f"Improvement: {result.improvement_pct:.1f}%")
    """

    # Mutation strategies for fallback mode
    _MUTATION_STRATEGIES: list[str] = [
        "append_risk",
        "append_structure",
        "append_regime",
        "strengthen",
    ]

    def __init__(
        self,
        llm_model: str = "openai/gpt-4o",
        backtest_runner: BacktestRunner | None = None,
        max_iterations: int = 5,
        num_candidates: int = 4,
        optimiser_type: str = "bootstrap",
    ) -> None:
        self._llm_model = llm_model
        self._backtest_runner = backtest_runner
        self._max_iterations = max(1, max_iterations)
        self._num_candidates = max(1, num_candidates)
        self._optimiser_type = optimiser_type

    def optimize_agent_prompt(
        self,
        initial_prompt: str,
        instruction: str = "",
        train_examples: list[dict[str, Any]] | None = None,
    ) -> OptimizationResult:
        """Optimise a trading agent's prompt.

        Args:
            initial_prompt: The starting system prompt.
            instruction: Additional task-level instruction.
            train_examples: Optional list of training examples for DSPy
                few-shot bootstrapping. Each example should have keys
                matching :class:`TradingSignature` inputs and outputs.

        Returns:
            :class:`OptimizationResult` with the best prompt found and
            associated metrics.
        """
        start_time = time.monotonic()
        initial_candidate = AgentPromptCandidate(
            system_prompt=initial_prompt,
            instruction=instruction,
            metadata={"generation": 0, "origin": "initial"},
        )

        if is_dspy_available():
            result = self._optimize_with_dspy(
                initial_candidate, train_examples or []
            )
        else:
            result = self._optimize_fallback(initial_candidate)

        elapsed = time.monotonic() - start_time

        # Replace elapsed time with actual measurement
        return OptimizationResult(
            status=result.status,
            best_prompt=result.best_prompt,
            baseline_score=result.baseline_score,
            best_score=result.best_score,
            improvement_pct=result.improvement_pct,
            iterations=result.iterations,
            candidates_evaluated=result.candidates_evaluated,
            elapsed_seconds=elapsed,
            history=result.history,
            message=result.message,
        )

    # ── DSPy-based optimisation ───────────────────────────────────────

    def _optimize_with_dspy(
        self,
        initial: AgentPromptCandidate,
        train_examples: list[dict[str, Any]],
    ) -> OptimizationResult:
        """Run full DSPy optimisation pipeline."""
        import dspy

        # Configure LLM
        try:
            lm = dspy.LM(self._llm_model)
            dspy.configure(lm=lm)
        except Exception as exc:
            logger.warning(
                "Failed to configure DSPy LLM (%s), falling back to heuristic: %s",
                self._llm_model, exc,
            )
            return self._optimize_fallback(initial)

        # Get the signature
        TradingSig = get_trading_signature()
        if TradingSig is None:
            return self._optimize_fallback(initial)

        # Build DSPy examples
        examples = []
        for ex in train_examples:
            try:
                examples.append(
                    dspy.Example(
                        market_context=ex.get("market_context", ""),
                        regime=ex.get("regime", "UNKNOWN"),
                        technical_data=ex.get("technical_data", ""),
                        sentiment=ex.get("sentiment", "0.0"),
                        signal_direction=ex.get("signal_direction", "NEUTRAL"),
                        confidence=ex.get("confidence", "0.5"),
                        rationale=ex.get("rationale", ""),
                    ).with_inputs(
                        "market_context", "regime", "technical_data", "sentiment"
                    )
                )
            except Exception as exc:
                logger.debug("Skipping invalid training example: %s", exc)
                continue

        # Create the module
        class TradingModule(dspy.Module):  # type: ignore[misc]
            def __init__(self) -> None:
                super().__init__()
                self.prog = dspy.ChainOfThought(TradingSig)

            def forward(self, **kwargs: Any) -> Any:
                return self.prog(**kwargs)

        # Get metric
        MetricCls = get_backtest_metric_class()
        metric = MetricCls(backtest_runner=self._backtest_runner) if MetricCls else None

        if metric is None or not examples:
            logger.info(
                "No backtest metric or no training examples — using fallback"
            )
            return self._optimize_fallback(initial)

        # Score baseline
        baseline_score = self._score_with_dspy(
            initial, TradingModule, metric, examples
        )

        # Choose optimiser
        try:
            if self._optimiser_type == "mipro":
                optimizer = dspy.MIPROv2(
                    metric=metric,
                    num_threads=1,
                    max_bootstrapped_demos=3,
                    max_labeled_demos=3,
                )
            else:
                optimizer = dspy.BootstrapFewShot(
                    metric=metric,
                    max_bootstrapped_demos=4,
                    max_labeled_demos=4,
                    max_errors=5,
                )
        except Exception as exc:
            logger.warning("Failed to create DSPy optimizer: %s", exc)
            return self._optimize_fallback(initial)

        # Run optimisation
        best_score = baseline_score
        best_candidate = initial
        history: list[tuple[str, float]] = [("initial", baseline_score)]
        candidates_evaluated = 0

        try:
            module = TradingModule()
            compiled = optimizer.compile(
                module,
                trainset=examples,
            )

            # Extract the optimised instruction if available
            compiled_instruction = ""
            if hasattr(compiled, "prog") and hasattr(compiled.prog, "signature"):
                sig = compiled.prog.signature
                if hasattr(sig, "instructions"):
                    compiled_instruction = sig.instructions or ""

            optimised = AgentPromptCandidate(
                system_prompt=initial.system_prompt,
                instruction=compiled_instruction or initial.instruction,
                metadata={"generation": 1, "origin": "dspy_compiled"},
            )

            opt_score = self._score_with_dspy(
                optimised, TradingModule, metric, examples
            )
            candidates_evaluated += 1
            history.append(("dspy_compiled", opt_score))

            if opt_score > best_score:
                best_score = opt_score
                best_candidate = optimised

        except Exception as exc:
            logger.warning("DSPy optimisation failed: %s", exc)
            return OptimizationResult(
                status=OptimizationStatus.ERROR,
                best_prompt=initial,
                baseline_score=baseline_score,
                best_score=baseline_score,
                improvement_pct=0.0,
                iterations=0,
                candidates_evaluated=candidates_evaluated,
                elapsed_seconds=0.0,
                history=history,
                message=f"DSPy optimisation failed: {exc}",
            )

        improvement = (
            ((best_score - baseline_score) / baseline_score * 100)
            if baseline_score > 0 else 0.0
        )
        status = (
            OptimizationStatus.SUCCESS
            if improvement > 0
            else OptimizationStatus.NO_IMPROVEMENT
        )

        return OptimizationResult(
            status=status,
            best_prompt=best_candidate,
            baseline_score=baseline_score,
            best_score=best_score,
            improvement_pct=round(improvement, 2),
            iterations=1,
            candidates_evaluated=candidates_evaluated,
            elapsed_seconds=0.0,  # Will be overridden by caller
            history=history,
            message=(
                f"DSPy optimisation completed. Best score: {best_score:.4f}"
                if status == OptimizationStatus.SUCCESS
                else f"No improvement found. Baseline: {baseline_score:.4f}"
            ),
        )

    @staticmethod
    def _score_with_dspy(
        candidate: AgentPromptCandidate,
        module_cls: type,
        metric: Any,
        examples: list[Any],
    ) -> float:
        """Score a candidate using DSPy's metric on training examples."""
        try:
            module = module_cls()
            total_score = 0.0
            count = 0
            for ex in examples[:10]:  # Cap at 10 examples for speed
                try:
                    pred = module(
                        market_context=ex.market_context,
                        regime=ex.regime,
                        technical_data=ex.technical_data,
                        sentiment=ex.sentiment,
                    )
                    score = metric(ex, pred)
                    total_score += score
                    count += 1
                except Exception:
                    continue
            return total_score / count if count > 0 else 0.0
        except Exception:
            return 0.0

    # ── Fallback (no dspy) optimisation ───────────────────────────────

    def _optimize_fallback(
        self,
        initial: AgentPromptCandidate,
    ) -> OptimizationResult:
        """Heuristic prompt optimisation when dspy is unavailable.

        Strategy:
            1. Score the initial prompt with :func:`_heuristic_score_prompt`
            2. Generate variants using each mutation strategy
            3. Score all variants
            4. Pick the best; repeat with the best as new base
            5. Return the overall best after *max_iterations* rounds
        """
        baseline_score = _heuristic_score_prompt(initial)
        best_score = baseline_score
        best_candidate = initial
        history: list[tuple[str, float]] = [("initial", baseline_score)]
        candidates_evaluated = 0

        current = initial

        for iteration in range(self._max_iterations):
            round_best = current
            round_best_score = _heuristic_score_prompt(current)

            for strategy in self._MUTATION_STRATEGIES:
                variant = _mutate_prompt(current, strategy=strategy)
                score = _heuristic_score_prompt(variant)
                candidates_evaluated += 1
                label = f"iter{iteration}_{strategy}"
                history.append((label, score))

                if score > round_best_score:
                    round_best_score = score
                    round_best = variant

            # If this round found an improvement, carry it forward
            if round_best_score > _heuristic_score_prompt(current):
                current = round_best

            if round_best_score > best_score:
                best_score = round_best_score
                best_candidate = round_best

            logger.debug(
                "Fallback iteration %d: best_score=%.4f, round_best=%.4f",
                iteration, best_score, round_best_score,
            )

        improvement = (
            ((best_score - baseline_score) / baseline_score * 100)
            if baseline_score > 0 else 0.0
        )

        if not is_dspy_available():
            status = OptimizationStatus.FALLBACK
            message = (
                "dspy not installed — used heuristic mutation fallback. "
                f"Evaluated {candidates_evaluated} candidates across "
                f"{self._max_iterations} iterations."
            )
        elif improvement > 0:
            status = OptimizationStatus.SUCCESS
            message = (
                f"Fallback optimisation improved score by {improvement:.1f}%. "
                f"Best strategy: {best_candidate.metadata.get('mutation', 'initial')}"
            )
        else:
            status = OptimizationStatus.NO_IMPROVEMENT
            message = (
                "Fallback optimisation found no improvement over baseline. "
                f"Baseline: {baseline_score:.4f}, Best: {best_score:.4f}"
            )

        return OptimizationResult(
            status=status,
            best_prompt=best_candidate,
            baseline_score=baseline_score,
            best_score=best_score,
            improvement_pct=round(improvement, 2),
            iterations=self._max_iterations,
            candidates_evaluated=candidates_evaluated,
            elapsed_seconds=0.0,  # Will be overridden by caller
            history=history,
            message=message,
        )
