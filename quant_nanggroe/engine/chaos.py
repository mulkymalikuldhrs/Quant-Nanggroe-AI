"""Chaos engineering utilities for testing system resilience."""
import random
import time
import structlog
from typing import Optional, Callable, Any
from enum import Enum
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

class ChaosType(str, Enum):
    LATENCY_SPIKE = "latency_spike"
    EXCHANGE_TIMEOUT = "exchange_timeout"
    DATA_FEED_CORRUPTION = "data_feed_corruption"
    MEMORY_PRESSURE = "memory_pressure"
    KILL_SWITCH_STORM = "kill_switch_storm"
    PARTIAL_FILL = "partial_fill"
    SLIPPAGE_BURST = "slippage_burst"

class ChaosConfig(BaseModel):
    enabled: bool = False
    probability: float = Field(default=0.1, ge=0.0, le=1.0)
    chaos_types: list[ChaosType] = Field(default_factory=lambda: list(ChaosType))
    max_latency_ms: int = 5000
    seed: Optional[int] = None

class ChaosResult(BaseModel):
    chaos_type: ChaosType
    injected: bool
    description: str
    duration_ms: float = 0.0

class ChaosEngine:
    """Inject controlled failures for resilience testing."""
    
    def __init__(self, config: ChaosConfig):
        self.config = config
        self._rng = random.Random(config.seed)
        self._injection_count = 0
        self._results: list[ChaosResult] = []
    
    def maybe_inject(self, chaos_type: ChaosType) -> ChaosResult:
        """Potentially inject a failure based on probability."""
        if not self.config.enabled:
            return ChaosResult(chaos_type=chaos_type, injected=False, description="Chaos disabled")
        if chaos_type not in self.config.chaos_types:
            return ChaosResult(chaos_type=chaos_type, injected=False, description=f"{chaos_type} not in scope")
        if self._rng.random() > self.config.probability:
            return ChaosResult(chaos_type=chaos_type, injected=False, description="Probability threshold not met")
        
        # Inject the failure
        self._injection_count += 1
        result = self._inject(chaos_type)
        self._results.append(result)
        logger.warning("chaos_injected", chaos_type=chaos_type.value, description=result.description)
        return result
    
    def _inject(self, chaos_type: ChaosType) -> ChaosResult:
        if chaos_type == ChaosType.LATENCY_SPIKE:
            delay = self._rng.uniform(0, self.config.max_latency_ms / 1000)
            time.sleep(delay)
            return ChaosResult(chaos_type=chaos_type, injected=True, 
                             description=f"Injected {delay:.3f}s latency", duration_ms=delay*1000)
        elif chaos_type == ChaosType.EXCHANGE_TIMEOUT:
            return ChaosResult(chaos_type=chaos_type, injected=True, 
                             description="Simulated exchange timeout")
        elif chaos_type == ChaosType.DATA_FEED_CORRUPTION:
            return ChaosResult(chaos_type=chaos_type, injected=True, 
                             description="Corrupted data feed (NaN injection)")
        elif chaos_type == ChaosType.PARTIAL_FILL:
            fill_pct = self._rng.uniform(0.1, 0.9)
            return ChaosResult(chaos_type=chaos_type, injected=True, 
                             description=f"Partial fill: {fill_pct:.0%}")
        elif chaos_type == ChaosType.SLIPPAGE_BURST:
            slippage = self._rng.uniform(0.5, 5.0)  # 0.5% to 5%
            return ChaosResult(chaos_type=chaos_type, injected=True, 
                             description=f"Slippage burst: {slippage:.2f}%")
        elif chaos_type == ChaosType.KILL_SWITCH_STORM:
            return ChaosResult(chaos_type=chaos_type, injected=True, 
                             description="Kill switch trigger storm")
        elif chaos_type == ChaosType.MEMORY_PRESSURE:
            return ChaosResult(chaos_type=chaos_type, injected=True, 
                             description="Memory pressure simulation")
        return ChaosResult(chaos_type=chaos_type, injected=False, description="Unknown type")
    
    @property
    def injection_count(self) -> int:
        return self._injection_count
    
    def get_results(self) -> list[ChaosResult]:
        return list(self._results)
    
    def reset(self) -> None:
        self._injection_count = 0
        self._results.clear()
