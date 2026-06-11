"""Sensor Orchestrator Service — Wires multi-agent sensors to Pressure Engine.

This is Layer 3 of the 8-layer architecture:
    ingestion → normalization → regime detection → **MULTI-AGENT SENSOR** → pressure synthesis → risk guard → output → audit

The SensorOrchestrator:
1. Runs all registered sensors in parallel
2. Collects their outputs into a unified SensorReadout
3. Feeds the readout into the PressureNormalizationEngine

This closes the critical gap where PressureInput was hand-crafted
instead of being derived from actual sensor outputs.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SensorType(str, Enum):
    """Types of market sensors."""
    TECHNICAL = "technical"
    SMART_MONEY = "smart_money"
    FLOW = "flow"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    GEOPOLITICAL = "geopolitical"
    INTERMARKET = "intermarket"
    SCREENER = "screener"
    ONCHAIN = "onchain"


@dataclass
class SensorReading:
    """Output from a single sensor agent."""
    sensor_type: SensorType
    symbol: str
    signal_direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    confidence: float  # 0.0 to 1.0
    strength: float  # 0.0 to 1.0 (how strong the signal is)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "computed"  # "live", "cached", "historical", "computed"


@dataclass
class SensorReadout:
    """Aggregated output from all sensors for a symbol.

    This is the input to the PressureNormalizationEngine.
    """
    symbol: str
    readings: List[SensorReading] = field(default_factory=list)
    composite_direction: str = "NEUTRAL"
    composite_confidence: float = 0.0
    composite_strength: float = 0.0
    regime: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_pressure_input(self) -> Dict[str, Any]:
        """Convert to PressureInput-compatible dict for the Pressure Engine.

        Maps sensor readings to the pressure dimensions used by
        engine/pressure.py PressureNormalizationEngine.
        """
        reading_map = {r.sensor_type: r for r in self.readings}

        # Extract individual sensor values
        technical = reading_map.get(SensorType.TECHNICAL)
        smart_money = reading_map.get(SensorType.SMART_MONEY)
        flow = reading_map.get(SensorType.FLOW)
        sentiment = reading_map.get(SensorType.SENTIMENT)
        macro = reading_map.get(SensorType.MACRO)

        return {
            "symbol": self.symbol,
            "technical_pressure": self._direction_to_pressure(technical),
            "smart_money_pressure": self._direction_to_pressure(smart_money),
            "flow_pressure": self._direction_to_pressure(flow),
            "sentiment_pressure": self._direction_to_pressure(sentiment),
            "macro_pressure": self._direction_to_pressure(macro),
            "composite_direction": self.composite_direction,
            "composite_confidence": self.composite_confidence,
            "composite_strength": self.composite_strength,
            "regime": self.regime,
            "timestamp": self.timestamp,
            "sensor_count": len(self.readings),
        }

    @staticmethod
    def _direction_to_pressure(reading: Optional[SensorReading]) -> float:
        """Convert sensor reading to pressure value (-1.0 to +1.0)."""
        if reading is None:
            return 0.0
        direction_map = {"BULLISH": 1.0, "BEARISH": -1.0, "NEUTRAL": 0.0}
        base = direction_map.get(reading.signal_direction, 0.0)
        return base * reading.confidence * reading.strength


# Type for sensor functions
SensorFunction = Callable[[str], SensorReading]


class SensorOrchestrator:
    """Orchestrates parallel sensor execution and aggregates results.

    The orchestrator:
    1. Registers sensor functions by type
    2. Runs all sensors for a given symbol (parallel)
    3. Aggregates results into a SensorReadout
    4. Feeds the readout to the Pressure Engine

    Usage:
        orchestrator = SensorOrchestrator()
        orchestrator.register(SensorType.TECHNICAL, my_technical_sensor)
        orchestrator.register(SensorType.SENTIMENT, my_sentiment_sensor)

        readout = await orchestrator.run_sensors("BTC/USDT")
        pressure_input = readout.to_pressure_input()
    """

    def __init__(self) -> None:
        self._sensors: Dict[SensorType, List[SensorFunction]] = {}
        self._last_readouts: Dict[str, SensorReadout] = {}

    def register(self, sensor_type: SensorType, func: SensorFunction) -> None:
        """Register a sensor function.

        Parameters
        ----------
        sensor_type:
            The type of sensor (determines priority and grouping).
        func:
            Async or sync function that takes a symbol and returns a SensorReading.
        """
        if sensor_type not in self._sensors:
            self._sensors[sensor_type] = []
        self._sensors[sensor_type].append(func)
        logger.info("Registered %s sensor: %s", sensor_type.value, func.__name__)

    def register_many(self, sensors: Dict[SensorType, SensorFunction]) -> None:
        """Register multiple sensor functions at once."""
        for sensor_type, func in sensors.items():
            self.register(sensor_type, func)

    async def run_sensors(
        self,
        symbol: str,
        sensor_types: Optional[List[SensorType]] = None,
        timeout: float = 30.0,
    ) -> SensorReadout:
        """Run all (or selected) sensors for a symbol.

        Parameters
        ----------
        symbol:
            Trading symbol to analyze.
        sensor_types:
            Specific sensor types to run. If None, runs all registered.
        timeout:
            Maximum seconds to wait for each sensor.

        Returns
        -------
        SensorReadout
            Aggregated sensor output.
        """
        types_to_run = sensor_types or list(self._sensors.keys())
        tasks = []

        for sensor_type in types_to_run:
            funcs = self._sensors.get(sensor_type, [])
            for func in funcs:
                tasks.append(self._run_single_sensor(func, symbol, sensor_type, timeout))

        # Run all sensors in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        readings = []
        for result in results:
            if isinstance(result, SensorReading):
                readings.append(result)
            elif isinstance(result, Exception):
                logger.warning("Sensor failed: %s", result)

        # Aggregate into readout
        readout = self._aggregate(symbol, readings)

        # Cache the result
        self._last_readouts[symbol] = readout

        return readout

    async def _run_single_sensor(
        self,
        func: SensorFunction,
        symbol: str,
        sensor_type: SensorType,
        timeout: float,
    ) -> SensorReading:
        """Run a single sensor with timeout and error handling."""
        try:
            if asyncio.iscoroutinefunction(func):
                reading = await asyncio.wait_for(func(symbol), timeout=timeout)
            else:
                reading = await asyncio.get_event_loop().run_in_executor(
                    None, func, symbol
                )
            return reading
        except asyncio.TimeoutError:
            logger.warning("Sensor %s timed out for %s", sensor_type.value, symbol)
            return SensorReading(
                sensor_type=sensor_type,
                symbol=symbol,
                signal_direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                details={"error": "timeout"},
                data_source="unavailable",
            )
        except Exception as e:
            logger.warning("Sensor %s failed for %s: %s", sensor_type.value, symbol, e)
            return SensorReading(
                sensor_type=sensor_type,
                symbol=symbol,
                signal_direction="NEUTRAL",
                confidence=0.0,
                strength=0.0,
                details={"error": str(e)},
                data_source="unavailable",
            )

    def _aggregate(self, symbol: str, readings: List[SensorReading]) -> SensorReadout:
        """Aggregate individual sensor readings into a composite readout.

        Uses confidence-weighted voting for direction, and
        takes the mean for confidence and strength.
        """
        if not readings:
            return SensorReadout(symbol=symbol, composite_direction="NEUTRAL")

        # Confidence-weighted direction vote
        bullish_weight = 0.0
        bearish_weight = 0.0
        total_confidence = 0.0
        total_strength = 0.0

        for r in readings:
            weight = r.confidence * r.strength
            if r.signal_direction == "BULLISH":
                bullish_weight += weight
            elif r.signal_direction == "BEARISH":
                bearish_weight += weight
            total_confidence += r.confidence
            total_strength += r.strength

        n = len(readings)
        avg_confidence = total_confidence / n if n > 0 else 0.0
        avg_strength = total_strength / n if n > 0 else 0.0

        # Determine composite direction
        if bullish_weight > bearish_weight * 1.5:
            composite_direction = "BULLISH"
        elif bearish_weight > bullish_weight * 1.5:
            composite_direction = "BEARISH"
        else:
            composite_direction = "NEUTRAL"

        return SensorReadout(
            symbol=symbol,
            readings=readings,
            composite_direction=composite_direction,
            composite_confidence=round(avg_confidence, 4),
            composite_strength=round(avg_strength, 4),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_last_readout(self, symbol: str) -> Optional[SensorReadout]:
        """Get the most recent readout for a symbol."""
        return self._last_readouts.get(symbol)

    @property
    def registered_sensor_types(self) -> List[SensorType]:
        """List of registered sensor types."""
        return list(self._sensors.keys())

    @property
    def total_sensor_count(self) -> int:
        """Total number of registered sensor functions."""
        return sum(len(funcs) for funcs in self._sensors.values())
