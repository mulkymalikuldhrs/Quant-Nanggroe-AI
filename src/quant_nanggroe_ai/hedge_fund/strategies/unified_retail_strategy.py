"""
Unified Retail Strategy System - All-in-One Trading Strategy

Integrates:
1. Wyckoff Methodology
2. ICT (Inner Circle Trader)
3. SMC (Smart Money Concepts)
4. SNR (Support & Resistance)
5. MSNR (Multi-SNR)
6. Fibonacci Retracements & Extensions
7. Volume Profile
8. Order Flow & Auction Theory

This is the ULTIMATE retail trading system!
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class StrategyType(Enum):
    WYCKOFF = "wyckoff"
    ICT = "ict"
    SMC = "smc"
    SNR = "snr"
    MSRN = "msnr"
    FIBONACCI = "fibonacci"
    VOLUME_PROFILE = "volume_profile"
    ORDER_FLOW = "order_flow"
    UNIFED = "unified"


@dataclass
class Level:
    price: float
    level_type: str  # 'support', 'resistance', 'order_block', 'fvg', ' liquidity'
    strength: float  # 0-1
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class ICTSignal:
    signal_type: SignalType
    order_block: Optional[Level]
    fvg_zones: List[Level]
    liquidity_levels: List[Level]
    premium_discount: str  # 'premium', 'discount', 'fair_value'
    session: str  # 'london', 'ny', 'asian'
    market_structure: str  # 'bullish', 'bearish', 'neutral'
    confidence: float
    entry_zone: Tuple[float, float]
    stop_loss: float
    take_profit: Tuple[float, ...]


@dataclass
class SMCSignal:
    signal_type: SignalType
    order_blocks: List[Level]
    fair_value_gaps: List[Level]
    breaker_blocks: List[Level]
    liquidity_sweeps: List[Level]
    equal_highs_lows: List[Level]
    change_of_character: bool
    market_structure_shift: bool
    confidence: float
    entry_zone: Tuple[float, float]
    stop_loss: float
    take_profit: Tuple[float, ...]


@dataclass
class FibonacciSignal:
    signal_type: SignalType
    retracement_level: float  # 0.236, 0.382, 0.500, 0.618, 0.786
    extension_level: float  # 1.272, 1.618, 2.000, 2.618
    golden_pocket: bool
    confluence_score: float
    entry_zone: Tuple[float, float]
    stop_loss: float
    take_profit: Tuple[float, ...]


@dataclass
class UnifiedSignal:
    symbol: str
    timestamp: datetime
    direction: SignalType
    confidence: float
    score: int  # 0-100

    # Component signals
    wyckoff_signal: Optional[Any] = None
    ict_signal: Optional[ICTSignal] = None
    smc_signal: Optional[SMCSignal] = None
    fibonacci_signal: Optional[FibonacciSignal] = None

    # Key levels
    entry_zone: Tuple[float, float] = (0, 0)
    stop_loss: float = 0
    take_profit_levels: Tuple[float, ...] = ()

    # Analysis details
    trend: TrendDirection = TrendDirection.NEUTRAL
    volatility: str = "normal"
    session: str = "unknown"

    # Metadata
    reasons: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


# ============ NEW DATACLASSES FOR MISSING SMC/ICT CONCEPTS ============

@dataclass
class OTESignal:
    """Optimal Trade Entry (OTE) - ICT Concept"""
    zone: str  # 'discount', 'premium', 'fair_value'
    ote_level: float
    current_position_pct: float  # 0-100 dalam range
    distance_to_ote: float
    confidence: float
    entry_zone: Tuple[float, float]
    signal_type: SignalType


@dataclass
class KillZoneSignal:
    """ICT Kill Zones - High probability trading sessions"""
    current_zone: str
    zone_active: bool
    session_start: datetime
    session_end: datetime
    liquidity_window: bool
    recommended_session: str
    kills_found: List[Dict]


@dataclass
class MarketProfileSignal:
    """Market Profile / TPO Analysis"""
    poc: float  # Point of Control
    vah: float  # Value Area High (70%)
    val: float  # Value Area Low (70%)
    tpo_count: int
    profile_shape: str  # 'normal', 'b_shape', 'p_shape', 'bipolar'
    auction_type: str  # 'balanced', 'unfinished', 'tail'
    initial_balance: Tuple[float, float]
    extended_balance: Tuple[float, float]
    vwap: float


@dataclass
class VolumeDeltaSignal:
    """Volume Delta / Order Flow Analysis"""
    delta: float  # Buy volume - Sell volume
    delta_ratio: float  # Delta as % of total volume
    buying_pressure: float
    selling_pressure: float
    cumulative_delta: float
    delta_trend: str  # 'accumulating', 'distributing', 'neutral'
    order_flow_quality: str  # 'strong', 'weak', 'neutral'
    bid_ask_imbalance: float


@dataclass
class AbsorptionSignal:
    """Absorption / Rejection Detection"""
    absorption_detected: bool
    absorption_zone: float
    rejection_count: int
    rejection_strength: float
    failed_break_attempts: int
    time_at_level: int  # Candles spent at level
    signal_type: SignalType
    confidence: float


@dataclass
class DisplacementSignal:
    """Displacement - Strong Momentum Break"""
    displacement_detected: bool
    displacement_candle_index: int
    displacement_size: float  # % move
    displaced_level: float
    target_after_displacement: float
    pullback_zone: float
    signal_type: SignalType
    confidence: float


@dataclass
class MitigationCounter:
    """Order Block Mitigation Counter"""
    order_block: Level
    mitigation_count: int
    is_fully_mitigated: bool
    remaining_strength: float
    original_strength: float
    last_mitigation_time: datetime
    time_since_creation: int  # Candles


@dataclass
class MitigationSignal:
    """Signal based on mitigation analysis"""
    active_ob_count: int
    partially_mitigated_count: int
    fully_mitigated_count: int
    best_buy_ob: Optional[MitigationCounter]
    best_sell_ob: Optional[MitigationCounter]
    lowest_mitigation_ob: Level
    signal_type: SignalType
    confidence: float


@dataclass
class LiquidityVoidSignal:
    """Liquidity Void / Imbalance Detection"""
    voids: List[Dict]  # Price ranges with no volume
    void_depth: float
    void_width: int  # Candles
    fair_value_gap_count: int
    unfilled_gaps: List[Level]
    gap_quality: str  # 'strong', 'weak'
    signal_type: SignalType


@dataclass
class OpeningRangeSignal:
    """Opening Range Analysis"""
    or_high: float
    or_low: float
    or_range: float
    or_mid: float
    current_price_vs_or: str  # 'above', 'below', 'inside'
    break_of_or: bool
    or_test: bool
    failed_break_count: int
    session_type: str  # 'london', 'ny', 'asian'
    signal_type: SignalType


@dataclass
class DivergenceSignal:
    """Divergence Detection (Price vs RSI/MACD)"""
    rsi_divergence: Optional[Dict]
    macd_divergence: Optional[Dict]
    volume_divergence: Optional[Dict]
    divergence_type: str  # 'regular', 'hidden', 'none'
    divergence_direction: str  # 'bullish', 'bearish', 'none'
    divergence_strength: float
    confidence: float
    signal_type: SignalType


@dataclass
class CVDSignal:
    """Cumulative Volume Delta"""
    cumulative_delta: float
    delta_per_candle: List[float]
    cvd_trend: str  # 'rising', 'falling', 'flat'
    cvd_extremes: Tuple[float, float]  # Max/min CVD
    zero_line_crosses: int
    signal_type: SignalType
    confidence: float


@dataclass
class TrendLineBreakSignal:
    """Trend Line Break Detection"""
    trend_lines: List[Dict]
    active_trend: str  # 'uptrend', 'downtrend', 'sideways'
    broken_line: Optional[Dict]
    break_quality: str  # 'strong', 'weak'
    retest_zone: float
    time_since_break: int  # Candles
    signal_type: SignalType
    confidence: float


# ============ MISSING SMC/ICT ANALYZERS ============

class OTEAnalyzer:
    """Optimal Trade Entry Analyzer - ICT Concept"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> OTESignal:
        """Calculate OTE zone and position"""
        
        if len(close) < 20:
            return OTESignal(
                zone='unknown',
                ote_level=close.iloc[-1],
                current_position_pct=50,
                distance_to_ote=0,
                confidence=0,
                entry_zone=(close.iloc[-1], close.iloc[-1]),
                signal_type=SignalType.HOLD
            )
        
        # Calculate range
        highest = high.rolling(20).max().iloc[-1]
        lowest = low.rolling(20).min().iloc[-1]
        current = close.iloc[-1]
        range_size = highest - lowest
        
        if range_size == 0:
            return OTESignal(
                zone='unknown',
                ote_level=current,
                current_position_pct=50,
                distance_to_ote=0,
                confidence=0,
                entry_zone=(current, current),
                signal_type=SignalType.HOLD
            )
        
        # Current position dalam range (0-100%)
        current_position = ((current - lowest) / range_size) * 100
        
        # OTE Level (50% of range)
        ote_level = lowest + (range_size * 0.5)
        distance_to_ote = abs(current - ote_level) / current * 100
        
        # Determine zone
        if current_position < 40:
            zone = 'deep_discount'
            signal = SignalType.BUY
            confidence = 0.8
        elif current_position < 50:
            zone = 'discount'
            signal = SignalType.BUY
            confidence = 0.7
        elif current_position > 60:
            zone = 'deep_premium'
            signal = SignalType.SELL
            confidence = 0.8
        elif current_position > 50:
            zone = 'premium'
            signal = SignalType.SELL
            confidence = 0.7
        else:
            zone = 'fair_value'
            signal = SignalType.HOLD
            confidence = 0.5
        
        # Entry zone (OTE level dengan buffer)
        entry_zone = (ote_level * 0.999, ote_level * 1.001)
        
        return OTESignal(
            zone=zone,
            ote_level=ote_level,
            current_position_pct=current_position,
            distance_to_ote=distance_to_ote,
            confidence=confidence,
            entry_zone=entry_zone,
            signal_type=signal
        )


