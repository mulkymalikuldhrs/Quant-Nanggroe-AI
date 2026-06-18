"""NVIDIA NIM Intelligent Model Router.

Routes different task types to optimal NIM models, implements fallback
chains when primary models are unavailable, tracks per-model performance
metrics, and optimises for cost when quality differences are marginal.

Task-to-Model Mapping
---------------------
- ANALYSIS   → meta/llama-3.1-70b-instruct  (fast, capable)
- STRATEGY   → meta/llama-3.1-405b-instruct  (most capable)
- RISK       → mistralai/mixtral-8x22b-instruct (balanced)
- SENTIMENT  → google/gemma-2-27b-it         (fast)
- CODE       → microsoft/phi-3-medium-128k-instruct (code-specialised)
- REWARD     → nvidia/nemotron-4-340b-reward  (reward model)

Usage::

    from quant_nanggroe.engine.nvidia_nim import NIMModelRouter, NIMClient

    router = NIMModelRouter(NIMClient())
    decision = router.route(TaskType.ANALYSIS)
    response = await router.chat(TaskType.ANALYSIS, "Analyze AAPL")
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from quant_nanggroe.engine.nvidia_nim.client import NIMClient, NIMAPIError, NIMRateLimitError
from quant_nanggroe.engine.nvidia_nim.config import NIMConfig, get_nim_config
from quant_nanggroe.engine.nvidia_nim.models import (
    NIMChatResponse,
    NIMModelMetrics,
    NIMModelStatus,
    NIMRoutingDecision,
    TaskType,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Task → Model mapping (primary + fallback chain)
# ---------------------------------------------------------------------------

_TASK_MODEL_MAP: Dict[TaskType, Dict[str, Any]] = {
    TaskType.ANALYSIS: {
        "primary": "meta/llama-3.1-70b-instruct",
        "fallbacks": [
            "mistralai/mixtral-8x22b-instruct",
            "google/gemma-2-27b-it",
            "microsoft/phi-3-medium-128k-instruct",
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    },
    TaskType.STRATEGY: {
        "primary": "meta/llama-3.1-405b-instruct",
        "fallbacks": [
            "meta/llama-3.1-70b-instruct",
            "mistralai/mixtral-8x22b-instruct",
        ],
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    TaskType.RISK: {
        "primary": "mistralai/mixtral-8x22b-instruct",
        "fallbacks": [
            "meta/llama-3.1-70b-instruct",
            "google/gemma-2-27b-it",
        ],
        "temperature": 0.05,
        "max_tokens": 4096,
    },
    TaskType.SENTIMENT: {
        "primary": "google/gemma-2-27b-it",
        "fallbacks": [
            "meta/llama-3.1-70b-instruct",
            "microsoft/phi-3-medium-128k-instruct",
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
    },
    TaskType.CODE: {
        "primary": "microsoft/phi-3-medium-128k-instruct",
        "fallbacks": [
            "meta/llama-3.1-70b-instruct",
            "mistralai/mixtral-8x22b-instruct",
        ],
        "temperature": 0.1,
        "max_tokens": 8192,
    },
    TaskType.REWARD: {
        "primary": "nvidia/nemotron-4-340b-reward",
        "fallbacks": [
            "meta/llama-3.1-70b-instruct",
        ],
        "temperature": 0.0,
        "max_tokens": 1024,
    },
}

# Quality tolerance threshold: if a cheaper model's success rate is within
# this margin of the primary, the router may prefer the cheaper option.
_COST_OPTIMISATION_THRESHOLD = 0.05


class NIMModelRouter:
    """Intelligent model router for NVIDIA NIM inference microservices.

    Routes different task types to optimal models, implements fallback
    chains when primary models are unavailable, tracks per-model
    performance metrics, and optimises for cost when quality differences
    are marginal.

    Args:
        client: An initialised NIMClient instance.
        config: Optional NIMConfig (uses global default if not provided).
    """

    def __init__(
        self,
        client: NIMClient,
        config: Optional[NIMConfig] = None,
    ) -> None:
        self._client = client
        self._config = config or get_nim_config()
        self._metrics: Dict[str, NIMModelMetrics] = {}
        self._initialize_metrics()

    # ------------------------------------------------------------------
    # Metrics initialization
    # ------------------------------------------------------------------

    def _initialize_metrics(self) -> None:
        """Pre-populate metrics for all known models."""
        all_models: set[str] = set()
        for task_config in _TASK_MODEL_MAP.values():
            all_models.add(task_config["primary"])
            all_models.update(task_config["fallbacks"])

        for model_id in sorted(all_models):
            self._metrics[model_id] = NIMModelMetrics(model_id=model_id)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(
        self,
        task_type: TaskType,
        *,
        prefer_cheaper: bool = False,
    ) -> NIMRoutingDecision:
        """Determine the optimal model for a given task type.

        Selects the primary model or, if it is unhealthy/rate-limited,
        walks the fallback chain.  When ``prefer_cheaper`` is True and
        the primary model's success rate is within the cost-optimisation
        threshold of a cheaper alternative, the cheaper model is chosen.

        Args:
            task_type: The task being routed.
            prefer_cheaper: Prefer cheaper models when quality is close.

        Returns:
            NIMRoutingDecision with the selected model and reasoning.
        """
        task_config = _TASK_MODEL_MAP[task_type]
        primary = task_config["primary"]
        fallbacks = list(task_config["fallbacks"])

        # Cost optimisation: consider swapping primary for a cheaper alternative
        selected = primary
        reason = "Primary model for task"

        if prefer_cheaper:
            cheaper = self._find_cheaper_alternative(primary, fallbacks)
            if cheaper is not None:
                selected = cheaper
                reason = "Cost-optimised: cheaper alternative within quality threshold"

        # Check if selected model is available
        metrics = self._metrics.get(selected)
        if metrics and metrics.status in (
            NIMModelStatus.RATE_LIMITED,
            NIMModelStatus.UNAVAILABLE,
        ):
            # Walk fallback chain
            for fb in fallbacks:
                fb_metrics = self._metrics.get(fb)
                if fb_metrics is None or fb_metrics.status not in (
                    NIMModelStatus.RATE_LIMITED,
                    NIMModelStatus.UNAVAILABLE,
                ):
                    selected = fb
                    reason = f"Fallback from {primary} (unavailable)"
                    break
            else:
                # All fallbacks exhausted; try primary anyway
                reason = f"All fallbacks exhausted, retrying {primary}"
                selected = primary

        cost_estimate = self._estimate_call_cost(
            selected, task_config["max_tokens"]
        )

        # Estimate latency from historical data
        est_latency = 0.0
        if metrics:
            est_latency = metrics.avg_latency_ms
        elif selected in self._metrics:
            est_latency = self._metrics[selected].avg_latency_ms

        decision = NIMRoutingDecision(
            task_type=task_type,
            primary_model=primary,
            fallback_chain=fallbacks,
            selected_model=selected,
            reason=reason,
            cost_estimate_usd=cost_estimate,
            estimated_latency_ms=est_latency,
        )

        logger.debug(
            "nim_route",
            task_type=task_type.value,
            selected=selected,
            reason=reason,
        )

        return decision

    # ------------------------------------------------------------------
    # Chat with routing
    # ------------------------------------------------------------------

    async def chat(
        self,
        task_type: TaskType,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        prefer_cheaper: bool = False,
    ) -> NIMChatResponse:
        """Send a chat request with automatic model routing and fallback.

        Routes to the optimal model for ``task_type``, then falls back
        through the fallback chain if the primary model fails.

        Args:
            task_type: Task type for routing.
            prompt: User message text.
            system_prompt: Optional system message.
            prefer_cheaper: Prefer cheaper models when quality is close.

        Returns:
            NIMChatResponse from the first successful model.

        Raises:
            RuntimeError: If all models in the chain fail.
        """
        decision = self.route(task_type, prefer_cheaper=prefer_cheaper)
        task_config = _TASK_MODEL_MAP[task_type]

        # Build attempt order: selected → remaining fallbacks
        attempt_order = [decision.selected_model]
        for fb in decision.fallback_chain:
            if fb not in attempt_order:
                attempt_order.append(fb)

        last_error: Exception | None = None

        for model_id in attempt_order:
            try:
                response = await self._client.chat(
                    prompt,
                    system_prompt=system_prompt,
                    model=model_id,
                    temperature=task_config["temperature"],
                    max_tokens=task_config["max_tokens"],
                )

                # Record success
                self._record_success(
                    model_id,
                    latency_ms=response.usage.latency_ms,
                    tokens_in=response.usage.prompt_tokens,
                    tokens_out=response.usage.completion_tokens,
                    cost_usd=response.usage.cost_usd,
                )

                return response

            except (NIMAPIError, NIMRateLimitError) as exc:
                last_error = exc
                self._record_failure(model_id, str(exc))

                logger.warning(
                    "nim_model_fallback",
                    model=model_id,
                    error=str(exc)[:200],
                    task_type=task_type.value,
                )
                continue

        raise RuntimeError(
            f"All NIM models failed for task {task_type.value}: {last_error}"
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get model performance metrics.

        Args:
            model_id: If provided, return metrics for a specific model.
                If None, return metrics for all models.

        Returns:
            Dict with metrics data.
        """
        if model_id:
            metrics = self._metrics.get(model_id)
            if metrics is None:
                return {"error": f"Unknown model: {model_id}"}
            return metrics.model_dump()

        return {
            mid: m.model_dump()
            for mid, m in self._metrics.items()
        }

    def get_task_model_map(self) -> Dict[str, Dict[str, Any]]:
        """Return the current task-to-model mapping configuration.

        Returns:
            Dict mapping TaskType values to their model configurations.
        """
        return {
            tt.value: {
                "primary": cfg["primary"],
                "fallbacks": cfg["fallbacks"],
                "temperature": cfg["temperature"],
                "max_tokens": cfg["max_tokens"],
            }
            for tt, cfg in _TASK_MODEL_MAP.items()
        }

    def mark_model_unavailable(self, model_id: str, reason: str = "") -> None:
        """Manually mark a model as unavailable.

        Args:
            model_id: NIM model identifier.
            reason: Reason for marking unavailable.
        """
        if model_id in self._metrics:
            self._metrics[model_id].status = NIMModelStatus.UNAVAILABLE
            self._metrics[model_id].last_error = reason or "Manually marked unavailable"
            logger.info("nim_model_marked_unavailable", model=model_id, reason=reason)

    def mark_model_available(self, model_id: str) -> None:
        """Manually mark a model as available.

        Args:
            model_id: NIM model identifier.
        """
        if model_id in self._metrics:
            self._metrics[model_id].status = NIMModelStatus.AVAILABLE
            self._metrics[model_id].consecutive_failures = 0
            self._metrics[model_id].last_error = None
            logger.info("nim_model_marked_available", model=model_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_cheaper_alternative(
        self, primary: str, fallbacks: List[str]
    ) -> Optional[str]:
        """Check if a cheaper fallback is within quality threshold.

        Compares the primary model's success rate with each fallback.
        If a cheaper model's success rate is within the cost-optimisation
        threshold, it is returned.

        Args:
            primary: Primary model identifier.
            fallbacks: Fallback model identifiers.

        Returns:
            Cheaper model identifier or None.
        """
        primary_metrics = self._metrics.get(primary)
        if primary_metrics is None or primary_metrics.total_requests < 10:
            # Not enough data to make a cost-optimised decision
            return None

        primary_rate = primary_metrics.success_rate

        for fb in fallbacks:
            fb_metrics = self._metrics.get(fb)
            if fb_metrics is None or fb_metrics.total_requests < 10:
                continue

            fb_rate = fb_metrics.success_rate

            # Check if fallback is cheaper and within quality threshold
            fb_cost = NIMClient.estimate_cost(fb, 1000, 500)
            primary_cost = NIMClient.estimate_cost(primary, 1000, 500)

            if (
                fb_cost < primary_cost
                and (primary_rate - fb_rate) <= _COST_OPTIMISATION_THRESHOLD
            ):
                return fb

        return None

    @staticmethod
    def _estimate_call_cost(model: str, max_tokens: int) -> float:
        """Estimate cost for a single chat call.

        Uses a heuristic of input ≈ max_tokens/2 and output ≈ max_tokens/2.

        Args:
            model: NIM model identifier.
            max_tokens: Max output tokens for the request.

        Returns:
            Estimated cost in USD.
        """
        estimated_input = max_tokens // 2
        estimated_output = max_tokens // 2
        return NIMClient.estimate_cost(model, estimated_input, estimated_output)

    def _record_success(
        self,
        model_id: str,
        latency_ms: float,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
    ) -> None:
        """Record a successful call in the metrics."""
        metrics = self._metrics.get(model_id)
        if metrics is None:
            metrics = NIMModelMetrics(model_id=model_id)
            self._metrics[model_id] = metrics

        metrics.total_requests += 1
        metrics.total_tokens_in += tokens_in
        metrics.total_tokens_out += tokens_out
        metrics.total_cost_usd += cost_usd
        metrics.consecutive_failures = 0
        metrics.last_used_at = datetime.now(tz=timezone.utc).isoformat()
        metrics.last_error = None

        # Update latency stats
        if metrics.avg_latency_ms == 0:
            metrics.avg_latency_ms = latency_ms
        else:
            metrics.avg_latency_ms = (
                metrics.avg_latency_ms * 0.8 + latency_ms * 0.2
            )
        metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
        metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)

        # Mark available
        if metrics.status != NIMModelStatus.AVAILABLE:
            metrics.status = NIMModelStatus.AVAILABLE

    def _record_failure(self, model_id: str, error: str) -> None:
        """Record a failed call in the metrics."""
        metrics = self._metrics.get(model_id)
        if metrics is None:
            metrics = NIMModelMetrics(model_id=model_id)
            self._metrics[model_id] = metrics

        metrics.total_requests += 1
        metrics.total_failures += 1
        metrics.consecutive_failures += 1
        metrics.last_error = error[:500]
        metrics.last_used_at = datetime.now(tz=timezone.utc).isoformat()

        # Update status based on failure pattern
        if metrics.consecutive_failures >= 5:
            metrics.status = NIMModelStatus.UNAVAILABLE
        elif metrics.consecutive_failures >= 3:
            metrics.status = NIMModelStatus.RATE_LIMITED


__all__ = ["NIMModelRouter", "_TASK_MODEL_MAP"]
