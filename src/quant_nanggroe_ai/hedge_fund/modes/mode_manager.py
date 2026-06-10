"""
Mode Manager for AI Quant Hedge Fund
Manages trading modes: MANUAL, SEMI_AUTO, FULL_AUTO
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading mode options."""
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


@dataclass
class ModeConfig:
    """Configuration for a trading mode."""
    auto_analyze: bool
    auto_signal: bool
    auto_execute: bool
    require_confirmation: bool
    notify_user: bool
    max_position_size: float
    max_daily_loss: float
    max_correlation: float
    auto_hedge: bool
    emergency_stop: bool
    
    @classmethod
    def manual(cls) -> "ModeConfig":
        """Manual mode: View only, no auto actions."""
        return cls(
            auto_analyze=False,
            auto_signal=False,
            auto_execute=False,
            require_confirmation=False,
            notify_user=True,
            max_position_size=0.0,
            max_daily_loss=0.0,
            max_correlation=0.0,
            auto_hedge=False,
            emergency_stop=True
        )
    
    @classmethod
    def semi_auto(cls) -> "ModeConfig":
        """Semi-auto mode: Auto analyze, manual confirmation."""
        return cls(
            auto_analyze=True,
            auto_signal=True,
            auto_execute=False,
            require_confirmation=True,
            notify_user=True,
            max_position_size=10.0,
            max_daily_loss=0.05,
            max_correlation=0.7,
            auto_hedge=False,
            emergency_stop=True
        )
    
    @classmethod
    def full_auto(cls) -> "ModeConfig":
        """Full auto mode: Fully autonomous trading."""
        return cls(
            auto_analyze=True,
            auto_signal=True,
            auto_execute=True,
            require_confirmation=False,
            notify_user=False,
            max_position_size=20.0,
            max_daily_loss=0.10,
            max_correlation=0.8,
            auto_hedge=True,
            emergency_stop=True
        )
    
    def to_dict(self) -> Dict:
        return {
            "auto_analyze": self.auto_analyze,
            "auto_signal": self.auto_signal,
            "auto_execute": self.auto_execute,
            "require_confirmation": self.require_confirmation,
            "notify_user": self.notify_user,
            "max_position_size": self.max_position_size,
            "max_daily_loss": self.max_daily_loss,
            "max_correlation": self.max_correlation,
            "auto_hedge": self.auto_hedge,
            "emergency_stop": self.emergency_stop
        }


@dataclass
class ModeChange:
    """Record of a mode change."""
    timestamp: datetime
    from_mode: Optional[TradingMode]
    to_mode: TradingMode
    reason: str
    config: Dict