class KillZoneAnalyzer:
    """ICT Kill Zones Analyzer"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> KillZoneSignal:
        """Analyze kill zones and sessions"""
        
        utc_hour = datetime.utcnow().hour
        
        # Define kill zones
        zones = {
            'asian': {'start': 0, 'end': 8, 'name': 'Asian Session'},
            'london_kill': {'start': 8, 'end': 11, 'name': 'London Kill Zone'},
            'london': {'start': 8, 'end': 13, 'name': 'London Session'},
            'overlap': {'start': 13, 'end': 14, 'name': 'London/NY Overlap'},
            'ny_kill': {'start': 13, 'end': 16, 'name': 'NY Kill Zone'},
            'ny': {'start': 13, 'end': 17, 'name': 'NY Session'},
            'american': {'start': 17, 'end': 22, 'name': 'American Session'},
        }
        
        # Find current zone
        current_zone = 'unknown'
        for zone_name, config in zones.items():
            if config['start'] <= utc_hour < config['end']:
                current_zone = zone_name
                break
        
        zone_active = current_zone in ['london_kill', 'ny_kill', 'london', 'ny']
        
        # Liquidity window check (high volatility periods)
        liquidity_window = current_zone in ['london_kill', 'ny_kill', 'overlap']
        
        # Recommended sessions based on volatility
        recommended = 'ny_kill' if 13 <= utc_hour < 16 else 'london_kill' if 8 <= utc_hour < 11 else 'ny'
        
        # Find potential kill zones in data
        kills = []
        if len(close) > 50:
            # Look for high volatility moves
            returns = close.pct_change().abs()
            vol_rolling = returns.rolling(10).mean()
            vol_threshold = vol_rolling.mean() * 2
            
            for i in range(20, len(close)):
                if returns.iloc[i] > vol_threshold:
                    kills.append({
                        'candle': i,
                        'return': float(returns.iloc[i]),
                        'type': 'potential_kill'
                    })
        
        return KillZoneSignal(
            current_zone=current_zone,
            zone_active=zone_active,
            session_start=datetime.utcnow(),
            session_end=datetime.utcnow(),
            liquidity_window=liquidity_window,
            recommended_session=recommended,
            kills_found=kills[:5]
        )


class MarketProfileAnalyzer:
    """Market Profile / TPO Analyzer"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> MarketProfileSignal:
        """Calculate Market Profile metrics"""
        
        if len(close) < 50:
            return MarketProfileSignal(
                poc=close.iloc[-1],
                vah=close.iloc[-1],
                val=close.iloc[-1],
                tpo_count=0,
                profile_shape='normal',
                auction_type='unfinished',
                initial_balance=(close.iloc[-1], close.iloc[-1]),
                extended_balance=(close.iloc[-1], close.iloc[-1]),
                vwap=close.iloc[-1]
            )
        
        # Calculate price bins
        price_range = high.max() - low.min()
        if price_range == 0:
            return MarketProfileSignal(
                poc=close.iloc[-1],
                vah=close.iloc[-1],
                val=close.iloc[-1],
                tpo_count=0,
                profile_shape='normal',
                auction_type='unfinished',
                initial_balance=(close.iloc[-1], close.iloc[-1]),
                extended_balance=(close.iloc[-1], close.iloc[-1]),
                vwap=close.iloc[-1]
            )
        
        num_bins = min(50, int(price_range / (price_range / 100)))
        bin_size = price_range / num_bins
        
        # Create bins
        bins = np.arange(low.min(), high.max(), bin_size)
        vol_per_bin = np.zeros(len(bins))
        
        for i in range(len(close)):
            bin_idx = int((close.iloc[i] - low.min()) / bin_size)
            if 0 <= bin_idx < len(bins):
                vol_per_bin[bin_idx] += volume.iloc[i] if i < len(volume) else 1
        
        # Find POC
        poc_idx = np.argmax(vol_per_bin)
        poc = bins[poc_idx]
        
        # Calculate Value Area (70%)
        total_vol = np.sum(vol_per_bin)
        target_vol = total_vol * 0.70
        cumsum = np.cumsum(vol_per_bin)
        
        vah_idx = min(len(bins) - 1, max(0, int((cumsum[poc_idx] + target_vol / 2).clip(0, total_vol) / bin_size)))
        val_idx = min(len(bins) - 1, max(0, int((cumsum[poc_idx] - target_vol / 2).clip(0, total_vol) / bin_size)))
        
        vah = bins[vah_idx]
        val = bins[val_idx]
        
        # VWAP
        vwap = (close * (volume if i < len(volume) else 1)).sum() / volume.sum() if len(volume) > 0 else close.mean()
        
        # Initial Balance (first hour)
        first_hour = min(60, len(close) // 4)
        if first_hour > 0:
            ib_high = high.iloc[:first_hour].max()
            ib_low = low.iloc[:first_hour].min()
            initial_balance = (ib_high, ib_low)
        else:
            initial_balance = (close.iloc[-1], close.iloc[-1])
        
        # Extended Balance
        extended_balance = (high.max(), low.min())
        
        # Profile Shape
        left_tail = np.sum(vol_per_bin[:poc_idx])
        right_tail = np.sum(vol_per_bin[poc_idx + 1:])
        
        if left_tail > right_tail * 1.5:
            profile_shape = 'b_shape'  # Distribution
        elif right_tail > left_tail * 1.5:
            profile_shape = 'p_shape'  # Accumulation
        else:
            profile_shape = 'normal'
        
        # Auction Type
        if abs(close.iloc[-1] - poc) < bin_size:
            auction_type = 'balanced'
        elif close.iloc[-1] > vah:
            auction_type = 'tail'  # Rejected high
        elif close.iloc[-1] < val:
            auction_type = 'tail'  # Rejected low
        else:
            auction_type = 'unfinished'
        
        return MarketProfileSignal(
            poc=float(poc),
            vah=float(vah),
            val=float(val),
            tpo_count=num_bins,
            profile_shape=profile_shape,
            auction_type=auction_type,
            initial_balance=(float(ib_high), float(ib_low)),
            extended_balance=(float(high.max()), float(low.min())),
            vwap=float(vwap)
        )


class VolumeDeltaAnalyzer:
    """Volume Delta / Order Flow Analyzer"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> VolumeDeltaSignal:
        """Calculate volume delta metrics"""
        
        if len(close) < 10:
            return VolumeDeltaSignal(
                delta=0,
                delta_ratio=0,
                buying_pressure=50,
                selling_pressure=50,
                cumulative_delta=0,
                delta_trend='neutral',
                order_flow_quality='neutral',
                bid_ask_imbalance=0
            )
        
        # Calculate delta based on candle characteristics
        deltas = []
        for i in range(len(close)):
            body = abs(close.iloc[i] - (close.iloc[i-1] if i > 0 else close.iloc[i]))
            range_ = high.iloc[i] - low.iloc[i] if high.iloc[i] > low.iloc[i] else 1
            
            # Up candle = buying pressure
            if close.iloc[i] > (close.iloc[i-1] if i > 0 else close.iloc[i]):
                delta = body / range_ * volume.iloc[i] if i < len(volume) else body
            else:
                delta = -body / range_ * volume.iloc[i] if i < len(volume) else -body
            
            deltas.append(delta)
        
        deltas = np.array(deltas)
        total_volume = np.abs(deltas).sum()
        
        if total_volume == 0:
            return VolumeDeltaSignal(
                delta=0,
                delta_ratio=0,
                buying_pressure=50,
                selling_pressure=50,
                cumulative_delta=0,
                delta_trend='neutral',
                order_flow_quality='neutral',
                bid_ask_imbalance=0
            )
        
        delta = deltas[-1]
        delta_ratio = delta / total_volume * 100
        buying_pressure = np.sum(deltas[deltas > 0]) / total_volume * 100
        selling_pressure = np.sum(deltas[deltas < 0]) / total_volume * 100
        cumulative_delta = np.cumsum(deltas)[-1]
        
        # Delta trend
        if len(deltas) > 10:
            recent = deltas[-10:]
            if np.mean(recent) > 0:
                delta_trend = 'accumulating'
            elif np.mean(recent) < 0:
                delta_trend = 'distributing'
            else:
                delta_trend = 'neutral'
        else:
            delta_trend = 'neutral'
        
        # Order flow quality
        if buying_pressure > 65:
            order_flow_quality = 'strong'
        elif buying_pressure < 35:
            order_flow_quality = 'weak'
        else:
            order_flow_quality = 'neutral'
        
        # Bid/Ask imbalance
        bid_ask_imbalance = (buying_pressure - selling_pressure) / 100
        
        return VolumeDeltaSignal(
            delta=float(delta),
            delta_ratio=float(delta_ratio),
            buying_pressure=float(buying_pressure),
            selling_pressure=float(selling_pressure),
            cumulative_delta=float(cumulative_delta),
            delta_trend=delta_trend,
            order_flow_quality=order_flow_quality,
            bid_ask_imbalance=float(bid_ask_imbalance)
        )


class AbsorptionAnalyzer:
    """Absorption / Rejection Detection"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> AbsorptionSignal:
        """Detect absorption patterns at key levels"""
        
        if len(close) < 50:
            return AbsorptionSignal(
                absorption_detected=False,
                absorption_zone=close.iloc[-1],
                rejection_count=0,
                rejection_strength=0,
                failed_break_attempts=0,
                time_at_level=0,
                signal_type=SignalType.HOLD,
                confidence=0
            )
        
        # Find swing high/low as potential absorption zones
        swing_highs = []
        swing_lows = []
        
        for i in range(10, len(high) - 5):
            if high.iloc[i] >= high.iloc[i-5:i].max() and high.iloc[i] >= high.iloc[i+1:i+6].max():
                swing_highs.append((i, high.iloc[i]))
        
        for i in range(10, len(low) - 5):
            if low.iloc[i] <= low.iloc[i-5:i].min() and low.iloc[i] <= low.iloc[i+1:i+6].min():
                swing_lows.append((i, low.iloc[i]))
        
        # Check recent swing for absorption
        absorption_detected = False
        absorption_zone = 0
        rejection_count = 0
        time_at_level = 0
        
        if swing_highs:
            last_high = swing_highs[-1]
            idx, price = last_high
            
            # Check for rejection candles at this level
            for i in range(idx, min(idx + 20, len(close))):
                # Rejection: candle with long wick
                wick_top = high.iloc[i] - max(close.iloc[i], open_ := close.iloc[i-1])
                wick_bottom = min(close.iloc[i], open_) - low.iloc[i]
                body = abs(close.iloc[i] - open_)
                
                if wick_top > body * 2:  # Long upper wick = rejection up
                    rejection_count += 1
                    absorption_detected = True
            
            time_at_level = min(20, len(close) - idx)
        
        if swing_lows:
            last_low = swing_lows[-1]
            idx, price = last_low
            
            for i in range(idx, min(idx + 20, len(close))):
                open_ = close.iloc[i-1]
                wick_bottom = min(close.iloc[i], open_) - low.iloc[i]
                body = abs(close.iloc[i] - open_)
                
                if wick_bottom > body * 2:  # Long lower wick = rejection down
                    rejection_count += 1
                    absorption_detected = True
            
            time_at_level = min(20, len(close) - idx)
        
        # Failed break attempts
        failed_break_attempts = 0
        for i in range(20, len(close)):
            if i > 0 and i + 1 < len(close):
                prev_direction = 1 if close.iloc[i] > close.iloc[i-1] else -1
                next_direction = 1 if close.iloc[i+1] > close.iloc[i] else -1
                if prev_direction != next_direction:
                    failed_break_attempts += 1
        
        # Signal determination
        if absorption_detected and rejection_count >= 3:
            signal = SignalType.HOLD  # Wait for confirmation
            confidence = 0.7
            if swing_highs:
                absorption_zone = swing_highs[-1][1]
        elif absorption_detected:
            signal = SignalType.HOLD
            confidence = 0.5
            if swing_highs:
                absorption_zone = swing_highs[-1][1]
        else:
            signal = SignalType.HOLD
            confidence = 0.3
            absorption_zone = close.iloc[-1]
        
        rejection_strength = min(1, rejection_count / 5)
        
        return AbsorptionSignal(
            absorption_detected=absorption_detected,
            absorption_zone=absorption_zone,
            rejection_count=rejection_count,
            rejection_strength=rejection_strength,
            failed_break_attempts=failed_break_attempts,
            time_at_level=time_at_level,
            signal_type=signal,
            confidence=confidence
        )


class DisplacementAnalyzer:
    """Displacement Detection - Strong Momentum Moves"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> DisplacementSignal:
        """Detect displacement candles and analyze pullback targets"""
        
        if len(close) < 20:
            return DisplacementSignal(
                displacement_detected=False,
                displacement_candle_index=0,
                displacement_size=0,
                displaced_level=0,
                target_after_displacement=0,
                pullback_zone=0,
                signal_type=SignalType.HOLD,
                confidence=0
            )
        
        # Find displacement candles (large moves)
        returns = close.pct_change().abs()
        vol_rolling = returns.rolling(10).mean()
        threshold = vol_rolling.iloc[-1] * 2
        
        displacement_candle_idx = 0
        displacement_size = 0
        
        for i in range(-20, 0):
            if abs(returns.iloc[i]) > threshold:
                displacement_candle_idx = i
                displacement_size = abs(returns.iloc[i]) * 100
                break
        
        if displacement_candle_idx == 0:
            return DisplacementSignal(
                displacement_detected=False,
                displacement_candle_index=0,
                displacement_size=0,
                displaced_level=0,
                target_after_displacement=0,
                pullback_zone=0,
                signal_type=SignalType.HOLD,
                confidence=0
            )
        
        # Calculate displaced level
        if close.iloc[displacement_candle_idx] > close.iloc[displacement_candle_idx - 1]:
            # Bullish displacement
            displaced_level = low.iloc[displacement_candle_idx]
            pullback_zone = displaced_level * 1.001  # 0.1% pullback
            target_after_displacement = high.iloc[displacement_candle_idx] * 1.02
            signal = SignalType.BUY
        else:
            # Bearish displacement
            displaced_level = high.iloc[displacement_candle_idx]
            pullback_zone = displaced_level * 0.999  # 0.1% pullback
            target_after_displacement = low.iloc[displacement_candle_idx] * 0.98
            signal = SignalType.SELL
        
        confidence = min(0.85, 0.5 + displacement_size / 10)
        
        return DisplacementSignal(
            displacement_detected=True,
            displacement_candle_index=displacement_candle_idx,
            displacement_size=displacement_size,
            displaced_level=float(displaced_level),
            target_after_displacement=float(target_after_displacement),
            pullback_zone=float(pullback_zone),
            signal_type=signal,
            confidence=confidence
        )


class MitigationAnalyzer:
    """Order Block Mitigation Counter"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> MitigationSignal:
        """Analyze order block mitigation status"""
        
        # Get order blocks from SMC analyzer logic
        blocks = []
        open_est = close.shift(1).fillna(close)
        
        for i in range(5, len(close)):
            if close.iloc[i-1] < open_est.iloc[i-1]:  # Bearish
                if high.iloc[i] > high.iloc[i-3] and low.iloc[i] < low.iloc[i-3]:
                    blocks.append({
                        'price': close.iloc[i-1],
                        'type': 'bullish',
                        'created_at': i,
                        'mitigated': False,
                        'mitigation_count': 0
                    })
            if close.iloc[i-1] > open_est.iloc[i-1]:  # Bullish
                if high.iloc[i] > high.iloc[i-3] and low.iloc[i] < low.iloc[i-3]:
                    blocks.append({
                        'price': close.iloc[i-1],
                        'type': 'bearish',
                        'created_at': i,
                        'mitigated': False,
                        'mitigation_count': 0
                    })
        
        # Check mitigation for each block
        active_count = 0
        partial_count = 0
        full_count = 0
        best_buy = None
        best_sell = None
        
        for block in blocks:
            idx = block['created_at']
            if block['type'] == 'bullish':
                # Check if price returned to OB
                for i in range(idx, len(close)):
                    if close.iloc[i] <= block['price']:
                        block['mitigated'] = True
                        block['mitigation_count'] += 1
            else:
                for i in range(idx, len(close)):
                    if close.iloc[i] >= block['price']:
                        block['mitigated'] = True
                        block['mitigation_count'] += 1
            
            # Count status
            if block['mitigation_count'] == 0:
                active_count += 1
                if block['type'] == 'bullish' and (best_buy is None or block['mitigation_count'] < best_buy.mitigation_count):
                    best_buy = MitigationCounter(
                        order_block=Level(
                            price=block['price'],
                            level_type='ob_bullish',
                            strength=0.7,
                            timestamp=datetime.now()
                        ),
                        mitigation_count=0,
                        is_fully_mitigated=False,
                        remaining_strength=0.7,
                        original_strength=0.7,
                        last_mitigation_time=datetime.now(),
                        time_since_creation=len(close) - idx
                    )
            elif block['mitigation_count'] < 3:
                partial_count += 1
            else:
                full_count += 1
        
        # Determine signal
        if active_count > 0 and best_buy:
            signal = SignalType.BUY
            confidence = min(0.8, 0.5 + active_count * 0.1)
        elif active_count > 0 and best_sell:
            signal = SignalType.SELL
            confidence = min(0.8, 0.5 + active_count * 0.1)
        else:
            signal = SignalType.HOLD
            confidence = 0.5
        
        # Lowest mitigation OB (best opportunity)
        lowest_ob = Level(
            price=blocks[0]['price'] if blocks else close.iloc[-1],
            level_type='ob',
            strength=0.5,
            timestamp=datetime.now()
        ) if blocks else None
        
        return MitigationSignal(
            active_ob_count=active_count,
            partially_mitigated_count=partial_count,
            fully_mitigated_count=full_count,
            best_buy_ob=best_buy,
            best_sell_ob=best_sell,
            lowest_mitigation_ob=lowest_ob,
            signal_type=signal,
            confidence=confidence
        )


class LiquidityVoidAnalyzer:
    """Liquidity Void / Imbalance Detection"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> LiquidityVoidSignal:
        """Find liquidity voids and unfilled gaps"""
        
        voids = []
        unfilled_fvgs = []
        
        if len(close) < 10:
            return LiquidityVoidSignal(
                voids=[],
                void_depth=0,
                void_width=0,
                fair_value_gap_count=0,
                unfilled_gaps=[],
                gap_quality='weak',
                signal_type=SignalType.HOLD
            )
        
        # Find FVGs (Fair Value Gaps)
        fvg_count = 0
        for i in range(2, len(close)):
            # Bullish FVG
            if low.iloc[i] > high.iloc[i-2]:
                void_depth = (low.iloc[i] - high.iloc[i-2]) / high.iloc[i-2]
                voids.append({
                    'type': 'fvg_bullish',
                    'start': float(high.iloc[i-2]),
                    'end': float(low.iloc[i]),
                    'depth': float(void_depth),
                    'filled': False
                })
                fvg_count += 1
            
            # Bearish FVG
            if high.iloc[i] < low.iloc[i-2]:
                void_depth = (low.iloc[i-2] - high.iloc[i]) / low.iloc[i-2]
                voids.append({
                    'type': 'fvg_bearish',
                    'start': float(low.iloc[i-2]),
                    'end': float(high.iloc[i]),
                    'depth': float(void_depth),
                    'filled': False
                })
                fvg_count += 1
        
        # Check which gaps are still unfilled
        for void in voids:
            void_start = void['start']
            void_end = void['end']
            
            if void['type'] == 'fvg_bullish':
                # Check if price filled the gap
                for i in range(-20, 0):
                    if close.iloc[i] <= void_start:
                        void['filled'] = True
                        break
            else:
                for i in range(-20, 0):
                    if close.iloc[i] >= void_start:
                        void['filled'] = True
                        break
        
        # Unfilled gaps
        unfilled = [v for v in voids if not v['filled']]
        unfilled_gaps = [
            Level(
                price=(v['start'] + v['end']) / 2,
                level_type=v['type'],
                strength=min(1, v['depth'] * 100),
                timestamp=datetime.now()
            )
            for v in unfilled[:5]
        ]
        
        # Gap quality
        if unfilled:
            avg_depth = np.mean([v['depth'] for v in unfilled])
            if avg_depth > 0.005:
                gap_quality = 'strong'
            else:
                gap_quality = 'weak'
        else:
            gap_quality = 'weak'
        
        # Signal
        if len(unfilled) > 3:
            signal = SignalType.HOLD  # Wait for fill
            confidence = 0.6
        elif len(unfilled) > 0:
            signal = SignalType.HOLD
            confidence = 0.4
        else:
            signal = SignalType.HOLD
            confidence = 0.3
        
        return LiquidityVoidSignal(
            voids=voids[:10],
            void_depth=float(np.mean([v['depth'] for v in voids])) if voids else 0,
            void_width=0,
            fair_value_gap_count=fvg_count,
            unfilled_gaps=unfilled_gaps,
            gap_quality=gap_quality,
            signal_type=signal
        )


class OpeningRangeAnalyzer:
    """Opening Range Analysis"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> OpeningRangeSignal:
        """Analyze opening range breakouts/failures"""
        
        if len(close) < 60:
            return OpeningRangeSignal(
                or_high=close.iloc[-1],
                or_low=close.iloc[-1],
                or_range=0,
                or_mid=close.iloc[-1],
                current_price_vs_or='inside',
                break_of_or=False,
                or_test=False,
                failed_break_count=0,
                session_type='unknown',
                signal_type=SignalType.HOLD
            )
        
        # Determine session based on UTC hour
        utc_hour = datetime.utcnow().hour
        if 0 <= utc_hour < 8:
            session_type = 'asian'
        elif 8 <= utc_hour < 13:
            session_type = 'london'
        else:
            session_type = 'ny'
        
        # First hour data
        first_hour = min(60, len(close) // 4)
        if first_hour < 5:
            return OpeningRangeSignal(
                or_high=close.iloc[-1],
                or_low=close.iloc[-1],
                or_range=0,
                or_mid=close.iloc[-1],
                current_price_vs_or='inside',
                break_of_or=False,
                or_test=False,
                failed_break_count=0,
                session_type=session_type,
                signal_type=SignalType.HOLD
            )
        
        or_high = high.iloc[:first_hour].max()
        or_low = low.iloc[:first_hour].min()
        or_range = or_high - or_low
        or_mid = (or_high + or_low) / 2
        
        current_price = close.iloc[-1]
        
        # Price vs OR
        if current_price > or_high:
            current_price_vs_or = 'above'
        elif current_price < or_low:
            current_price_vs_or = 'below'
        else:
            current_price_vs_or = 'inside'
        
        # Break of OR
        break_of_or = current_price_vs_or in ['above', 'below']
        
        # OR Test (retest of broken OR)
        or_test = False
        failed_break_count = 0
        
        for i in range(first_hour, len(close)):
            # Check for failures
            if current_price_vs_or == 'above':
                if close.iloc[i] < or_high:
                    failed_break_count += 1
                if close.iloc[i] > or_high and close.iloc[i-1] < or_high:
                    or_test = True
            elif current_price_vs_or == 'below':
                if close.iloc[i] > or_low:
                    failed_break_count += 1
                if close.iloc[i] < or_low and close.iloc[i-1] > or_low:
                    or_test = True
        
        # Signal
        if current_price_vs_or == 'above' and not or_test:
            signal = SignalType.BUY
            confidence = 0.7
        elif current_price_vs_or == 'below' and not or_test:
            signal = SignalType.SELL
            confidence = 0.7
        elif or_test:
            signal = SignalType.HOLD
            confidence = 0.5
        else:
            signal = SignalType.HOLD
            confidence = 0.4
        
        return OpeningRangeSignal(
            or_high=float(or_high),
            or_low=float(or_low),
            or_range=float(or_range),
            or_mid=float(or_mid),
            current_price_vs_or=current_price_vs_or,
            break_of_or=break_of_or,
            or_test=or_test,
            failed_break_count=failed_break_count,
            session_type=session_type,
            signal_type=signal
        )


class DivergenceAnalyzer:
    """Divergence Detection (RSI, MACD, Volume)"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> DivergenceSignal:
        """Detect regular and hidden divergences"""
        
        if len(close) < 50:
            return DivergenceSignal(
                rsi_divergence=None,
                macd_divergence=None,
                volume_divergence=None,
                divergence_type='none',
                divergence_direction='none',
                divergence_strength=0,
                confidence=0,
                signal_type=SignalType.HOLD
            )
        
        # RSI Calculation
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        # MACD Calculation
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        macd_hist = macd_line - signal_line
        
        # Find price peaks and troughs
        def find_peaks(data, lookback=10):
            peaks = []
            for i in range(lookback, len(data) - lookback):
                if data.iloc[i] >= data.iloc[i-lookback:i].max() and data.iloc[i] >= data.iloc[i+1:i+lookback+1].max():
                    peaks.append((i, data.iloc[i]))
            return peaks
        
        def find_troughs(data, lookback=10):
            troughs = []
            for i in range(lookback, len(data) - lookback):
                if data.iloc[i] <= data.iloc[i-lookback:i].min() and data.iloc[i] <= data.iloc[i+1:i+lookback+1].min():
                    troughs.append((i, data.iloc[i]))
            return troughs
        
        price_peaks = find_peaks(close, 10)
        price_troughs = find_troughs(close, 10)
        rsi_peaks = find_peaks(rsi, 10)
        rsi_troughs = find_troughs(rsi, 10)
        macd_peaks = find_peaks(macd_hist, 10)
        macd_troughs = find_troughs(macd_hist, 10)
        
        rsi_div = None
        macd_div = None
        vol_div = None
        
        # Check RSI Divergence
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            p1_idx, p1_price = price_peaks[-2]
            p2_idx, p2_price = price_peaks[-1]
            r1_idx, r1_val = rsi_peaks[-2]
            r2_idx, r2_val = rsi_peaks[-1]
            
            # Regular Bearish Div: Higher price peaks, lower RSI peaks
            if p2_price > p1_price and r2_val < r1_val:
                rsi_div = {'type': 'regular_bearish', 'strength': (p2_price - p1_price) / p1_price}
            # Hidden Bearish: Lower price peaks, higher RSI peaks
            elif p2_price < p1_price and r2_val > r1_val:
                rsi_div = {'type': 'hidden_bearish', 'strength': (p1_price - p2_price) / p2_price}
        
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            t1_idx, t1_price = price_troughs[-2]
            t2_idx, t2_price = price_troughs[-1]
            r1_idx, r1_val = rsi_troughs[-2]
            r2_idx, r2_val = rsi_troughs[-1]
            
            # Regular Bullish Div: Lower price troughs, higher RSI troughs
            if t2_price < t1_price and r2_val > r1_val:
                rsi_div = {'type': 'regular_bullish', 'strength': (t1_price - t2_price) / t2_price}
            # Hidden Bullish: Higher price troughs, lower RSI troughs
            elif t2_price > t1_price and r2_val < r1_val:
                rsi_div = {'type': 'hidden_bullish', 'strength': (t2_price - t1_price) / t1_price}
        
        # Check MACD Divergence (similar logic)
        if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
            p1_idx, p1_price = price_peaks[-2]
            p2_idx, p2_price = price_peaks[-1]
            m1_idx, m1_val = macd_peaks[-2]
            m2_idx, m2_val = macd_peaks[-1]
            
            if p2_price > p1_price and m2_val < m1_val:
                macd_div = {'type': 'regular_bearish', 'strength': (p2_price - p1_price) / p1_price}
            elif p2_price < p1_price and m2_val > m1_val:
                macd_div = {'type': 'hidden_bearish', 'strength': (p1_price - p2_price) / p2_price}
        
        # Determine overall divergence
        divergence_type = 'none'
        divergence_direction = 'none'
        divergence_strength = 0
        
        for div in [rsi_div, macd_div]:
            if div and 'bullish' in div.get('type', ''):
                divergence_type = div['type']
                divergence_direction = 'bullish'
                divergence_strength = div['strength']
                break
            elif div and 'bearish' in div.get('type', ''):
                divergence_type = div['type']
                divergence_direction = 'bearish'
                divergence_strength = div['strength']
                break
        
        # Signal
        if divergence_direction == 'bullish':
            signal = SignalType.BUY
            confidence = min(0.8, 0.5 + divergence_strength * 10)
        elif divergence_direction == 'bearish':
            signal = SignalType.SELL
            confidence = min(0.8, 0.5 + divergence_strength * 10)
        else:
            signal = SignalType.HOLD
            confidence = 0.3
        
        return DivergenceSignal(
            rsi_divergence=rsi_div,
            macd_divergence=macd_div,
            volume_divergence=vol_div,
            divergence_type=divergence_type,
            divergence_direction=divergence_direction,
            divergence_strength=divergence_strength,
            confidence=confidence,
            signal_type=signal
        )


class CVDAnalyzer:
    """Cumulative Volume Delta Analyzer"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> CVDSignal:
        """Calculate Cumulative Volume Delta"""
        
        if len(close) < 20:
            return CVDSignal(
                cumulative_delta=0,
                delta_per_candle=[],
                cvd_trend='flat',
                cvd_extremes=(0, 0),
                zero_line_crosses=0,
                signal_type=SignalType.HOLD,
                confidence=0
            )
        
        # Calculate delta per candle
        deltas = []
        for i in range(len(close)):
            body = abs(close.iloc[i] - (close.iloc[i-1] if i > 0 else close.iloc[i]))
            range_ = high.iloc[i] - low.iloc[i] if high.iloc[i] > low.iloc[i] else 1
            
            if close.iloc[i] > (close.iloc[i-1] if i > 0 else close.iloc[i]):
                delta = body / range_ * (volume.iloc[i] if i < len(volume) else 1)
            else:
                delta = -body / range_ * (volume.iloc[i] if i < len(volume) else 1)
            
            deltas.append(delta)
        
        deltas = np.array(deltas)
        cvd = np.cumsum(deltas)
        
        # CVD trend
        if len(cvd) > 10:
            recent_cvd = cvd[-10:]
            if recent_cvd[-1] > recent_cvd[0] * 1.1:
                cvd_trend = 'rising'
            elif recent_cvd[-1] < recent_cvd[0] * 0.9:
                cvd_trend = 'falling'
            else:
                cvd_trend = 'flat'
        else:
            cvd_trend = 'flat'
        
        # CVD extremes
        cvd_extremes = (float(cvd.min()), float(cvd.max()))
        
        # Zero line crosses
        zero_crosses = 0
        for i in range(1, len(cvd)):
            if cvd[i-1] < 0 and cvd[i] >= 0:
                zero_crosses += 1
            elif cvd[i-1] > 0 and cvd[i] <= 0:
                zero_crosses += 1
        
        # Signal
        if cvd_trend == 'rising' and cvd[-1] > 0:
            signal = SignalType.BUY
            confidence = 0.7
        elif cvd_trend == 'falling' and cvd[-1] < 0:
            signal = SignalType.SELL
            confidence = 0.7
        elif cvd_trend == 'rising':
            signal = SignalType.BUY
            confidence = 0.5
        elif cvd_trend == 'falling':
            signal = SignalType.SELL
            confidence = 0.5
        else:
            signal = SignalType.HOLD
            confidence = 0.4
        
        return CVDSignal(
            cumulative_delta=float(cvd[-1]),
            delta_per_candle=deltas[-20:].tolist(),
            cvd_trend=cvd_trend,
            cvd_extremes=cvd_extremes,
            zero_line_crosses=zero_crosses,
            signal_type=signal,
            confidence=confidence
        )


class TrendLineBreakAnalyzer:
    """Trend Line Break Detection"""
    
    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> TrendLineBreakSignal:
        """Detect trend line breaks"""
        
        if len(close) < 50:
            return TrendLineBreakSignal(
                trend_lines=[],
                active_trend='sideways',
                broken_line=None,
                break_quality='weak',
                retest_zone=0,
                time_since_break=0,
                signal_type=SignalType.HOLD,
                confidence=0
            )
        
        # Find swing points
        swing_highs = []
        swing_lows = []
        
        for i in range(10, len(high) - 5):
            if high.iloc[i] >= high.iloc[i-5:i].max() and high.iloc[i] >= high.iloc[i+1:i+6].max():
                swing_highs.append((i, high.iloc[i]))
        
        for i in range(10, len(low) - 5):
            if low.iloc[i] <= low.iloc[i-5:i].min() and low.iloc[i] <= low.iloc[i+1:i+6].min():
                swing_lows.append((i, low.iloc[i]))
        
        # Build trend lines
        trend_lines = []
        
        # Uptrend line (connecting swing lows)
        if len(swing_lows) >= 3:
            lows_sorted = sorted(swing_lows[-5:])
            slope = (lows_sorted[-1][1] - lows_sorted[0][1]) / (lows_sorted[-1][0] - lows_sorted[0][0] + 1)
            trend_lines.append({
                'type': 'uptrend',
                'slope': slope,
                'points': lows_sorted,
                'intercept': lows_sorted[0][1] - slope * lows_sorted[0][0]
            })
        
        # Downtrend line (connecting swing highs)
        if len(swing_highs) >= 3:
            highs_sorted = sorted(swing_highs[-5:])
            slope = (highs_sorted[-1][1] - highs_sorted[0][1]) / (highs_sorted[-1][0] - highs_sorted[0][0] + 1)
            trend_lines.append({
                'type': 'downtrend',
                'slope': slope,
                'points': highs_sorted,
                'intercept': highs_sorted[0][1] - slope * highs_sorted[0][0]
            })
        
        # Determine active trend
        if len(trend_lines) == 0:
            active_trend = 'sideways'
        elif trend_lines[0]['type'] == 'uptrend':
            active_trend = 'uptrend'
        elif trend_lines[0]['type'] == 'downtrend':
            active_trend = 'downtrend'
        else:
            active_trend = 'sideways'
        
        # Check for broken lines
        broken_line = None
        break_quality = 'weak'
        time_since_break = 0
        retest_zone = close.iloc[-1]
        
        for line in trend_lines:
            for idx, price in line['points']:
                for i in range(idx, len(close)):
                    if line['type'] == 'uptrend':
                        expected_price = line['slope'] * i + line['intercept']
                        if close.iloc[i] < expected_price:
                            broken_line = line
                            time_since_break = len(close) - i
                            retest_zone = expected_price
                            # Check break quality (how far below trend)
                            break_size = (expected_price - close.iloc[i]) / expected_price
                            if break_size > 0.01:
                                break_quality = 'strong'
                            break
                    else:
                        expected_price = line['slope'] * i + line['intercept']
                        if close.iloc[i] > expected_price:
                            broken_line = line
                            time_since_break = len(close) - i
                            retest_zone = expected_price
                            break_size = (close.iloc[i] - expected_price) / expected_price
                            if break_size > 0.01:
                                break_quality = 'strong'
                            break
                if broken_line:
                    break
            if broken_line:
                break
        
        # Signal
        if broken_line:
            if broken_line['type'] == 'uptrend':
                signal = SignalType.SELL
            else:
                signal = SignalType.BUY
            confidence = 0.7 if break_quality == 'strong' else 0.5
        else:
            signal = SignalType.HOLD
            confidence = 0.4
        
        return TrendLineBreakSignal(
            trend_lines=trend_lines,
            active_trend=active_trend,
            broken_line=broken_line,
            break_quality=break_quality,
            retest_zone=retest_zone,
            time_since_break=time_since_break,
            signal_type=signal,
            confidence=confidence
        )


class RetailStrategyAnalyzer:
    """
    Unified Retail Strategy Analyzer

    Combines multiple retail trading methodologies:
    - Wyckoff (Phase analysis, accumulation/distribution)
    - ICT (Order blocks, FVGs, liquidity, premium/discount)
    - SMC (Smart money concepts, institutional order flow)
    - SNR/MSNR (Support/resistance levels)
    - Fibonacci (Retracements, extensions, golden ratios)
    - Volume Profile (POC, VAH, VAL)
    - OTE (Optimal Trade Entry)
    - Kill Zones (London/NY/Asian sessions)
    - Market Profile (TPO analysis)
    - Volume Delta (Order flow)
    - Absorption Detection
    - Displacement Analysis
    - Mitigation Counter
    - Liquidity Void
    - Opening Range
    - Divergence Detection
    - CVD (Cumulative Volume Delta)
    - Trend Line Break
    """

    def __init__(self):
        self.strategies = {
            'wyckoff': WyckoffAnalyzer(),
            'ict': ICTAnalyzer(),
            'smc': SMCAnalyzer(),
            'fibonacci': FibonacciAnalyzer(),
            'snr': SNRAnalyzer(),
            'volume_profile': VolumeProfileAnalyzer(),
            # New SMC/ICT Concepts
            'ote': OTEAnalyzer(),
            'kill_zone': KillZoneAnalyzer(),
            'market_profile': MarketProfileAnalyzer(),
            'volume_delta': VolumeDeltaAnalyzer(),
            'absorption': AbsorptionAnalyzer(),
            'displacement': DisplacementAnalyzer(),
            'mitigation': MitigationAnalyzer(),
            'liquidity_void': LiquidityVoidAnalyzer(),
            'opening_range': OpeningRangeAnalyzer(),
            'divergence': DivergenceAnalyzer(),
            'cvd': CVDAnalyzer(),
            'trend_line': TrendLineBreakAnalyzer(),
        }

        # Strategy weights for unified scoring
        self.weights = {
            'wyckoff': 0.08,
            'ict': 0.12,
            'smc': 0.12,
            'fibonacci': 0.08,
            'snr': 0.08,
            'volume_profile': 0.06,
            # New weights
            'ote': 0.06,
            'kill_zone': 0.04,
            'market_profile': 0.05,
            'volume_delta': 0.05,
            'absorption': 0.04,
            'displacement': 0.04,
            'mitigation': 0.04,
            'liquidity_void': 0.03,
            'opening_range': 0.04,
            'divergence': 0.04,
            'cvd': 0.03,
            'trend_line': 0.02,
        }

    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        symbol: str = "UNKNOWN",
        lookback: int = 500
    ) -> UnifiedSignal:
        """
        Perform comprehensive retail strategy analysis

        Returns UnifiedSignal with all components
        """

        # Run all strategy analyses
        wyckoff = self.strategies['wyckoff'].analyze(high, low, close, volume, lookback)
        ict = self.strategies['ict'].analyze(high, low, close, volume, symbol)
        smc = self.strategies['smc'].analyze(high, low, close, volume)
        fib = self.strategies['fibonacci'].analyze(high, low, close)
        snr = self.strategies['snr'].analyze(high, low, close)
        vp = self.strategies['volume_profile'].analyze(high, low, close, volume)
        
        # Run new SMC/ICT analyses
        ote = self.strategies['ote'].analyze(high, low, close)
        kill_zone = self.strategies['kill_zone'].analyze(high, low, close, volume)
        market_profile = self.strategies['market_profile'].analyze(high, low, close, volume)
        volume_delta = self.strategies['volume_delta'].analyze(high, low, close, volume)
        absorption = self.strategies['absorption'].analyze(high, low, close)
        displacement = self.strategies['displacement'].analyze(high, low, close)
        mitigation = self.strategies['mitigation'].analyze(high, low, close)
        liquidity_void = self.strategies['liquidity_void'].analyze(high, low, close)
        opening_range = self.strategies['opening_range'].analyze(high, low, close)
        divergence = self.strategies['divergence'].analyze(high, low, close, volume)
        cvd = self.strategies['cvd'].analyze(high, low, close, volume)
        trend_line = self.strategies['trend_line'].analyze(high, low, close)

        # Aggregate signals
        signal = self._aggregate_signals(
            symbol=symbol,
            wyckoff=wyckoff,
            ict=ict,
            smc=smc,
            fib=fib,
            snr=snr,
            volume_profile=vp,
            # New signals
            ote=ote,
            kill_zone=kill_zone,
            market_profile=market_profile,
            volume_delta=volume_delta,
            absorption=absorption,
            displacement=displacement,
            mitigation=mitigation,
            liquidity_void=liquidity_void,
            opening_range=opening_range,
            divergence=divergence,
            cvd=cvd,
            trend_line=trend_line,
            high=high,
            low=low,
            close=close,
            volume=volume
        )

        return signal

    def _aggregate_signals(
        self,
        symbol: str,
        wyckoff: Any,
        ict: ICTSignal,
        smc: SMCSignal,
        fib: FibonacciSignal,
        snr: Dict,
        volume_profile: Dict,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        # New signals
        ote: OTESignal = None,
        kill_zone: KillZoneSignal = None,
        market_profile: MarketProfileSignal = None,
        volume_delta: VolumeDeltaSignal = None,
        absorption: AbsorptionSignal = None,
        displacement: DisplacementSignal = None,
        mitigation: MitigationSignal = None,
        liquidity_void: LiquidityVoidSignal = None,
        opening_range: OpeningRangeSignal = None,
        divergence: DivergenceSignal = None,
        cvd: CVDSignal = None,
        trend_line: TrendLineBreakSignal = None,
    ) -> UnifiedSignal:
        """Aggregate all signals into unified signal"""

        current_price = close.iloc[-1]

        # Calculate individual scores
        scores = {
            'wyckoff': self._score_wyckoff(wyckoff),
            'ict': self._score_ict(ict),
            'smc': self._score_smc(smc),
            'fibonacci': self._score_fibonacci(fib),
            'snr': self._score_snr(snr, current_price),
            'volume_profile': self._score_volume_profile(volume_profile, current_price),
            # New scores
            'ote': self._score_ote(ote) if ote else 50,
            'kill_zone': self._score_kill_zone(kill_zone) if kill_zone else 50,
            'market_profile': self._score_market_profile(market_profile, close) if market_profile else 50,
            'volume_delta': self._score_volume_delta(volume_delta) if volume_delta else 50,
            'absorption': self._score_absorption(absorption) if absorption else 50,
            'displacement': self._score_displacement(displacement) if displacement else 50,
            'mitigation': self._score_mitigation(mitigation) if mitigation else 50,
            'liquidity_void': self._score_liquidity_void(liquidity_void) if liquidity_void else 50,
            'opening_range': self._score_opening_range(opening_range) if opening_range else 50,
            'divergence': self._score_divergence(divergence) if divergence else 50,
            'cvd': self._score_cvd(cvd) if cvd else 50,
            'trend_line': self._score_trend_line(trend_line) if trend_line else 50,
        }

        # Calculate weighted score
        total_score = sum(scores[k] * self.weights.get(k, 0.04) for k in scores)

        # Determine direction
        if total_score >= 60:
            direction = SignalType.BUY
        elif total_score <= 40:
            direction = SignalType.SELL
        else:
            direction = SignalType.HOLD

        # Collect reasons
        reasons = []
        if scores.get('wyckoff', 50) > 0.6:
            reasons.append(f"Wyckoff: {wyckoff.phase.value if hasattr(wyckoff, 'phase') else 'Strong'}")
        if ict.confidence > 0.6:
            reasons.append(f"ICT: {ict.premium_discount} zone, {ict.session} session")
        if smc.confidence > 0.6:
            reasons.append(f"SMC: {'BOS' if smc.change_of_character else 'MSS' if smc.market_structure_shift else 'Structure'} confirmed")
        if fib.golden_pocket:
            reasons.append("Fibonacci: Golden pocket confluence")
        if scores.get('snr', 50) > 0.6:
            reasons.append(f"SNR: {len(snr.get('support', []))} support / {len(snr.get('resistance', []))} resistance levels")
        # New reasons
        if ote and ote.confidence > 0.6:
            reasons.append(f"OTE: {ote.zone} zone, {ote.current_position_pct:.0f}% in range")
        if kill_zone and kill_zone.zone_active:
            reasons.append(f"Kill Zone: Active {kill_zone.current_zone} session")
        if divergence and divergence.divergence_direction != 'none':
            reasons.append(f"Divergence: {divergence.divergence_type} {divergence.divergence_direction}")
        if displacement and displacement.displacement_detected:
            reasons.append(f"Displacement: {displacement.displacement_size:.1f}% move detected")
        if absorption and absorption.absorption_detected:
            reasons.append(f"Absorption: {absorption.rejection_count} rejections at level")

        # Calculate entry, SL, TP
        entry, sl, tp = self._calculate_entry_sl_tp(
            current_price, direction, wyckoff, ict, smc, fib, snr
        )

        # Determine trend
        trend = self._determine_trend(high, low, close)

        # Determine session
        session = self._get_current_session()

        # Extend metadata with new signals
        metadata = {
            'ote_signal': ote.__dict__ if ote else None,
            'kill_zone_signal': kill_zone.__dict__ if kill_zone else None,
            'market_profile_signal': market_profile.__dict__ if market_profile else None,
            'volume_delta_signal': volume_delta.__dict__ if volume_delta else None,
            'absorption_signal': absorption.__dict__ if absorption else None,
            'displacement_signal': displacement.__dict__ if displacement else None,
            'mitigation_signal': mitigation.__dict__ if mitigation else None,
            'liquidity_void_signal': liquidity_void.__dict__ if liquidity_void else None,
            'opening_range_signal': opening_range.__dict__ if opening_range else None,
            'divergence_signal': divergence.__dict__ if divergence else None,
            'cvd_signal': cvd.__dict__ if cvd else None,
            'trend_line_signal': trend_line.__dict__ if trend_line else None,
        }

        return UnifiedSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            direction=direction,
            confidence=total_score / 100,
            score=int(total_score),
            wyckoff_signal=wyckoff,
            ict_signal=ict,
            smc_signal=smc,
            fibonacci_signal=fib,
            entry_zone=(entry - entry * 0.002, entry + entry * 0.002) if entry else (current_price, current_price),
            stop_loss=sl if sl else current_price * 0.98 if direction == SignalType.BUY else current_price * 1.02,
            take_profit_levels=tp if tp else (current_price * 1.02, current_price * 1.05),
            trend=trend,
            session=session,
            reasons=reasons,
            metadata=metadata
        )

    # ============ NEW SCORING METHODS ============

    def _score_ote(self, ote: OTESignal) -> float:
        if not ote:
            return 50
        score = 50
        if ote.signal_type == SignalType.BUY:
            score += 25
            if ote.zone == 'deep_discount':
                score += 15
        elif ote.signal_type == SignalType.SELL:
            score -= 25
            if ote.zone == 'deep_premium':
                score -= 15
        score += ote.confidence * 20
        return max(0, min(100, score))

    def _score_kill_zone(self, kill_zone: KillZoneSignal) -> float:
        if not kill_zone:
            return 50
        score = 50
        if kill_zone.zone_active:
            score += 20
        if kill_zone.liquidity_window:
            score += 15
        return max(0, min(100, score))

    def _score_market_profile(self, mp: MarketProfileSignal, close: pd.Series) -> float:
        if not mp:
            return 50
        score = 50
        # Price in value area is neutral
        if mp.auction_type == 'balanced':
            score += 10
        # Price above POC is bullish
        if close.iloc[-1] > mp.poc:
            score += 15
        else:
            score -= 15
        return max(0, min(100, score))

    def _score_volume_delta(self, vd: VolumeDeltaSignal) -> float:
        if not vd:
            return 50
        score = 50
        if vd.order_flow_quality == 'strong':
            score += 25
        elif vd.order_flow_quality == 'weak':
            score -= 25
        if vd.delta_trend == 'accumulating':
            score += 15
        elif vd.delta_trend == 'distributing':
            score -= 15
        return max(0, min(100, score))

    def _score_absorption(self, abs_signal: AbsorptionSignal) -> float:
        if not abs_signal:
            return 50
        score = 50
        if abs_signal.absorption_detected:
            score += 20
            score += abs_signal.rejection_strength * 20
        return max(0, min(100, score))

    def _score_displacement(self, disp: DisplacementSignal) -> float:
        if not disp:
            return 50
        score = 50
        if disp.displacement_detected:
            score += 25
            score += min(20, disp.displacement_size)
        return max(0, min(100, score))

    def _score_mitigation(self, mit: MitigationSignal) -> float:
        if not mit:
            return 50
        score = 50
        if mit.active_ob_count > 0:
            score += 20
        if mit.best_buy_ob:
            score += 15
        return max(0, min(100, score))

    def _score_liquidity_void(self, lv: LiquidityVoidSignal) -> float:
        if not lv:
            return 50
        score = 50
        if lv.gap_quality == 'strong':
            score += 15
        score += min(15, lv.fair_value_gap_count * 3)
        return max(0, min(100, score))

    def _score_opening_range(self, or_signal: OpeningRangeSignal) -> float:
        if not or_signal:
            return 50
        score = 50
        if or_signal.break_of_or and not or_signal.or_test:
            if or_signal.current_price_vs_or == 'above':
                score += 25
            else:
                score -= 25
        return max(0, min(100, score))

    def _score_divergence(self, div: DivergenceSignal) -> float:
        if not div:
            return 50
        score = 50
        if div.divergence_direction == 'bullish':
            score += 30
        elif div.divergence_direction == 'bearish':
            score -= 30
        score += div.confidence * 20
        return max(0, min(100, score))

    def _score_cvd(self, cvd_signal: CVDSignal) -> float:
        if not cvd_signal:
            return 50
        score = 50
        if cvd_signal.signal_type == SignalType.BUY:
            score += 25
        elif cvd_signal.signal_type == SignalType.SELL:
            score -= 25
        score += cvd_signal.confidence * 20
        return max(0, min(100, score))

    def _score_trend_line(self, tl: TrendLineBreakSignal) -> float:
        if not tl:
            return 50
        score = 50
        if tl.broken_line:
            score -= 20 if tl.broken_line['type'] == 'uptrend' else -20
        if tl.break_quality == 'strong':
            score += 15
        return max(0, min(100, score))

    def _score_wyckoff(self, wyckoff: Any) -> float:
        if not wyckoff or not hasattr(wyckoff, 'phase'):
            return 50
        score = 50
        if wyckoff.phase.value in ['accumulation_c', 'markup']:
            score += 30
        elif wyckoff.phase.value in ['distribution_c', 'markdown']:
            score -= 30
        score += wyckoff.confidence * 0.2
        return max(0, min(100, score))

    def _score_ict(self, ict: ICTSignal) -> float:
        if not ict:
            return 50
        score = 50
        if ict.signal_type == SignalType.BUY:
            score += 25
            if ict.premium_discount == 'discount':
                score += 15
        elif ict.signal_type == SignalType.SELL:
            score -= 25
            if ict.premium_discount == 'premium':
                score -= 15
        score += ict.confidence * 0.2
        return max(0, min(100, score))

    def _score_smc(self, smc: SMCSignal) -> float:
        if not smc:
            return 50
        score = 50
        if smc.signal_type == SignalType.BUY:
            score += 20
        elif smc.signal_type == SignalType.SELL:
            score -= 20
        if smc.change_of_character:
            score += 15
        if smc.market_structure_shift:
            score += 15
        score += smc.confidence * 0.2
        return max(0, min(100, score))

    def _score_fibonacci(self, fib: FibonacciSignal) -> float:
        if not fib:
            return 50
        score = 50
        if fib.golden_pocket:
            score += 25
        if fib.confluence_score > 0.7:
            score += 15
        if fib.signal_type == SignalType.BUY:
            score += 10
        elif fib.signal_type == SignalType.SELL:
            score -= 10
        return max(0, min(100, score))

    def _score_snr(self, snr: Dict, current_price: float) -> float:
        if not snr:
            return 50
        score = 50
        supports = snr.get('support', [])
        resistances = snr.get('resistance', [])
        for s in supports:
            if abs(s['price'] - current_price) / current_price < 0.02:
                score += 10
        for r in resistances:
            if abs(r['price'] - current_price) / current_price < 0.02:
                score -= 10
        return max(0, min(100, score))

    def _score_volume_profile(self, vp: Dict, current_price: float) -> float:
        if not vp:
            return 50
        score = 50
        poc = vp.get('poc', current_price)
        if abs(poc - current_price) / current_price < 0.01:
            score += 20
        return max(0, min(100, score))

    def _calculate_entry_sl_tp(
        self,
        current_price: float,
        direction: SignalType,
        wyckoff: Any,
        ict: ICTSignal,
        smc: SMCSignal,
        fib: FibonacciSignal,
        snr: Dict
    ) -> Tuple[float, float, Tuple[float, ...]]:
        """Calculate optimal entry, stop loss, and take profit levels"""

        entry = current_price

        if direction == SignalType.BUY:
            # Entry at current price or ICT entry zone
            if ict and ict.entry_zone:
                entry = (ict.entry_zone[0] + ict.entry_zone[1]) / 2

            # Stop loss below support or order block
            sl = current_price * 0.97
            if ict and ict.order_block:
                sl = min(sl, ict.order_block.price * 0.99)
            if snr.get('support'):
                sl = min(sl, min(s['price'] for s in snr['support'][:3]) * 0.995)

            # Take profit at resistance or extension targets
            tp1 = current_price * 1.03
            tp2 = current_price * 1.05
            if fib and fib.extension_level:
                tp1 = current_price * (1 + (fib.extension_level - 1) * 0.5)
                tp2 = current_price * fib.extension_level
            if snr.get('resistance'):
                tp1 = min(tp1, min(r['price'] for r in snr['resistance'][:3]))

        elif direction == SignalType.SELL:
            if ict and ict.entry_zone:
                entry = (ict.entry_zone[0] + ict.entry_zone[1]) / 2

            sl = current_price * 1.03
            if ict and ict.order_block:
                sl = max(sl, ict.order_block.price * 1.01)
            if snr.get('resistance'):
                sl = max(sl, max(r['price'] for r in snr['resistance'][:3]) * 1.005)

            tp1 = current_price * 0.97
            tp2 = current_price * 0.95
            if fib and fib.extension_level:
                tp1 = current_price * (1 - (fib.extension_level - 1) * 0.5)
                tp2 = current_price * (2 - fib.extension_level)
            if snr.get('support'):
                tp1 = max(tp1, max(s['price'] for s in snr['support'][:3]))

        else:
            sl = current_price * 0.98
            tp1 = current_price * 1.01
            tp2 = current_price * 1.02

        return entry, sl, (tp1, tp2)

    def _determine_trend(self, high: pd.Series, low: pd.Series, close: pd.Series) -> TrendDirection:
        """Determine market trend using price action"""

        if len(close) < 50:
            return TrendDirection.NEUTRAL

        # Higher highs and higher lows = Uptrend
        # Lower highs and lower lows = Downtrend

        hh = high.rolling(20).max().iloc[-1]
        hl = low.rolling(20).min().iloc[-1]
        prev_hh = high.rolling(20).max().iloc[-2]
        prev_hl = low.rolling(20).min().iloc[-2]

        ll = low.rolling(20).min().iloc[-1]
        lh = high.rolling(20).min().iloc[-1]
        prev_ll = low.rolling(20).min().iloc[-2]
        prev_lh = high.rolling(20).min().iloc[-2]

        current = close.iloc[-1]
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]

        bullish_count = 0
        bearish_count = 0

        if current > sma_20:
            bullish_count += 1
        else:
            bearish_count += 1

        if sma_20 > sma_50:
            bullish_count += 1
        else:
            bearish_count += 1

        if hh > prev_hh and hl > prev_hl:
            bullish_count += 2
        elif ll < prev_ll and lh < prev_lh:
            bearish_count += 2

        if bullish_count > bearish_count:
            return TrendDirection.BULLISH
        elif bearish_count > bullish_count:
            return TrendDirection.BEARISH
        return TrendDirection.NEUTRAL

    def _get_current_session(self) -> str:
        """Get current trading session"""
        utc_hour = datetime.utcnow().hour

        if 0 <= utc_hour < 8:
            return "asian"
        elif 8 <= utc_hour < 13:
            return "london"
        elif 13 <= utc_hour < 17:
            return "london_ny_overlap"
        elif 17 <= utc_hour < 22:
            return "ny"
        else:
            return "asian"


