"""
🛡️ Error Recovery System - Autonomous Error Handling & Recovery
Self-healing system for detecting, diagnosing, and recovering from errors

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import time
import traceback
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum


class RecoveryStrategy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    RESTART = "restart"
    SKIP = "skip"
    ESCALATE = "escalate"


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorRecoverySystem:
    """
    Autonomous error recovery system that:
    - Detects and classifies errors
    - Applies appropriate recovery strategies
    - Tracks error patterns and frequencies
    - Provides self-healing capabilities
    - Escalates unrecoverable errors
    """

    def __init__(self):
        self.system_id = "error_recovery"
        self.status = "active"

        # Error tracking
        self.error_history: List[Dict] = []
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}

        # Recovery handlers
        self.recovery_handlers: Dict[str, Callable] = {}
        self.escalation_handlers: List[Callable] = []

        # Configuration
        self.max_retry_attempts = 3
        self.retry_delay_base = 5  # seconds
        self.max_error_history = 1000

        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict] = {}

        # Register default strategies
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register default recovery strategies for common error types"""
        self.recovery_strategies = {
            "ConnectionError": RecoveryStrategy.RETRY,
            "TimeoutError": RecoveryStrategy.RETRY,
            "ValueError": RecoveryStrategy.FALLBACK,
            "KeyError": RecoveryStrategy.FALLBACK,
            "ImportError": RecoveryStrategy.SKIP,
            "AttributeError": RecoveryStrategy.ESCALATE,
            "RuntimeError": RecoveryStrategy.RESTART,
            "Exception": RecoveryStrategy.ESCALATE,
        }

    def handle_error(self, error: Exception, context: Dict = None) -> Dict[str, Any]:
        """
        Handle an error with automatic recovery

        Args:
            error: The exception that occurred
            context: Additional context about where/why the error occurred

        Returns:
            Recovery result with status and action taken
        """
        error_type = type(error).__name__
        error_info = {
            "error_type": error_type,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "severity": self._classify_severity(error),
        }

        # Record error
        self._record_error(error_info)

        # Get recovery strategy
        strategy = self.recovery_strategies.get(
            error_type, RecoveryStrategy.ESCALATE
        )

        # Check circuit breaker
        if self._is_circuit_open(error_type):
            return {
                "recovered": False,
                "strategy": "circuit_breaker",
                "message": f"Circuit breaker open for {error_type}",
                "error_info": error_info,
            }

        # Apply recovery strategy
        result = self._apply_strategy(strategy, error_info)

        return result

    def _classify_severity(self, error: Exception) -> ErrorSeverity:
        """Classify error severity"""
        error_type = type(error).__name__

        critical_errors = {"SystemExit", "KeyboardInterrupt", "MemoryError"}
        high_errors = {"RuntimeError", "ConnectionError", "TimeoutError"}
        medium_errors = {"ValueError", "KeyError", "TypeError"}

        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL
        elif error_type in high_errors:
            return ErrorSeverity.HIGH
        elif error_type in medium_errors:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _record_error(self, error_info: Dict):
        """Record error in history"""
        self.error_history.append(error_info)
        error_type = error_info["error_type"]
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Trim history if too long
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]

        # Update circuit breaker
        self._update_circuit_breaker(error_type)

    def _update_circuit_breaker(self, error_type: str):
        """Update circuit breaker state for an error type"""
        if error_type not in self.circuit_breakers:
            self.circuit_breakers[error_type] = {
                "failure_count": 0,
                "last_failure": None,
                "state": "closed",  # closed, open, half_open
                "opened_at": None,
            }

        cb = self.circuit_breakers[error_type]
        cb["failure_count"] += 1
        cb["last_failure"] = datetime.now().isoformat()

        # Open circuit breaker if too many failures
        if cb["failure_count"] >= self.max_retry_attempts and cb["state"] == "closed":
            cb["state"] = "open"
            cb["opened_at"] = datetime.now().isoformat()

    def _is_circuit_open(self, error_type: str) -> bool:
        """Check if circuit breaker is open for error type"""
        if error_type not in self.circuit_breakers:
            return False

        cb = self.circuit_breakers[error_type]
        if cb["state"] == "open":
            # Check if we should try half-open
            if cb["opened_at"]:
                opened_time = datetime.fromisoformat(cb["opened_at"])
                elapsed = (datetime.now() - opened_time).total_seconds()
                if elapsed > self.retry_delay_base * 60:  # Reset after base*60 seconds
                    cb["state"] = "half_open"
                    return False
            return True
        return False

    def _apply_strategy(self, strategy: RecoveryStrategy, error_info: Dict) -> Dict[str, Any]:
        """Apply a recovery strategy"""
        result = {
            "recovered": False,
            "strategy": strategy.value,
            "error_info": error_info,
        }

        if strategy == RecoveryStrategy.RETRY:
            result["message"] = f"Will retry after delay"
            result["retry_delay"] = self.retry_delay_base

        elif strategy == RecoveryStrategy.FALLBACK:
            result["message"] = "Using fallback approach"

        elif strategy == RecoveryStrategy.RESTART:
            result["message"] = "Component restart recommended"

        elif strategy == RecoveryStrategy.SKIP:
            result["recovered"] = True
            result["message"] = "Error skipped as non-critical"

        elif strategy == RecoveryStrategy.ESCALATE:
            result["message"] = "Error escalated for manual review"
            self._escalate_error(error_info)

        return result

    def _escalate_error(self, error_info: Dict):
        """Escalate error to registered handlers"""
        for handler in self.escalation_handlers:
            try:
                handler(error_info)
            except Exception:
                pass  # Don't let escalation failures cascade

    def register_recovery_handler(self, error_type: str, handler: Callable):
        """Register a custom recovery handler for an error type"""
        self.recovery_handlers[error_type] = handler

    def register_escalation_handler(self, handler: Callable):
        """Register an escalation handler"""
        self.escalation_handlers.append(handler)
    
    def record_failure(self, service_name: str):
        """Record a failure for a service (for circuit breaker pattern)"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = {
                "failure_count": 0,
                "last_failure": None,
                "state": "closed",
                "opened_at": None,
            }
        
        cb = self.circuit_breakers[service_name]
        cb["failure_count"] += 1
        cb["last_failure"] = datetime.now().isoformat()
        
        # Open circuit breaker if too many failures
        if cb["failure_count"] >= self.max_retry_attempts and cb["state"] == "closed":
            cb["state"] = "open"
            cb["opened_at"] = datetime.now().isoformat()
    
    def get_circuit_status(self, service_name: str) -> str:
        """Get the circuit breaker status for a service"""
        if service_name not in self.circuit_breakers:
            return "closed"
        
        cb = self.circuit_breakers[service_name]
        state = cb.get("state", "closed")
        
        # Check if we should transition from open to half_open
        if state == "open" and cb.get("opened_at"):
            try:
                opened_time = datetime.fromisoformat(cb["opened_at"])
                elapsed = (datetime.now() - opened_time).total_seconds()
                if elapsed > self.retry_delay_base * 60:
                    cb["state"] = "half_open"
                    return "half_open"
            except (ValueError, TypeError):
                pass
        
        return state

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": len(self.error_history),
            "error_counts": self.error_counts,
            "circuit_breakers": {
                k: v["state"] for k, v in self.circuit_breakers.items()
            },
            "recent_errors": self.error_history[-10:] if self.error_history else [],
        }

    def reset_circuit_breaker(self, error_type: str = None):
        """Reset circuit breaker(s)"""
        if error_type:
            if error_type in self.circuit_breakers:
                self.circuit_breakers[error_type]["state"] = "closed"
                self.circuit_breakers[error_type]["failure_count"] = 0
        else:
            for cb in self.circuit_breakers.values():
                cb["state"] = "closed"
                cb["failure_count"] = 0


# Global instance
error_recovery = ErrorRecoverySystem()
