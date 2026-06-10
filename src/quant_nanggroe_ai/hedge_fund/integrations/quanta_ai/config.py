"""
⚡ QUANTA AI - Configuration Management System
==============================================
Centralized configuration with environment support, dynamic loading,
and institutional-grade settings management.

Author: Quanta AI Team
Version: 2.0.0
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib


class MarketRegime(Enum):
    """Market regime classification for adaptive trading."""
    BULL_STRONG = "bull_strong"      # Strong uptrend
    BULL_WEAK = "bull_weak"          # Weak uptrend
    BEAR_STRONG = "bear_strong"      # Strong downtrend
    BEAR_WEAK = "bear_weak"          # Weak downtrend
    SIDEWAYS_LOW = "sideways_low"    # Range-bound, low volatility
    SIDEWAYS_HIGH = "sideways_high"  # Range-bound, high volatility
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk tolerance levels."""
    CONSERVATIVE = "conservative"    # Low risk, stable returns
    MODERATE = "moderate"            # Balanced risk/return
    AGGRESSIVE = "aggressive"        # High risk, high returns
    INSTITUTIONAL = "institutional"  # Institutional-grade risk management


class StrategyMode(Enum):
    """Trading strategy modes."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"
    POSITION = "position"
    ADAPTIVE = "adaptive"
    ENSEMBLE = "ensemble"


class ExecutionMode(Enum):
    """Order execution modes."""
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    SMART = "smart"
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"


@dataclass
class APIConfig:
    """API configurations for data sources."""
    yahoo_finance: bool = True
    yahoo_interval: str = "1d"
    binance: bool = True
    binance_testnet: bool = False
    alpha_vantage: str = ""
    polygon: str = ""
    finnhub: str = ""
    twitter: str = ""
    newsapi: str = ""
    crypto_compare: str = ""
    
    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled data sources."""
        sources = []
        if self.yahoo_finance:
            sources.append('yahoo')
        if self.binance:
            sources.append('binance')
        if self.alpha_vantage:
            sources.append('alpha_vantage')
        if self.polygon:
            sources.append('polygon')
        return sources


@dataclass
class ModelConfig:
    """ML model configurations."""
    # Transformer model settings
    transformer_heads: int = 8
    transformer_layers: int = 6
    hidden_dim: int = 256
    feed_forward_dim: int = 512
    dropout: float = 0.1
    
    # Sequence settings
    sequence_length: int = 128
    prediction_horizon: int = 5
    min_sequence_length: int = 20
    
    # Confidence settings
    confidence_threshold: float = 0.65
    min_confidence: float = 0.5
    ensemble_size: int = 5
    
    # Training settings
    learning_rate: float = 1e-4
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10
    
    # Feature settings
    feature_dim: int = 50
    embedding_dim: int = 64
    
    def get_model_hash(self) -> str:
        """Generate hash for model configuration."""
        config_str = json.dumps({
            'heads': self.transformer_heads,
            'layers': self.transformer_layers,
            'hidden': self.hidden_dim,
            'seq_len': self.sequence_length,
            'horizon': self.prediction_horizon
        }, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]


@dataclass
class TradingConfig:
    """Trading-related configurations."""
    # Capital management
    initial_capital: float = 100000.0
    min_capital: float = 10000.0
    max_capital: float = 10000000.0
    
    # Position management
    max_position_size: float = 0.20
    min_position_size: float = 0.01
    max_leverage: float = 2.0
    max_positions: int = 10
    
    # Risk limits
    max_drawdown_limit: float = 0.15
    max_daily_loss: float = 0.03
    max_correlation: float = 0.8
    max_concentration: float = 0.15
    
    # Execution settings
    transaction_cost: float = 0.001
    slippage_model: str = "adaptive"
    execution_style: ExecutionMode = ExecutionMode.SMART
    execution_timeout: float = 30.0
    
    # Trading hours
    trading_hours_only: bool = False
    pre_market: bool = False
    after_hours: bool = False
    
    # Strategy
    default_strategy: StrategyMode = StrategyMode.ENSEMBLE
    adaptive_strategy: bool = True
    regime_detection: bool = True
    
    def calculate_position_size(self, capital: float, risk_per_trade: float = 0.02) -> float:
        """Calculate recommended position size."""
        return min(capital * self.max_position_size, capital * risk_per_trade)