# ==================== INDIVIDUAL STRATEGY ANALYZERS ====================

class WyckoffAnalyzer:
    """Wyckoff methodology analyzer"""

    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        lookback: int = 100
    ) -> Any:
        """Analyze using Wyckoff methodology"""

        class WyckoffResult:
            def __init__(self):
                self.phase = TrendDirection.NEUTRAL
                self.confidence = 0.5
                self.events = []
                self.target = None
                self.stop = None

        result = WyckoffResult()

        if len(close) < lookback:
            return result

        # Calculate accumulation/distribution
        ad = (close - close.shift(1)) * volume
        ad_rolling = ad.rolling(20).sum()

        # Calculate price position
        recent_high = high.rolling(20).max().iloc[-1]
        recent_low = low.rolling(20).min().iloc[-1]
        current_price = close.iloc[-1]
        position = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5

        # Determine phase
        if position < 0.2:
            result.phase = TrendDirection.BEARISH
            result.events.append("Selling Climax")
        elif position < 0.35:
            result.phase = TrendDirection.NEUTRAL
            result.events.append("Automatic Rally")
        elif position > 0.8:
            result.phase = TrendDirection.BULLISH
            result.events.append("Spring")
        elif position > 0.65:
            result.phase = TrendDirection.NEUTRAL
            result.events.append("Sign of Strength")

        result.confidence = 0.5 + abs(position - 0.5) * 0.5

        return result


