"""Tests for config module."""

import pytest
import os
from quant_nanggroe.config.settings import Settings


class TestSettings:
    def test_default_settings(self):
        settings = Settings()
        assert settings.app_name == "Quant Nanggroe AI"
        assert settings.version == "0.1.0"
        assert settings.debug is False

    def test_constitutional_risk_limits(self):
        settings = Settings()
        assert settings.risk_max_per_trade == 0.5
        assert settings.risk_max_daily_loss == 1.0
        assert settings.risk_max_weekly_loss == 3.0
        assert settings.risk_max_drawdown == 10.0

    def test_log_level_validation(self):
        settings = Settings(log_level="DEBUG")
        assert settings.log_level == "DEBUG"

    def test_invalid_log_level(self):
        with pytest.raises(Exception):
            Settings(log_level="INVALID")

    def test_env_override(self):
        os.environ["QNAI_DEBUG"] = "true"
        try:
            settings = Settings()
            assert settings.debug is True
        finally:
            del os.environ["QNAI_DEBUG"]
