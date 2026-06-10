"""
Wyckoff Methodology Strategy Implementation
Based on Richard D. Wyckoff's principles for identifying accumulation and distribution phases.
Integrates with the existing backtesting framework.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class WyckoffPhase(Enum):
    """Wyckoff market phases"""
    ACCUMULATION_A = "ACCUMULATION_A"  # Stopping of prior downtrend
    ACCUMULATION_B = "ACCUMULATION_B"  # Building cause
    ACCUMULATION_C = "ACCUMULATION_C"  # Test for supply
    ACCUMULATION_D = "ACCUMULATION_D"  # Markup begins
    ACCUMULATION_E = "ACCUMULATION_E"  # Distribution begins
    
    DISTRIBUTION_A = "DISTRIBUTION_A"  # Stopping of prior uptrend
    DISTRIBUTION_B = "DISTRIBUTION_B"  # Building cause
    DISTRIBUTION_C = "DISTRIBUTION_C"  # Test for demand
    DISTRIBUTION_D = "DISTRIBUTION_D"  # Markdown begins
    DISTRIBUTION_E = "DISTRIBUTION_E"  # Complete distribution
    
    TRENDING = "TRENDING"  # Clear trend direction
    UNKNOWN = "UNKNOWN"


class WyckoffEvent(Enum):
    """Wyckoff chart events"""
    PS = "PS"              # Preliminary Support
    SC = "SC"              # Selling Climax
    AR = "AR"              # Automatic Rally
    ST = "ST"              # Secondary Test
    SPRING = "SPRING"      # Spring (test below support)
    SHAKEOUT = "SHAKEOUT"  # Terminal shakeout
    UPTHRUST = "UPTHRUST"  # Test above resistance
    BU = "BU"              # Back up (to previous resistance)
    SOS = "SOS"            # Sign of Strength
    LPS = "LPS"            # Last Point of Support
    LPSY = "LPSY"          # Last Point of Support Yesterday


@dataclass
class WyckoffStructure:
    """Wyckoff market structure analysis"""
    phase: WyckoffPhase
    confidence: float
    events: Dict[str, datetime]
    support_level: float
    resistance_level: float
    cause_measurement: float
    effect_projection: float
    supply_demand_balance: float  # Positive = demand, negative = supply
    vertical_count: int  # P&F box count
    horizontal_count: int  # P&F column count in range


@dataclass 
class WyckoffSignal:
    """Wyckoff trading signal"""
    action: str  # BUY, SELL, HOLD
    phase: WyckoffPhase
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    reason: str
    events_found: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class WyckoffIndicators:
    """
    Calculate Wyckoff-specific indicators and metrics.
    """
    
    @staticmethod
    def calculate_volume_trend(volume: pd.Series, lookback: int = 20) -> pd.Series:
        """Calculate volume trend as percentage change from moving average"""
        vol_ma = volume.rolling(lookback).mean()
        return ((volume - vol_ma) / vol_ma * 100)
    
    @staticmethod
    def calculate_price_position(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Calculate where close is within the high-low range (0-100%)
        Similar to Wyckoff's analysis of price position
        """
        return ((close - low) / (high - low + 1e-10)) * 100
    
    @staticmethod
    def calculate_spread(Open: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
        """Calculate price spread metrics"""
        return pd.DataFrame({
            'daily_range': high - low,
            'range_pct': (high - low) / close * 100,
            'upper_shadow': high - pd.concat([Open, close], axis=1).max(axis=1),
            'lower_shadow': pd.concat([Open, close], axis=1).min(axis=1) - low,
            'body': abs(close - Open),
            'body_pct': abs(close - Open) / (high - low + 1e-10) * 100
        })
    
    @staticmethod
    def identify_spring_or_shakeout(
        close: pd.Series,
        low: pd.Series,
        support_level: float,
        tolerance: float = 0.02,
        confirmation_bars: int = 2
    ) -> List[datetime]:
        """
        Identify spring or shakeout events.
        Spring: Price drops below support but closes back above.
        Shakeout: Similar but more violent, often on high volume.
        """
        springs = []
        for i in range(confirmation_bars, len(close)):
            # Check if low breached support
            if low.iloc[i] < support_level * (1 - tolerance):
                # Check if closed back above support
                if close.iloc[i] > support_level:
                    # Check for confirmation (higher close next bar)
                    if i + 1 < len(close) and close.iloc[i+1] > close.iloc[i]:
                        springs.append(close.index[i])
        return springs
    
    @staticmethod
    def identify_upthrust(
        close: pd.Series,
        high: pd.Series,
        resistance_level: float,
        tolerance: float = 0.02
    ) -> List[datetime]:
        """Identify upthrust events - price rises above resistance but closes below."""
        upthrusts = []
        for i in range(1, len(close)):
            # Check if high breached resistance
            if high.iloc[i] > resistance_level * (1 + tolerance):
                # Check if closed below resistance
                if close.iloc[i] < resistance_level:
                    upthrusts.append(close.index[i])
        return upthrusts
    
    @staticmethod
    def calculate_cause_measurement(
        low: pd.Series,
        high: pd.Series,
        box_size: float = 1.0,
        reversal: int = 3
    ) -> Tuple[int, int]:
        """
        Calculate Point & Figure-style cause measurement.
        Returns: (vertical_count, horizontal_count)
        
        Vertical count: Number of boxes in accumulation range
        Horizontal count: Number of columns in the range
        """
        # Simplified P&F counting
        range_high = high.max()
        range_low = low.min()
        
        vertical_count = int((range_high - range_low) / box_size)
        
        # Count columns (simplified - would need proper P&F algorithm)
        horizontal_count = 1  # Placeholder
        
        return vertical_count, horizontal_count
    
    @staticmethod
    def project_target_from_cause(
        cause_measurement: int,
        breakout_level: float,
        box_size: float = 1.0,
        reversal: int = 3
    ) -> float:
        """
        Project target using Wyckoff's Cause & Effect principle.
        Effect = Cause * 3 (typical multiplier)
        """
        effect_boxes = cause_measurement * 3
        return breakout_level + (effect_boxes * box_size)
    
    @staticmethod
    def analyze_supply_demand(
        close: pd.Series,
        volume: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        Calculate supply/demand balance.
        Positive = Demand (buying pressure)
        Negative = Supply (selling pressure)
        """
        price_change = close.pct_change()
        
        # Weighted by volume
        weighted_change = price_change * volume
        
        # Rolling supply/demand
        sd_balance = weighted_change.rolling(period).sum()
        
        return sd_balance
    
    @staticmethod
    def calculate_wyckoff_wave(
        close: pd.Series,
        volume: pd.Series,
        short_period: int = 5,
        long_period: int = 20
    ) -> pd.DataFrame:
        """
        Calculate Wyckoff Wave indicators.
        Compares price and volume trends.
        """
        # Price wave
        price_short = close.rolling(short_period).mean()
        price_long = close.rolling(long_period).mean()
        
        # Volume wave
        vol_short = volume.rolling(short_period).mean()
        vol_long = volume.rolling(long_period).mean()
        
        return pd.DataFrame({
            'price_wave': price_short - price_long,
            'volume_wave': vol_short - vol_long,
            'wave_ratio': (price_short / price_long) / (vol_short / vol_long + 1e-10)
        })


class WyckoffAnalyzer:
    """
    Comprehensive Wyckoff Analysis for identifying accumulation and distribution phases.
    """
    
    def __init__(
        self,
        box_size: float = 1.0,
        reversal: int = 3,
        accumulation_threshold: float = 0.3,
        distribution_threshold: float = 0.3
    ):
        """
        Initialize Wyckoff analyzer.
        
        Args:
            box_size: P&F box size for measurements
            reversal: P&F reversal amount
            accumulation_threshold: Threshold for accumulation signal
            distribution_threshold: Threshold for distribution signal
        """
        self.box_size = box_size
        self.reversal = reversal
        self.accumulation_threshold = accumulation_threshold
        self.distribution_threshold = distribution_threshold
        
        self.indicators = WyckoffIndicators()
    
    def analyze_phase(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        lookback: int = 100
    ) -> WyckoffStructure:
        """
        Analyze Wyckoff phase of the market.
        
        Returns:
            WyckoffStructure with phase analysis
        """
        data = high.tail(lookback) if len(high) > lookback else high
        close_data = close.tail(lookback) if len(close) > lookback else close
        low_data = low.tail(lookback) if len(low) > lookback else low
        vol_data = volume.tail(lookback) if len(volume) > lookback else volume
        
        # Calculate key metrics
        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()
        
        # Support and resistance
        support = low.rolling(20).min().iloc[-1]
        resistance = high.rolling(20).max().iloc[-1]
        
        # Calculate supply/demand balance
        sd_balance = self.indicators.analyze_supply_demand(close, volume).iloc[-1]
        
        # Calculate volume trend
        vol_trend = self.indicators.calculate_volume_trend(volume).iloc[-1]
        
        # Calculate price position
        price_position = self.indicators.calculate_price_position(high, low, close).iloc[-1]
        
        # Calculate cause measurement
        vertical_count, _ = self.indicators.calculate_cause_measurement(low, high, self.box_size)
        
        # Determine phase based on multiple factors
        phase, confidence = self._determine_phase(
            sd_balance, vol_trend, price_position, vertical_count
        )
        
        # Identify key events
        events = self._identify_events(high, low, close, volume, support, resistance)
        
        # Calculate effect projection
        breakout_level = resistance if phase in [WyckoffPhase.ACCUMULATION_D, WyckoffPhase.TRENDING] else support
        effect_projection = self.indicators.project_target_from_cause(
            vertical_count, breakout_level, self.box_size
        )
        
        return WyckoffStructure(
            phase=phase,
            confidence=confidence,
            events=events,
            support_level=support,
            resistance_level=resistance,
            cause_measurement=vertical_count * self.box_size,
            effect_projection=effect_projection,
            supply_demand_balance=sd_balance,
            vertical_count=vertical_count,
            horizontal_count=0
        )
    
    def _determine_phase(
        self,
        sd_balance: float,
        vol_trend: float,
        price_position: float,
        vertical_count: int
    ) -> Tuple[WyckoffPhase, float]:
        """Determine Wyckoff phase based on indicators."""
        score = 0
        confidence = 0.5
        
        # Accumulation signals
        if sd_balance > 0.1:  # Demand increasing
            score += 1
            confidence += 0.1
        elif sd_balance < -0.1:  # Supply increasing
            score -= 1
            confidence += 0.1
        
        if vol_trend > 20:  # Volume expanding
            score += 0.5
            confidence += 0.05
        elif vol_trend < -20:  # Volume contracting
            score -= 0.5
            confidence += 0.05
        
        if price_position > 70:  # Near highs
            if score > 0:
                score += 1
        elif price_position < 30:  # Near lows
            if score < 0:
                score += 1
        
        # Large cause suggests accumulation/distribution building
        if vertical_count > 50:
            confidence += 0.15
        
        # Determine phase
        if score >= 2:
            return WyckoffPhase.ACCUMULATION_D, min(0.95, confidence)
        elif score >= 1:
            return WyckoffPhase.ACCUMULATION_C, min(0.90, confidence)
        elif score >= 0.5:
            return WyckoffPhase.ACCUMULATION_B, min(0.85, confidence)
        elif score <= -2:
            return WyckoffPhase.DISTRIBUTION_D, min(0.95, confidence)
        elif score <= -1:
            return WyckoffPhase.DISTRIBUTION_C, min(0.90, confidence)
        elif score <= -0.5:
            return WyckoffPhase.DISTRIBUTION_B, min(0.85, confidence)
        else:
            return WyckoffPhase.TRENDING if abs(score) < 0.3 else WyckoffPhase.UNKNOWN, confidence
    
    def _identify_events(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        support: float,
        resistance: float
    ) -> Dict[str, datetime]:
        """Identify Wyckoff chart events."""
        events = {}
        
        # Find springs
        springs = self.indicators.identify_spring_or_shakeout(close, low, support)
        if springs:
            events['SPRING'] = springs[-1]
        
        # Find upthrusts
        upthrusts = self.indicators.identify_upthrust(close, high, resistance)
        if upthrusts:
            events['UPTHRUST'] = upthrusts[-1]
        
        # Find SOS (sign of strength)
        sos_bars = self._identify_sos(close, high, low, volume)
        if sos_bars:
            events['SOS'] = sos_bars[-1]
        
        # Find LPS (last point of support)
        lps_bars = self._identify_lps(close, low, volume)
        if lps_bars:
            events['LPS'] = lps_bars[-1]
        
        return events
    
    def _identify_sos(
        self,
        close: pd.Series,
        high: pd.Series,
        low: pd.Series,
        volume: pd.Series
    ) -> List[datetime]:
        """Identify Sign of Strength (SOS) - bullish breakout bars."""
        sos = []
        for i in range(1, len(close)):
            # Strong close near high on expanding volume
            if (close.iloc[i] > close.iloc[i-1] * 1.01 and
                close.iloc[i] > high.iloc[i] * 0.99 and
                volume.iloc[i] > volume.iloc[i-1] * 1.2):
                sos.append(close.index[i])
        return sos
    
    def _identify_lps(
        self,
        close: pd.Series,
        low: pd.Series,
        volume: pd.Series
    ) -> List[datetime]:
        """Identify Last Point of Support (LPS) - buying at support."""
        lps = []
        for i in range(1, len(close)):
            # Close near low but with reduced volume (absorption)
            if (close.iloc[i] > close.iloc[i-1] * 0.99 and
                close.iloc[i] < close.iloc[i-1] * 1.01 and
                volume.iloc[i] < volume.iloc[i-1] * 0.8):
                lps.append(close.index[i])
        return lps
    
    def generate_signal(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        current_price: float
    ) -> WyckoffSignal:
        """
        Generate Wyckoff-based trading signal.
        
        Args:
            high, low, close, price: Price data
            volume: Volume data
            current_price: Current market price
            
        Returns:
            WyckoffSignal with trade recommendation
        """
        structure = self.analyze_phase(high, low, close, volume)
        
        # Calculate stop loss and take profit
        stop_loss = structure.support_level * 0.98 if structure.phase in [
            WyckoffPhase.ACCUMULATION_C, WyckoffPhase.ACCUMULATION_D, WyckoffPhase.TRENDING
        ] else structure.resistance_level * 1.02
        
        # Project target using cause & effect
        if structure.phase in [WyckoffPhase.ACCUMULATION_C, WyckoffPhase.ACCUMULATION_D]:
            take_profit = structure.effect_projection
        elif structure.phase in [WyckoffPhase.DISTRIBUTION_C, WyckoffPhase.DISTRIBUTION_D]:
            take_profit = structure.support_level - (structure.resistance_level - structure.effect_projection)
        else:
            take_profit = current_price * 1.05
        
        # Calculate risk/reward
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Generate signal based on phase
        action = "HOLD"
        reason = f"Phase: {structure.phase.value}, Confidence: {structure.confidence:.1%}"
        
        if structure.phase == WyckoffPhase.ACCUMULATION_C and 'SPRING' in structure.events:
            action = "BUY"
            reason = f"Spring detected at {structure.events['SPRING']}, accumulation phase"
        elif structure.phase == WyckoffPhase.ACCUMULATION_D:
            action = "BUY"
            reason = f"MArkup phase, target: {take_profit:.2f}"
        elif structure.phase == WyckoffPhase.DISTRIBUTION_C and 'UPTHRUST' in structure.events:
            action = "SELL"
            reason = f"Upthrust detected at {structure.events['UPTHRUST']}, distribution phase"
        elif structure.phase == WyckoffPhase.DISTRIBUTION_D:
            action = "SELL"
            reason = f"Markdown phase, target: {take_profit:.2f}"
        elif structure.phase == WyckoffPhase.TRENDING:
            if structure.supply_demand_balance > 0:
                action = "BUY"
                reason = "Strong demand in uptrend"
            else:
                action = "SELL"
                reason = "Strong supply in downtrend"
        
        return WyckoffSignal(
            action=action,
            phase=structure.phase,
            confidence=structure.confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            reason=reason,
            events_found=list(structure.events.keys())
        )


class WyckoffStrategy:
    """
    Complete Wyckoff Trading Strategy with backtesting support.
    """
    
    def __init__(self, config: Dict = None):
        default_config = {
            'box_size': 1.0,
            'reversal': 3,
            'accumulation_threshold': 0.3,
            'distribution_threshold': 0.3,
            'min_confidence': 0.6,
            'min_rr_ratio': 1.5,
            'position_size': 0.1
        }
        self.config = {**default_config, **(config or {})}
        
        self.analyzer = WyckoffAnalyzer(
            box_size=self.config['box_size'],
            reversal=self.config['reversal'],
            accumulation_threshold=self.config['accumulation_threshold'],
            distribution_threshold=self.config['distribution_threshold']
        )
    
    def calculate(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        ticker: str = "UNKNOWN"
    ) -> WyckoffSignal:
        """
        Calculate Wyckoff signal for given price data.
        
        Args:
            high, low, close, volume: OHLCV data
            ticker: Asset ticker for reference
            
        Returns:
            WyckoffSignal with trade recommendation
        """
        if len(close) < 50:
            return WyckoffSignal(
                action="HOLD",
                phase=WyckoffPhase.UNKNOWN,
                confidence=0.0,
                entry_price=close.iloc[-1] if len(close) > 0 else 0,
                stop_loss=0,
                take_profit=0,
                risk_reward_ratio=0,
                reason="Insufficient data (need 50+ bars)"
            )
        
        current_price = close.iloc[-1]
        signal = self.analyzer.generate_signal(high, low, close, volume, current_price)
        
        # Apply minimum confidence filter
        if signal.confidence < self.config['min_confidence']:
            signal.action = "HOLD"
            signal.reason += f" - Confidence {signal.confidence:.1%} below threshold"
        
        # Apply minimum R/R filter
        if signal.risk_reward_ratio < self.config['min_rr_ratio']:
            if signal.action in ["BUY", "SELL"]:
                signal.reason += f" - R/R {signal.risk_reward_ratio:.2f} below minimum"
        
        return signal
    
    def get_strategy_info(self) -> Dict:
        """Get strategy information."""
        return {
            'name': 'Wyckoff Methodology',
            'type': 'Price Action / Volume Analysis',
            'phases': [p.value for p in WyckoffPhase],
            'config': self.config,
            'description': 'Richard Wyckoff accumulation/distribution analysis'
        }


# Convenience functions
def calculate_wyckoff_signal(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> WyckoffSignal:
    """Calculate Wyckoff signal (simple function interface)."""
    strategy = WyckoffStrategy()
    return strategy.calculate(high, low, close, volume)


# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=500, freq='D')
    
    # Create accumulation-like pattern
    base = 100
    phases = [
        (50, 0.005, 0.02),   # Accumulation
        (100, 0.01, 0.03),   # Markup
        (50, 0.005, 0.02),   # Distribution
        (100, 0.01, 0.03),   # Markdown
    ]
    
    prices = []
    for n, vol, drift in phases:
        returns = np.random.randn(n) * vol + drift
        prices.extend(base * np.cumprod(1 + returns))
        base = prices[-1]
    
    close = pd.Series(prices[:500], index=dates)
    high = close * (1 + np.random.rand(500) * 0.02)
    low = close * (1 - np.random.rand(500) * 0.02)
    volume = pd.Series(np.random.randint(1000000, 10000000, 500), index=dates)
    
    # Test Wyckoff strategy
    strategy = WyckoffStrategy()
    
    print("Wyckoff Strategy Test")
    print("=" * 50)
    
    info = strategy.get_strategy_info()
    print(f"Strategy: {info['name']}")
    print(f"Type: {info['type']}")
    
    signal = strategy.calculate(high, low, close, volume)
    print(f"\nCurrent Signal:")
    print(f"  Action: {signal.action}")
    print(f"  Phase: {signal.phase.value}")
    print(f"  Confidence: {signal.confidence:.1%}")
    print(f"  Entry: {signal.entry_price:.2f}")
    print(f"  Stop: {signal.stop_loss:.2f}")
    print(f"  Target: {signal.take_profit:.2f}")
    print(f"  R/R: {signal.risk_reward_ratio:.2f}")
    print(f"  Events: {signal.events_found}")
    print(f"  Reason: {signal.reason}")