@dataclass
class RiskConfig:
    """Risk management configurations."""
    # VaR settings
    var_confidence: float = 0.95
    var_horizon: int = 1  # days
    
    # CVaR settings
    cvar_confidence: float = 0.99
    
    # Stress testing
    stress_test_enabled: bool = True
    stress_scenarios: List[str] = field(default_factory=lambda: [
        '2008_crisis',
        'covid_crash',
        'rate_shock',
        'flash_crash',
        'volatility_spike'
    ])
    
    # Limits
    risk_level: RiskLevel = RiskLevel.MODERATE
    stop_loss_default: float = 0.05
    trailing_stop: bool = True
    trailing_stop_distance: float = 0.02
    
    # Alerts
    risk_alerts_enabled: bool = True
    alert_threshold_warning: float = 0.10
    alert_threshold_critical: float = 0.20
    
    def get_var_percentile(self) -> float:
        """Get VaR percentile based on confidence."""
        return (1 - self.var_confidence) * 100


@dataclass
class AgentConfig:
    """Agent coordination configurations."""
    # Timing
    heartbeat_interval: float = 1.0
    decision_timeout: float = 10.0
    message_timeout: float = 30.0
    retry_delay: float = 1.0
    
    # Retries
    max_retries: int = 3
    max_message_retries: int = 5
    
    # Consensus
    consensus_threshold: float = 0.70
    voting_enabled: bool = True
    weighted_voting: bool = True
    
    # Learning
    agent_learning_enabled: bool = True
    performance_window: int = 100
    adaptation_rate: float = 0.1
    
    # Scalability
    max_concurrent_tasks: int = 10
    task_queue_size: int = 1000


@dataclass
class FeatureConfig:
    """Feature engineering configurations."""
    # Technical indicators
    enable_technicals: bool = True
    technical_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 50, 100, 200])
    
    # Volume features
    enable_volume: bool = True
    volume_lookback: int = 20
    
    # Volatility features
    enable_volatility: bool = True
    volatility_lookback: int = 20
    
    # Sentiment features
    enable_sentiment: bool = True
    sentiment_lookback: int = 10
    
    # On-chain features (for crypto)
    enable_onchain: bool = True
    onchain_lookback: int = 7
    
    # Fundamental features
    enable_fundamental: bool = False
    
    # Feature scaling
    normalize_features: bool = True
    handle_outliers: bool = True
    outlier_threshold: float = 3.0
    
    def get_feature_count(self) -> int:
        """Calculate total number of features."""
        count = 0
        if self.enable_technicals:
            count += len(self.technical_periods) * 10  # ~10 indicators per period
        if self.enable_volume:
            count += 5
        if self.enable_volatility:
            count += 5
        if self.enable_sentiment:
            count += 3
        if self.enable_onchain:
            count += 5
        if self.enable_fundamental:
            count += 10
        return count


