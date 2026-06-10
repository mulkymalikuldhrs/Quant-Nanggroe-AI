"""Comprehensive tests for Settings module.

Tests:
- Default values
- Environment variable loading
- Log level validation
- Constitutional risk limit validation
- get_settings caching
"""

from __future__ import annotations

import os
import pytest
from pydantic import ValidationError

from quant_nanggroe.config.settings import Settings, get_settings


class TestSettingsDefaults:
    """Test default values for Settings."""

    def test_app_name(self):
        s = Settings()
        assert s.app_name == "Quant Nanggroe AI"

    def test_version(self):
        s = Settings()
        assert s.version == "0.1.0"

    def test_debug_default_false(self):
        s = Settings()
        assert s.debug is False

    def test_database_url_default(self):
        s = Settings()
        assert "sqlite" in s.database_url

    def test_redis_url_default_none(self):
        s = Settings()
        assert s.redis_url is None

    def test_api_keys_default_none(self):
        s = Settings()
        assert s.openai_api_key is None
        assert s.anthropic_api_key is None
        assert s.google_api_key is None
        assert s.alpaca_api_key is None

    def test_llm_defaults(self):
        s = Settings()
        assert s.default_llm_provider == "openai"
        assert s.default_llm_model == "gpt-4o"
        assert s.default_llm_temperature == 0.0

    def test_log_level_default(self):
        # Clear any env override to test default
        old = os.environ.pop("QNAI_LOG_LEVEL", None)
        try:
            s = Settings()
            assert s.log_level == "INFO"
        finally:
            if old is not None:
                os.environ["QNAI_LOG_LEVEL"] = old

    def test_log_format_default(self):
        s = Settings()
        assert s.log_format == "json"

    def test_alpaca_paper_default(self):
        s = Settings()
        assert s.alpaca_paper is True


class TestConstitutionalRiskLimits:
    """Test constitutional risk limit defaults and validation."""

    def test_risk_max_per_trade_default(self):
        s = Settings()
        assert s.risk_max_per_trade == 0.5

    def test_risk_max_daily_loss_default(self):
        s = Settings()
        assert s.risk_max_daily_loss == 1.0

    def test_risk_max_weekly_loss_default(self):
        s = Settings()
        assert s.risk_max_weekly_loss == 3.0

    def test_risk_max_drawdown_default(self):
        s = Settings()
        assert s.risk_max_drawdown == 10.0

    def test_risk_per_trade_minimum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_per_trade=0.05)  # Below 0.1

    def test_risk_per_trade_maximum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_per_trade=3.0)  # Above 2.0

    def test_risk_daily_loss_minimum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_daily_loss=0.3)  # Below 0.5

    def test_risk_daily_loss_maximum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_daily_loss=6.0)  # Above 5.0

    def test_risk_weekly_loss_minimum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_weekly_loss=0.5)  # Below 1.0

    def test_risk_weekly_loss_maximum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_weekly_loss=15.0)  # Above 10.0

    def test_risk_drawdown_minimum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_drawdown=4.0)  # Below 5.0

    def test_risk_drawdown_maximum(self):
        with pytest.raises(ValidationError):
            Settings(risk_max_drawdown=25.0)  # Above 20.0


class TestLogLevelValidation:
    """Test log level validation."""

    def test_valid_log_levels(self):
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            s = Settings(log_level=level)
            assert s.log_level == level

    def test_invalid_log_level(self):
        with pytest.raises(ValidationError):
            Settings(log_level="INVALID")

    def test_log_level_case_insensitive(self):
        s = Settings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_log_level_mixed_case(self):
        s = Settings(log_level="Info")
        assert s.log_level == "INFO"


class TestEnvironmentVariableLoading:
    """Test that settings load from environment variables."""

    def test_env_prefix(self):
        """Settings should use QNAI_ prefix for env vars."""
        assert Settings.model_config.get("env_prefix") == "QNAI_"

    def test_env_file_configured(self):
        """Settings should load from .env file."""
        assert Settings.model_config.get("env_file") == ".env"

    def test_case_insensitive_env(self):
        """Environment variables should be case-insensitive."""
        assert Settings.model_config.get("case_sensitive") is False

    def test_extra_env_vars_ignored(self):
        """Extra environment variables should be ignored."""
        assert Settings.model_config.get("extra") == "ignore"


class TestBacktestSettings:
    """Test backtest default settings."""

    def test_default_commission(self):
        s = Settings()
        assert s.backtest_default_commission == 0.001

    def test_default_slippage(self):
        s = Settings()
        assert s.backtest_default_slippage == 0.0005

    def test_default_initial_capital(self):
        s = Settings()
        assert s.backtest_default_initial_capital == 100000.0


class TestDataSettings:
    """Test data-related settings."""

    def test_cache_ttl(self):
        s = Settings()
        assert s.data_cache_ttl == 300

    def test_provider_timeout(self):
        s = Settings()
        assert s.data_provider_timeout == 30


class TestGetSettings:
    """Test the get_settings cached factory."""

    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_cached_instance(self):
        """get_settings should return the same cached instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