class ModeManager:
    """
    Manages trading modes and their configurations.
    
    Provides:
    - Mode switching
    - Configuration management
    - Mode history tracking
    - Callback system for mode changes
    """
    
    def __init__(self, initial_mode: TradingMode = TradingMode.SEMI_AUTO):
        self._current_mode = initial_mode
        self._config = self._get_config_for_mode(initial_mode)
        self._mode_history: List[ModeChange] = []
        self._callbacks: List[Callable] = []
        self._emergency_stop_active = False
        self._last_emergency_stop_time: Optional[datetime] = None
        
        self._record_mode_change(None, initial_mode, "Initial mode")
    
    @property
    def current_mode(self) -> TradingMode:
        return self._current_mode
    
    @property
    def config(self) -> ModeConfig:
        return self._config
    
    @property
    def mode_history(self) -> List[ModeChange]:
        return self._mode_history.copy()
    
    @property
    def is_manual(self) -> bool:
        return self._current_mode == TradingMode.MANUAL
    
    @property
    def is_semi_auto(self) -> bool:
        return self._current_mode == TradingMode.SEMI_AUTO
    
    @property
    def is_full_auto(self) -> bool:
        return self._current_mode == TradingMode.FULL_AUTO
    
    @property
    def can_analyze(self) -> bool:
        return self._config.auto_analyze and not self._emergency_stop_active
    
    @property
    def can_execute(self) -> bool:
        return self._config.auto_execute and not self._emergency_stop_active
    
    @property
    def requires_confirmation(self) -> bool:
        return self._config.require_confirmation
    
    @property
    def should_notify(self) -> bool:
        return self._config.notify_user
    
    @property
    def is_emergency_stop(self) -> bool:
        return self._emergency_stop_active
    
    def set_mode(
        self,
        mode: TradingMode,
        reason: str = "User request"
    ) -> bool:
        """
        Change the trading mode.
        
        Args:
            mode: New trading mode
            reason: Reason for mode change
            
        Returns:
            bool: True if mode was changed
        """
        if mode == self._current_mode:
            logger.info(f"Already in {mode.value} mode")
            return False
        
        old_mode = self._current_mode
        self._current_mode = mode
        self._config = self._get_config_for_mode(mode)
        
        self._record_mode_change(old_mode, mode, reason)
        self._notify_callbacks(old_mode, mode)
        
        logger.info(f"Mode changed: {old_mode.value} -> {mode.value} ({reason})")
        return True
    
    def activate_emergency_stop(self, reason: str = "Emergency stop triggered") -> None:
        """
        Activate emergency stop mode.
        
        Args:
            reason: Reason for emergency stop
        """
        self._emergency_stop_active = True
        self._last_emergency_stop_time = datetime.now()
        
        logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
        
        self._notify_callbacks(
            self._current_mode,
            self._current_mode,
            emergency_stop=True
        )
    
    def deactivate_emergency_stop(self) -> None:
        """Deactivate emergency stop."""
        if self._emergency_stop_active:
            self._emergency_stop_active = False
            logger.info("Emergency stop deactivated")
    
    def is_execution_allowed(
        self,
        confidence: float,
        position_size: float,
        current_daily_loss: float
    ) -> tuple:
        """
        Check if execution is allowed based on mode config.
        
        Args:
            confidence: Signal confidence
            position_size: Proposed position size
            current_daily_loss: Current daily loss percentage
            
        Returns:
            tuple: (allowed: bool, reason: str)
        """
        if self._emergency_stop_active:
            return False, "Emergency stop is active"
        
        if not self._config.auto_execute:
            return False, "Auto-execution is disabled in current mode"
        
        if position_size > self._config.max_position_size:
            return False, f"Position size {position_size} exceeds limit {self._config.max_position_size}"
        
        if current_daily_loss >= self._config.max_daily_loss:
            return False, f"Daily loss limit reached ({current_daily_loss:.1%})"
        
        if confidence < 0.6:
            return False, f"Confidence {confidence:.0%} below minimum threshold"
        
        return True, "Execution allowed"
    
    def should_auto_approve(self, confidence: float) -> bool:
        """
        Check if signal should be auto-approved without confirmation.
        
        Args:
            confidence: Signal confidence
            
        Returns:
            bool: True if auto-approval
        """
        if self._current_mode != TradingMode.SEMI_AUTO:
            return False
        
        return confidence >= 0.85
    
    def add_callback(self, callback: Callable) -> None:
        """Add callback for mode changes."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable) -> None:
        """Remove mode change callback."""
        self._callbacks.remove(callback)
    
    def get_mode_summary(self) -> Dict:
        """Get current mode summary."""
        return {
            "current_mode": self._current_mode.value,
            "config": self._config.to_dict(),
            "emergency_stop": self._emergency_stop_active,
            "can_analyze": self.can_analyze,
            "can_execute": self.can_execute,
            "requires_confirmation": self.requires_confirmation,
            "history_count": len(self._mode_history)
        }
    
    def _get_config_for_mode(self, mode: TradingMode) -> ModeConfig:
        """Get configuration for a mode."""
        configs = {
            TradingMode.MANUAL: ModeConfig.manual(),
            TradingMode.SEMI_AUTO: ModeConfig.semi_auto(),
            TradingMode.FULL_AUTO: ModeConfig.full_auto()
        }
        return configs.get(mode, ModeConfig.manual())
    
    def _record_mode_change(
        self,
        from_mode: Optional[TradingMode],
        to_mode: TradingMode,
        reason: str
    ) -> None:
        """Record mode change in history."""
        change = ModeChange(
            timestamp=datetime.now(),
            from_mode=from_mode,
            to_mode=to_mode,
            reason=reason,
            config=self._config.to_dict()
        )
        self._mode_history.append(change)
        
        if len(self._mode_history) > 100:
            self._mode_history = self._mode_history[-100:]
    
    def _notify_callbacks(
        self,
        from_mode: TradingMode,
        to_mode: TradingMode,
        emergency_stop: bool = False
    ) -> None:
        """Notify all callbacks of mode change."""
        for callback in self._callbacks:
            try:
                callback(
                    from_mode=from_mode.value if from_mode else None,
                    to_mode=to_mode.value,
                    config=self._config.to_dict(),
                    emergency_stop=emergency_stop
                )
            except Exception as e:
                logger.error(f"Mode callback error: {e}")
    
    def get_mode_comparison(self) -> Dict:
        """Get comparison of all modes."""
        return {
            TradingMode.MANUAL.value: ModeConfig.manual().to_dict(),
            TradingMode.SEMI_AUTO.value: ModeConfig.semi_auto().to_dict(),
            TradingMode.FULL_AUTO.value: ModeConfig.full_auto().to_dict()
        }


def create_mode_manager(mode: str = "semi_auto") -> ModeManager:
    """
    Factory function to create mode manager.
    
    Args:
        mode: Initial mode ("manual", "semi_auto", "full_auto")
        
    Returns:
        ModeManager instance
    """
    mode_map = {
        "manual": TradingMode.MANUAL,
        "semi_auto": TradingMode.SEMI_AUTO,
        "semi": TradingMode.SEMI_AUTO,
        "full_auto": TradingMode.FULL_AUTO,
        "auto": TradingMode.FULL_AUTO
    }
    
    trading_mode = mode_map.get(mode.lower(), TradingMode.SEMI_AUTO)
    return ModeManager(initial_mode=trading_mode)