class ICTAnalyzer:
    """ICT (Inner Circle Trader) strategy analyzer"""

    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        symbol: str = "UNKNOWN"
    ) -> ICTSignal:
        """Analyze using ICT methodology"""

        current_price = close.iloc[-1]

        # Calculate order blocks
        order_blocks = self._find_order_blocks(high, low, close)

        # Find fair value gaps
        fvgs = self._find_fvgs(high, low, close)

        # Find liquidity levels
        liquidity = self._find_liquidity_levels(high, low, close)

        # Determine premium/discount
        sma_20 = close.rolling(20).mean().iloc[-1]
        premium_discount = 'premium' if current_price > sma_20 else 'discount'

        # Determine market structure
        trend = self._determine_structure(high, low, close)

        # Determine session
        session = self._get_session()

        # Calculate confidence
        confidence = 0.5
        if order_blocks:
            confidence += 0.2
        if fvgs:
            confidence += 0.1
        if trend != 'neutral':
            confidence += 0.2

        # Calculate entry zone
        if order_blocks:
            ob = order_blocks[0]
            entry_zone = (ob.price * 0.999, ob.price * 1.001)
            sl = ob.price * 0.98 if trend == 'bullish' else ob.price * 1.02
        else:
            entry_zone = (current_price * 0.999, current_price * 1.001)
            sl = current_price * 0.98 if trend == 'bullish' else current_price * 1.02

        tp1 = current_price * 1.02
        tp2 = current_price * 1.03

        signal_type = SignalType.HOLD
        if trend == 'bullish' and premium_discount == 'discount':
            signal_type = SignalType.BUY
        elif trend == 'bearish' and premium_discount == 'premium':
            signal_type = SignalType.SELL

        return ICTSignal(
            signal_type=signal_type,
            order_block=order_blocks[0] if order_blocks else None,
            fvg_zones=fvgs[:3],
            liquidity_levels=liquidity[:3],
            premium_discount=premium_discount,
            session=session,
            market_structure=trend,
            confidence=min(0.9, confidence),
            entry_zone=entry_zone,
            stop_loss=sl,
            take_profit=(tp1, tp2)
        )

    def _find_order_blocks(self, high: pd.Series, low: pd.Series, close: pd.Series) -> List[Level]:
        """Find order blocks (previous bearish/bullish candle before FVG)"""
        blocks = []
        # Need open price to determine candle direction - estimate from close
        open_est = close.shift(1).fillna(close)
        candles = pd.DataFrame({
            'high': high, 
            'low': low, 
            'close': close,
            'open': open_est
        })

        for i in range(3, len(candles)):
            # Check for bullish order block (bearish candle before FVG)
            if candles['close'].iloc[i-3] < candles['open'].iloc[i-3]:  # Bearish candle
                # Check for FVG next 3 candles
                high_imbalance = max(candles['high'].iloc[i-2:i+1])
                low_imbalance = min(candles['low'].iloc[i-2:i+1])

                if candles['high'].iloc[i-3] > low_imbalance and candles['low'].iloc[i-3] < high_imbalance:
                    blocks.append(Level(
                        price=candles['close'].iloc[i-3],
                        level_type='order_block_bullish',
                        strength=0.7,
                        timestamp=datetime.now()
                    ))

            # Check for bearish order block (bullish candle before FVG)
            if candles['close'].iloc[i-3] > candles['open'].iloc[i-3]:  # Bullish candle
                high_imbalance = max(candles['high'].iloc[i-2:i+1])
                low_imbalance = min(candles['low'].iloc[i-2:i+1])

                if candles['high'].iloc[i-3] > low_imbalance and candles['low'].iloc[i-3] < high_imbalance:
                    blocks.append(Level(
                        price=candles['close'].iloc[i-3],
                        level_type='order_block_bearish',
                        strength=0.7,
                        timestamp=datetime.now()
                    ))

        return blocks[:5]

    def _find_fvgs(self, high: pd.Series, low: pd.Series, close: pd.Series) -> List[Level]:
        """Find Fair Value Gaps (imbalances)"""
        fvgs = []
        candles = pd.DataFrame({'high': high, 'low': low, 'close': close})

        for i in range(2, len(candles)):
            # Bullish FVG: low of current > high of 2 candles ago
            if candles['low'].iloc[i] > candles['high'].iloc[i-2]:
                fvgs.append(Level(
                    price=(candles['low'].iloc[i] + candles['high'].iloc[i-2]) / 2,
                    level_type='fvg_bullish',
                    strength=0.6,
                    timestamp=datetime.now()
                ))

            # Bearish FVG: high of current < low of 2 candles ago
            if candles['high'].iloc[i] < candles['low'].iloc[i-2]:
                fvgs.append(Level(
                    price=(candles['high'].iloc[i] + candles['low'].iloc[i-2]) / 2,
                    level_type='fvg_bearish',
                    strength=0.6,
                    timestamp=datetime.now()
                ))

        return fvgs[:5]

    def _find_liquidity_levels(self, high: pd.Series, low: pd.Series, close: pd.Series) -> List[Level]:
        """Find liquidity levels (swing highs/lows)"""
        liquidity = []

        # Find swing highs
        swing_highs = []
        for i in range(2, len(high)-2):
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]:
                swing_highs.append(high.iloc[i])

        # Find swing lows
        swing_lows = []
        for i in range(2, len(low)-2):
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]:
                swing_lows.append(low.iloc[i])

        for price in swing_highs[-3:]:
            liquidity.append(Level(price=price, level_type='liquidity_high', strength=0.5, timestamp=datetime.now()))

        for price in swing_lows[-3:]:
            liquidity.append(Level(price=price, level_type='liquidity_low', strength=0.5, timestamp=datetime.now()))

        return liquidity

    def _determine_structure(self, high: pd.Series, low: pd.Series, close: pd.Series) -> str:
        """Determine market structure"""
        if len(close) < 20:
            return 'neutral'

        hh = high.rolling(10).max().iloc[-1]
        hl = low.rolling(10).min().iloc[-1]
        ll = low.rolling(10).min().iloc[-1]
        lh = high.rolling(10).min().iloc[-1]

        prev_hh = high.rolling(10).max().iloc[-2]
        prev_hl = low.rolling(10).min().iloc[-2]

        if hh > prev_hh and hl > prev_hl:
            return 'bullish'
        elif ll < low.rolling(10).min().iloc[-2] and lh < high.rolling(10).min().iloc[-2]:
            return 'bearish'
        return 'neutral'

    def _get_session(self) -> str:
        utc_hour = datetime.utcnow().hour
        if 0 <= utc_hour < 8:
            return 'asian'
        elif 8 <= utc_hour < 13:
            return 'london'
        elif 13 <= utc_hour < 17:
            return 'london_ny'
        elif 17 <= utc_hour < 22:
            return 'ny'
        return 'asian'