@dataclass
class QuantaConfig:
    """Main configuration class for Quanta AI System."""
    
    # System identification
    system_name: str = "Quanta AI"
    system_id: str = field(default_factory=lambda: f"quanta_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    version: str = "2.0.0"
    environment: str = "development"  # development, staging, production
    
    # Logging
    log_level: str = "INFO"
    debug_mode: bool = False
    log_performance: bool = True
    
    # API configurations
    api: APIConfig = field(default_factory=APIConfig)
    
    # Model configurations  
    model: ModelConfig = field(default_factory=ModelConfig)
    
    # Trading configurations
    trading: TradingConfig = field(default_factory=TradingConfig)
    
    # Risk configurations
    risk: RiskConfig = field(default_factory=RiskConfig)
    
    # Agent configurations
    agents: AgentConfig = field(default_factory=AgentConfig)
    
    # Feature configurations
    features: FeatureConfig = field(default_factory=FeatureConfig)
    
    # Paths
    data_path: str = "~/quanta_data"
    model_path: str = "~/quanta_models"
    log_path: str = "~/quanta_logs"
    cache_path: str = "~/quanta_cache"
    
    # Market settings
    market_regime: MarketRegime = MarketRegime.UNKNOWN
    last_regime_update: datetime = field(default_factory=datetime.now)
    
    def load_from_env(self) -> 'QuantaConfig':
        """Load configuration from environment variables."""
        env_mappings = {
            'QUANTA_INITIAL_CAPITAL': ('trading', 'initial_capital', float),
            'QUANTA_MAX_POSITION': ('trading', 'max_position_size', float),
            'QUANTA_MAX_DRAWDOWN': ('trading', 'max_drawdown_limit', float),
            'QUANTA_VAR_CONFIDENCE': ('risk', 'var_confidence', float),
            'QUANTA_LOG_LEVEL': ('system', 'log_level', str),
            'QUANTA_DEBUG': ('system', 'debug_mode', bool),
            'QUANTA_ENVIRONMENT': ('system', 'environment', str),
            'QUANTA_HEARTBEAT': ('agents', 'heartbeat_interval', float),
        }
        
        for env_var, (section, key, type_) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                if type_ == bool:
                    value = value.lower() in ('true', '1', 'yes')
                elif type_ == float:
                    value = float(value)
                else:
                    value = type_(value)
                self._set_nestedattr(section, key, value)
        
        return self
    
    def _set_nestedattr(self, section: str, key: str, value: Any) -> None:
        """Set nested attribute."""
        section_obj = getattr(self, section)
        setattr(section_obj, key, value)
    
    def load_from_file(self, filepath: str) -> 'QuantaConfig':
        """Load configuration from JSON file."""
        path = Path(filepath)
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                self._apply_dict(data)
        return self
    
    def _apply_dict(self, data: Dict[str, Any]) -> None:
        """Apply dictionary to configuration."""
        for section, values in data.items():
            if hasattr(self, section):
                section_obj = getattr(self, section)
                if isinstance(section_obj, dict):
                    section_obj.update(values)
                elif hasattr(section_obj, '__dataclass_fields__'):
                    for key, value in values.items():
                        if hasattr(section_obj, key):
                            setattr(section_obj, key, value)
    
    def save_to_file(self, filepath: str) -> None:
        """Save configuration to JSON file."""
        config_dict = {
            'system': {
                'system_name': self.system_name,
                'system_id': self.system_id,
                'version': self.version,
                'environment': self.environment,
                'log_level': self.log_level,
                'debug_mode': self.debug_mode
            },
            'trading': {
                'initial_capital': self.trading.initial_capital,
                'max_position_size': self.trading.max_position_size,
                'max_leverage': self.trading.max_leverage,
                'max_drawdown_limit': self.trading.max_drawdown_limit,
                'stop_loss_default': self.trading.stop_loss_default,
                'transaction_cost': self.trading.transaction_cost,
            },
            'risk': {
                'var_confidence': self.risk.var_confidence,
                'cvar_confidence': self.risk.cvar_confidence,
                'risk_level': self.risk.risk_level.value,
            },
            'model': {
                'transformer_heads': self.model.transformer_heads,
                'transformer_layers': self.model.transformer_layers,
                'hidden_dim': self.model.hidden_dim,
                'sequence_length': self.model.sequence_length,
                'prediction_horizon': self.model.prediction_horizon,
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'system': {
                'name': self.system_name,
                'id': self.system_id,
                'version': self.version,
                'environment': self.environment,
                'log_level': self.log_level,
                'debug_mode': self.debug_mode
            },
            'trading': {
                'initial_capital': self.trading.initial_capital,
                'max_position_size': self.trading.max_position_size,
                'max_drawdown_limit': self.trading.max_drawdown_limit,
            },
            'risk': {
                'var_confidence': self.risk.var_confidence,
                'risk_level': self.risk.risk_level.value,
            },
            'features': {
                'total_features': self.features.get_feature_count(),
                'technical_periods': self.features.technical_periods,
            }
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        return {
            'name': self.system_name,
            'version': self.version,
            'environment': self.environment,
            'enabled_data_sources': self.api.get_enabled_sources(),
            'model_config_hash': self.model.get_model_hash(),
            'feature_count': self.features.get_feature_count(),
            'total_agents': 8,  # Base agents
        }


# Global configuration instance
_config: Optional['QuantaConfig'] = None

def get_config() -> QuantaConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = QuantaConfig()
        _config.load_from_env()
    return _config

def set_config(config: QuantaConfig) -> None:
    """Set global configuration instance."""
    global _config
    _config = config

def create_config(**kwargs) -> QuantaConfig:
    """Create a new configuration with optional overrides."""
    config = QuantaConfig()
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config
