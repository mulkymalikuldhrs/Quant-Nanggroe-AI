"""Tests for DSPy Optimizer module."""

from __future__ import annotations

import pytest

from quant_nanggroe_ai.agents.dspy_optimizer import (
    DSPyOptimizer,
    OptimizationResult,
    is_dspy_available,
)


class TestDSPyAvailability:
    def test_is_dspy_available_returns_bool(self):
        result = is_dspy_available()
        assert isinstance(result, bool)

    def test_dspy_not_installed_in_test_env(self):
        # dspy is not installed in the test environment
        assert is_dspy_available() is False


class TestDSPyOptimizer:
    def test_create_optimizer(self):
        optimizer = DSPyOptimizer()
        assert optimizer is not None

    def test_optimize_with_fallback(self):
        optimizer = DSPyOptimizer()
        result = optimizer.optimize_agent_prompt(
            initial_prompt="You are a trading analyst. Analyze the market.",
            train_examples=[
                {"market_data": "bullish trend", "expected_action": "BUY"},
                {"market_data": "bearish trend", "expected_action": "SELL"},
            ],
        )
        assert isinstance(result, OptimizationResult)
        # Status can be enum or string
        status_val = result.status.value if hasattr(result.status, 'value') else str(result.status)
        assert status_val.lower() in ("completed", "fallback", "no_examples")
        assert result.best_prompt is not None

    def test_optimize_without_examples(self):
        optimizer = DSPyOptimizer()
        result = optimizer.optimize_agent_prompt(
            initial_prompt="Analyze market data.",
        )
        assert isinstance(result, OptimizationResult)

    def test_optimization_returns_best_prompt(self):
        optimizer = DSPyOptimizer()
        result = optimizer.optimize_agent_prompt(
            initial_prompt="You are a trading agent.",
            train_examples=[
                {"input": "high volatility", "output": "reduce position"},
            ],
        )
        assert result.best_prompt is not None
        # best_prompt can be a string or AgentPromptCandidate object
        prompt_text = str(result.best_prompt)
        assert len(prompt_text) > 0


class TestOptimizationResult:
    def test_create_result(self):
        result = OptimizationResult(
            status="completed",
            best_prompt="Optimized prompt",
            baseline_score=0.5,
            best_score=0.7,
            improvement_pct=40.0,
            history=[],
            iterations=3,
            candidates_evaluated=12,
            elapsed_seconds=1.5,
        )
        assert result.status == "completed"
        assert result.best_prompt == "Optimized prompt"
        assert result.improvement_pct == 40.0