class SMCAnalyzer:
    """Smart Money Concepts analyzer"""

    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> SMCSignal:
        """Analyze using SMC methodology"""

        # Find order blocks
        order_blocks = self._identify_order_blocks(high, low, close)

        # Find fair value gaps
        fvgs = self._identify_fvgs(high, low, close)

        # Find breaker blocks
        breaker_blocks = self._identify_breaker_blocks(high, low, close)

        # Find liquidity sweeps
        liquidity_sweeps = self._identify_liquidity_sweeps(high, low, close)

        # Find equal highs/lows
        ehl = self._identify_ehl(high, low)

        # Check for change of character
        choch = self._check_choch(high, low, close)

        # Check for market structure shift
        mss = self._check_mss(high, low, close)

        # Determine signal
        signal_type = SignalType.HOLD
        confidence = 0.5

        if mss:
            if self._get_trend(high, low, close) == 'bullish':
                signal_type = SignalType.BUY
                confidence = 0.8
            else:
                signal_type = SignalType.SELL
                confidence = 0.8
        elif choch:
            signal_type = SignalType.SELL if self._get_trend(high, low, close) == 'bullish' else SignalType.BUY
            confidence = 0.7

        current_price = close.iloc[-1]
        entry = current_price
        sl = current_price * 0.98 if signal_type == SignalType.BUY else current_price * 1.02
        tp = (current_price * 1.02, current_price * 1.05)

        return SMCSignal(
            signal_type=signal_type,
            order_blocks=order_blocks,
            fair_value_gaps=fvgs,
            breaker_blocks=breaker_blocks,
            liquidity_sweeps=liquidity_sweeps,
            equal_highs_lows=ehl,
            change_of_character=choch,
            market_structure_shift=mss,
            confidence=confidence,
            entry_zone=(entry * 0.999, entry * 1.001),
            stop_loss=sl,
            take_profit=tp
        )

    def _identify_order_blocks(self, high: pd.Series, low: pd.Series, close: pd.Series) -> List[Level]:
        """Identify order blocks"""
        blocks = []
        open_est = close.shift(1).fillna(close)

        for i in range(5, len(close)):
            # Check for bullish OB
            if close.iloc[i-1] < open_est.iloc[i-1]:  # Bearish candle
                if high.iloc[i] > high.iloc[i-3] and low.iloc[i] < low.iloc[i-3]:
                    blocks.append(Level(
                        price=close.iloc[i-1],
                        level_type='ob_bullish',
                        strength=0.7,
                        timestamp=datetime.now()
                    ))
            # Check for bearish OB
            if close.iloc[i-1] > open_est.iloc[i-1]:  # Bullish candle
                if high.iloc[i] > high.iloc[i-3] and low.iloc[i] < low.iloc[i-3]:
                    blocks.append(Level(
                        price=close.iloc[i-1],
                        level_type='ob_bearish',
                        strength=0.7,
                        timestamp=datetime.now()
                    ))
        return blocks[:5]

    def _identify_fvgs(self, high: pd.Series, low: pd.Series, close: pd.Series) -> List[Level]:
        """Identify fair value gaps"""
        fvgs = []
        for i in range(2, len(close)):
            if low.iloc[i] > high.iloc[i-2]:
                fvgs.append(Level(
                    price=(low.iloc[i] + high.iloc[i-2]) / 2,
                    level_type='fvg_bullish',
                    strength=0.6,
                    timestamp=datetime.now()
                ))
            if high.iloc[i] < low.iloc[i-2]:
                fvgs.append(Level(
                    price=(high.iloc[i] + low.iloc[i-2]) / 2,
                    level_type='fvg_bearish',
                    strength=0.6,
                    timestamp=datetime.now()
                ))
        return fvgs[:5]

    def _identify_breaker_blocks(self, high: pd.Series, low: pd.Series, close: pd.Series) -> List[Level]:
        """Identify breaker blocks"""
        breakers = []
        for i in range(10, len(close)):
            # A breaker block forms when price breaks and closes beyond OB
            # Simplified detection
            if abs(close.iloc[i] - close.iloc[i-5]) / close.iloc[i-5] > 0.01:
                breakers.append(Level(
                    price=close.iloc[i-5],
                    level_type='breaker',
                    strength=0.5,
                    timestamp=datetime.now()
                ))
        return breakers[:3]

    def _identify_liquidity_sweeps(self, high: pd.Series, low: pd.Series, close: pd.Series) -> List[Level]:
        """Identify liquidity sweeps"""
        sweeps = []
        swing_highs = []
        swing_lows = []

        for i in range(5, len(high)):
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2]:
                if i > 5 and high.iloc[i] > high.iloc[i-5:i].max() * 0.999:
                    swing_highs.append(high.iloc[i])

        for i in range(5, len(low)):
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2]:
                if i > 5 and low.iloc[i] < low.iloc[i-5:i].min() * 1.001:
                    swing_lows.append(low.iloc[i])

        for price in swing_highs[-2:]:
            sweeps.append(Level(price=price, level_type='sweep_high', strength=0.5, timestamp=datetime.now()))
        for price in swing_lows[-2:]:
            sweeps.append(Level(price=price, level_type='sweep_low', strength=0.5, timestamp=datetime.now()))

        return sweeps

    def _identify_ehl(self, high: pd.Series, low: pd.Series) -> List[Level]:
        """Identify Equal Highs/Lows"""
        ehl = []
        swing_highs = []
        swing_lows = []

        for i in range(5, len(high)-5):
            if high.iloc[i] >= high.iloc[i-5:i].max() and high.iloc[i] >= high.iloc[i+1:i+6].max():
                swing_highs.append(high.iloc[i])

        for i in range(5, len(low)-5):
            if low.iloc[i] <= low.iloc[i-5:i].min() and low.iloc[i] <= low.iloc[i+1:i+6].min():
                swing_lows.append(low.iloc[i])

        # Find equal highs
        for i, h1 in enumerate(swing_highs):
            for h2 in swing_highs[i+1:]:
                if abs(h1 - h2) / h1 < 0.001:
                    ehl.append(Level(price=h1, level_type='equal_highs', strength=0.7, timestamp=datetime.now()))
                    break

        # Find equal lows
        for i, l1 in enumerate(swing_lows):
            for l2 in swing_lows[i+1:]:
                if abs(l1 - l2) / l1 < 0.001:
                    ehl.append(Level(price=l1, level_type='equal_lows', strength=0.7, timestamp=datetime.now()))
                    break

        return ehl[:4]

    def _check_choch(self, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """Check for Change of Character"""
        if len(close) < 20:
            return False

        trend = self._get_trend(high, low, close)

        # CHoCH: price breaks opposite structure
        recent_high = high.rolling(10).max().iloc[-1]
        recent_low = low.rolling(10).min().iloc[-1]
        prev_high = high.rolling(10).max().iloc[-5]
        prev_low = low.rolling(10).min().iloc[-5]

        if trend == 'bullish' and close.iloc[-1] < prev_low:
            return True
        elif trend == 'bearish' and close.iloc[-1] > prev_high:
            return True

        return False

    def _check_mss(self, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """Check for Market Structure Shift"""
        if len(close) < 20:
            return False

        # MSS: Higher timeframe structure broken
        hh = high.rolling(20).max().iloc[-1]
        hl = low.rolling(20).min().iloc[-1]
        prev_hh = high.rolling(20).max().iloc[-10]
        prev_hl = low.rolling(20).min().iloc[-10]

        if close.iloc[-1] > prev_hh and close.iloc[-5] < prev_hh:
            return True
        if close.iloc[-1] < prev_hl and close.iloc[-5] > prev_hl:
            return True

        return False

    def _get_trend(self, high: pd.Series, low: pd.Series, close: pd.Series) -> str:
        """Get current trend"""
        if len(close) < 20:
            return 'neutral'

        hh = high.rolling(10).max().iloc[-1]
        hl = low.rolling(10).min().iloc[-1]
        ll = low.rolling(10).min().iloc[-1]
        lh = high.rolling(10).min().iloc[-1]

        prev_hh = high.rolling(10).max().iloc[-2]
        prev_hl = low.rolling(10).min().iloc[-2]

        if hh > prev_hh and hl > prev_hl:
            return 'bullish'
        elif ll < prev_hl and lh < prev_hh:
            return 'bearish'
        return 'neutral'


class FibonacciAnalyzer:
    """Fibonacci retracements and extensions analyzer"""

    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> FibonacciSignal:
        """Analyze using Fibonacci levels"""

        if len(close) < 50:
            return FibonacciSignal(
                signal_type=SignalType.HOLD,
                retracement_level=0,
                extension_level=0,
                golden_pocket=False,
                confluence_score=0,
                entry_zone=(close.iloc[-1], close.iloc[-1]),
                stop_loss=close.iloc[-1] * 0.98,
                take_profit=(close.iloc[-1] * 1.02, close.iloc[-1] * 1.05)
            )

        # Find swing high and swing low using numpy
        high_arr = high.values
        low_arr = low.values
        close_arr = close.values

        # Find swing high index
        swing_high_val = np.max(high_arr[-50:])
        swing_high_idx = np.argmax(high_arr[-50:]) + len(high_arr) - 50

        # Find swing low index
        swing_low_val = np.min(low_arr[-50:])
        swing_low_idx = np.argmin(low_arr[-50:]) + len(low_arr) - 50

        # Determine direction
        if swing_high_idx > swing_low_idx:
            # Uptrend - measure retracement from high
            move_high = swing_high_val
            move_low = swing_low_val
            current = close.iloc[-1]

            retracements = [0.236, 0.382, 0.500, 0.618, 0.786]
            extensions = [1.272, 1.414, 1.618, 2.000, 2.618]

            # Calculate retracement levels
            move_size = move_high - move_low
            retracement_levels = [move_high - r * move_size for r in retracements]

            # Check if in golden pocket (0.618-0.786)
            golden_pocket = 0.618 <= (move_high - current) / move_size <= 0.786

            # Fibonacci signal
            if current > move_high - 0.236 * move_size:
                signal_type = SignalType.BUY
            elif current < move_low + 0.786 * move_size:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD

            # Extension targets
            extension_levels = [current + (current - move_low) * e for e in extensions[:3]]

            # Confluence score
            confluence = 0.5
            if golden_pocket:
                confluence += 0.3
            if current > close.rolling(20).mean().iloc[-1]:
                confluence += 0.1

        else:
            # Downtrend
            move_high = swing_low_val
            move_low = swing_high_val
            current = close.iloc[-1]

            retracements = [0.236, 0.382, 0.500, 0.618, 0.786]
            extensions = [1.272, 1.414, 1.618, 2.000, 2.618]

            move_size = move_low - move_high
            retracement_levels = [move_low + r * move_size for r in retracements]

            golden_pocket = 0.618 <= (current - move_low) / move_size <= 0.786

            if current < move_low + 0.236 * move_size:
                signal_type = SignalType.SELL
            elif current > move_high - 0.786 * move_size:
                signal_type = SignalType.BUY
            else:
                signal_type = SignalType.HOLD

            extension_levels = [current - (move_low - current) * e for e in extensions[:3]]

            confluence = 0.5
            if golden_pocket:
                confluence += 0.3
            if current < close.rolling(20).mean().iloc[-1]:
                confluence += 0.1

        return FibonacciSignal(
            signal_type=signal_type,
            retracement_level=retracement_levels[2],  # 0.500
            extension_level=extensions[2],  # 1.618
            golden_pocket=golden_pocket,
            confluence_score=confluence,
            entry_zone=(retracement_levels[2], retracement_levels[3]),
            stop_loss=retracement_levels[4] * 0.99 if signal_type == SignalType.BUY else retracement_levels[0] * 1.01,
            take_profit=(extension_levels[0], extension_levels[1])
        )


class SNRAnalyzer:
    """Support and Resistance analyzer"""

    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> Dict:
        """Analyze support and resistance levels"""

        supports = []
        resistances = []

        # Find swing lows for support
        for i in range(10, len(low)-10):
            if low.iloc[i] <= low.iloc[i-5:i].min() and low.iloc[i] <= low.iloc[i+1:i+11].min():
                strength = 0.5 + (high.iloc[i:i+20].max() - low.iloc[i]) / (high.iloc[i:i+20].max() - low.iloc[i:i+20].min() + 0.001) * 0.5
                supports.append({
                    'price': low.iloc[i],
                    'strength': min(1, strength),
                    'touches': sum(1 for p in low[-50:] if abs(p - low.iloc[i]) / low.iloc[i] < 0.005)
                })

        # Find swing highs for resistance
        for i in range(10, len(high)-10):
            if high.iloc[i] >= high.iloc[i-5:i].max() and high.iloc[i] >= high.iloc[i+1:i+11].max():
                strength = 0.5 + (high.iloc[i] - low.iloc[i:i+20].min()) / (high.iloc[i:i+20].max() - low.iloc[i:i+20].min() + 0.001) * 0.5
                resistances.append({
                    'price': high.iloc[i],
                    'strength': min(1, strength),
                    'touches': sum(1 for p in high[-50:] if abs(p - high.iloc[i]) / high.iloc[i] < 0.005)
                })

        # Sort by strength
        supports = sorted(supports, key=lambda x: x['strength'] * x['touches'], reverse=True)[:5]
        resistances = sorted(resistances, key=lambda x: x['strength'] * x['touches'], reverse=True)[:5]

        return {
            'support': supports,
            'resistance': resistances,
            'pivot': (high.rolling(20).max().iloc[-1] + low.rolling(20).min().iloc[-1] + close.iloc[-1]) / 3
        }


class VolumeProfileAnalyzer:
    """Volume Profile analyzer"""

    def analyze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> Dict:
        """Analyze volume profile"""

        if len(close) < 50:
            return {'poc': close.iloc[-1], 'vah': close.iloc[-1], 'val': close.iloc[-1]}

        # Calculate price bins
        price_range = high.max() - low.min()
        num_bins = 50
        bin_size = price_range / num_bins

        # Create price bins
        bins = np.arange(low.min(), high.max(), bin_size)

        # Calculate volume per bin
        vol_per_bin = np.zeros(len(bins))
        for i in range(len(close)):
            bin_idx = int((close.iloc[i] - low.min()) / bin_size)
            if 0 <= bin_idx < len(bins):
                vol_per_bin[bin_idx] += volume.iloc[i]

        # Find POC (Point of Control)
        poc_idx = np.argmax(vol_per_bin)
        poc = bins[poc_idx]

        # Find VAH and VAL (Value Area High/Low - 70%)
        total_vol = np.sum(vol_per_bin)
        target_vol = total_vol * 0.70
        cumsum = np.cumsum(vol_per_bin)

        vah_idx = np.searchsorted(cumsum, (cumsum[poc_idx] + target_vol / 2).clip(0, total_vol))
        val_idx = np.searchsorted(cumsum, (cumsum[poc_idx] - target_vol / 2).clip(0, total_vol))

        vah = bins[min(vah_idx, len(bins)-1)]
        val = bins[max(val_idx, 0)]

        return {
            'poc': float(poc),
            'vah': float(vah),
            'val': float(val),
            'vol_per_bin': vol_per_bin.tolist(),
            'bins': bins.tolist()
        }


# Convenience function
def analyze_market(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    symbol: str = "UNKNOWN"
) -> UnifiedSignal:
    """
    Perform comprehensive retail strategy analysis

    Usage:
    >>> data = get_market_data('BTCUSDT')
    >>> signal = analyze_market(data['high'], data['low'], data['close'], data['volume'])
    >>> print(f"Signal: {signal.direction}, Score: {signal.score}")
    """
    analyzer = RetailStrategyAnalyzer()
    return analyzer.analyze(high, low, close, volume, symbol)
