"""
Custom Exceptions
=================
Domain-specific exceptions for the trading system.
Each exception maps to a clear error category for API responses.
"""

from __future__ import annotations


class QuantNanggroeAIError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str = "UNKNOWN") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


# ── Engine Exceptions ─────────────────────────────────────────────────

class EngineError(QuantNanggroeAIError):
    """Base for all engine-layer errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="ENGINE_ERROR")


class InsufficientDataError(EngineError):
    """Not enough data points for calculation."""

    def __init__(self, required: int, actual: int, indicator: str = "") -> None:
        self.required = required
        self.actual = actual
        self.indicator = indicator
        msg = f"Insufficient data: need {required} points, got {actual}"
        if indicator:
            msg += f" for {indicator}"
        super().__init__(msg)


class InvalidParameterError(EngineError):
    """Invalid parameter passed to an engine function."""

    def __init__(self, parameter: str, value: object, reason: str = "") -> None:
        self.parameter = parameter
        self.value = value
        msg = f"Invalid parameter '{parameter}': {value}"
        if reason:
            msg += f" — {reason}"
        super().__init__(msg)


# ── Risk Exceptions ───────────────────────────────────────────────────

class RiskError(QuantNanggroeAIError):
    """Base for all risk-layer errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="RISK_ERROR")


class RiskVetoError(RiskError):
    """Risk officer vetoed the trade."""

    def __init__(self, symbol: str, reason: str) -> None:
        self.symbol = symbol
        self.reason = reason
        super().__init__(f"VETOED: {symbol} — {reason}")


class KillSwitchActiveError(RiskError):
    """Kill switch is active — all trading halted."""

    def __init__(self, reason: str = "Kill switch active") -> None:
        self.reason = reason
        super().__init__(f"KILL SWITCH ACTIVE: {reason}")


class DailyLimitExceededError(RiskError):
    """Daily loss limit exceeded."""

    def __init__(self, current_loss: float, limit: float) -> None:
        self.current_loss = current_loss
        self.limit = limit
        super().__init__(f"Daily loss limit exceeded: {current_loss:.2%} >= {limit:.2%}")


class WeeklyLimitExceededError(RiskError):
    """Weekly loss limit exceeded."""

    def __init__(self, current_loss: float, limit: float) -> None:
        self.current_loss = current_loss
        self.limit = limit
        super().__init__(f"Weekly loss limit exceeded: {current_loss:.2%} >= {limit:.2%}")


# ── Data Exceptions ───────────────────────────────────────────────────

class DataError(QuantNanggroeAIError):
    """Base for all data-layer errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="DATA_ERROR")


class DataSourceUnavailableError(DataError):
    """Data source is unavailable."""

    def __init__(self, source: str, detail: str = "") -> None:
        self.source = source
        msg = f"Data source unavailable: {source}"
        if detail:
            msg += f" — {detail}"
        super().__init__(msg)


class DataValidationError(DataError):
    """Data validation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ── Agent Exceptions ──────────────────────────────────────────────────

class AgentError(QuantNanggroeAIError):
    """Base for all agent-layer errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="AGENT_ERROR")


class AgentTimeoutError(AgentError):
    """Agent took too long to respond."""

    def __init__(self, agent_name: str, timeout_seconds: float) -> None:
        self.agent_name = agent_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Agent '{agent_name}' timed out after {timeout_seconds}s")


class AgentRoutingError(AgentError):
    """Error routing to an agent."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ── Execution Exceptions ─────────────────────────────────────────────

class ExecutionError(QuantNanggroeAIError):
    """Base for all execution-layer errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="EXECUTION_ERROR")


class OrderRejectedError(ExecutionError):
    """Order was rejected by the broker."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Order rejected: {reason}")


class SlippageExceededError(ExecutionError):
    """Slippage exceeded acceptable threshold."""

    def __init__(self, expected: float, actual: float, threshold: float) -> None:
        self.expected = expected
        self.actual = actual
        self.threshold = threshold
        super().__init__(
            f"Slippage exceeded: expected {expected:.4f}, got {actual:.4f} "
            f"(threshold: {threshold:.4f})"
        )
