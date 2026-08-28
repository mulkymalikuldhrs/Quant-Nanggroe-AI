"""Tests: Settings — Pydantic-based configuration, env overrides, field validation.

All tests are deterministic — no network calls or external dependencies.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pydantic_settings import BaseSettings, SettingsConfigDict

from quant_nanggroe.config.settings import Settings, get_settings


class _TestSettings(Settings):
    """Test-only subclass that skips .env file to avoid test interference."""

    model_config = SettingsConfigDict(
        env_prefix="QNAI_",
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )


def _make_settings(**kwargs) -> BaseSettings:
    """Create Settings instance without .env file interference."""
    return _TestSettings(**kwargs)


class _IsolatedEnvTest(unittest.TestCase):
    """Base class that clears QNAI_ env vars before each test and restores them."""

    def setUp(self):
        self._env_backup = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("QNAI_"):
                del os.environ[key]

    def tearDown(self):
        os.environ.clear()
        for k, v in self._env_backup.items():
            os.environ[k] = v


class TestSettingsDefaults(_IsolatedEnvTest):
    def test_app_name_default(self):
        s = _make_settings()
        self.assertEqual(s.app_name, "Quant Nanggroe AI")

    def test_version_default(self):
        s = _make_settings()
        self.assertEqual(s.version, "0.1.0")

    def test_debug_default(self):
        s = _make_settings()
        self.assertFalse(s.debug)

    def test_database_url_default(self):
        s = _make_settings()
        self.assertEqual(s.database_url, "sqlite:///data/agentic.db")

    def test_redis_url_default(self):
        s = _make_settings()
        self.assertIsNone(s.redis_url)

    def test_jwt_secret_default(self):
        s = _make_settings()
        # Sentinel default — NOT a usable secret. Boot is refused with this value.
        self.assertEqual(s.jwt_secret, "__UNSET_QNAI_JWT_SECRET__")

    def test_log_level_default(self):
        s = _make_settings()
        self.assertEqual(s.log_level, "INFO")

    def test_log_format_default(self):
        s = _make_settings()
        self.assertEqual(s.log_format, "json")

    def test_llm_provider_default(self):
        s = _make_settings()
        self.assertEqual(s.default_llm_provider, "openai")

    def test_llm_model_default(self):
        s = _make_settings()
        self.assertEqual(s.default_llm_model, "gpt-4o")

    def test_nvidia_base_url_default(self):
        s = _make_settings()
        self.assertEqual(s.nvidia_base_url, "https://integrate.api.nvidia.com/v1")

    def test_cors_origins_default(self):
        s = _make_settings()
        self.assertIn("http://localhost:3000", s.cors_origins)
        self.assertEqual(len(s.cors_origins), 3)

    def test_cors_methods_default(self):
        s = _make_settings()
        self.assertIn("GET", s.cors_methods)
        self.assertIn("POST", s.cors_methods)

    def test_cors_headers_default(self):
        s = _make_settings()
        self.assertIn("Authorization", s.cors_headers)
        self.assertIn("Content-Type", s.cors_headers)

    def test_data_cache_ttl_default(self):
        s = _make_settings()
        self.assertEqual(s.data_cache_ttl, 300)

    def test_data_provider_timeout_default(self):
        s = _make_settings()
        self.assertEqual(s.data_provider_timeout, 30)

    def test_backtest_commission_default(self):
        s = _make_settings()
        self.assertEqual(s.backtest_default_commission, 0.001)

    def test_backtest_slippage_default(self):
        s = _make_settings()
        self.assertEqual(s.backtest_default_slippage, 0.0005)

    def test_backtest_initial_capital_default(self):
        s = _make_settings()
        self.assertEqual(s.backtest_default_initial_capital, 100000.0)


class TestSettingsRiskLimits(_IsolatedEnvTest):
    def test_risk_max_per_trade_default(self):
        s = _make_settings()
        self.assertEqual(s.risk_max_per_trade, 0.5)

    def test_risk_max_daily_loss_default(self):
        s = _make_settings()
        self.assertEqual(s.risk_max_daily_loss, 1.0)

    def test_risk_max_weekly_loss_default(self):
        s = _make_settings()
        self.assertEqual(s.risk_max_weekly_loss, 3.0)

    def test_risk_max_drawdown_default(self):
        s = _make_settings()
        self.assertEqual(s.risk_max_drawdown, 10.0)


class TestSettingsEnvOverrides(_IsolatedEnvTest):
    def test_env_overrides_app_name(self):
        os.environ["QNAI_APP_NAME"] = "Test App"
        s = _make_settings()
        self.assertEqual(s.app_name, "Test App")

    def test_env_overrides_debug(self):
        os.environ["QNAI_DEBUG"] = "true"
        s = _make_settings()
        self.assertTrue(s.debug)

    def test_env_overrides_database_url(self):
        os.environ["QNAI_DATABASE_URL"] = "postgresql://localhost/mydb"
        s = _make_settings()
        self.assertEqual(s.database_url, "postgresql://localhost/mydb")

    def test_env_overrides_jwt_secret(self):
        os.environ["QNAI_JWT_SECRET"] = "my-production-secret"
        s = _make_settings()
        self.assertEqual(s.jwt_secret, "my-production-secret")

    def test_env_overrides_redis_url(self):
        os.environ["QNAI_REDIS_URL"] = "redis://prod:6379"
        s = _make_settings()
        self.assertEqual(s.redis_url, "redis://prod:6379")

    def test_env_overrides_log_level(self):
        os.environ["QNAI_LOG_LEVEL"] = "DEBUG"
        s = _make_settings()
        self.assertEqual(s.log_level, "DEBUG")

    def test_env_overrides_risk_max_per_trade(self):
        os.environ["QNAI_RISK_MAX_PER_TRADE"] = "1.5"
        s = _make_settings()
        self.assertEqual(s.risk_max_per_trade, 1.5)

    def test_env_overrides_risk_max_drawdown(self):
        os.environ["QNAI_RISK_MAX_DRAWDOWN"] = "15.0"
        s = _make_settings()
        self.assertEqual(s.risk_max_drawdown, 15.0)

    def test_env_overrides_llm_provider(self):
        os.environ["QNAI_DEFAULT_LLM_PROVIDER"] = "anthropic"
        s = _make_settings()
        self.assertEqual(s.default_llm_provider, "anthropic")

    def test_env_overrides_llm_model(self):
        os.environ["QNAI_DEFAULT_LLM_MODEL"] = "claude-3-opus-20240229"
        s = _make_settings()
        self.assertEqual(s.default_llm_model, "claude-3-opus-20240229")

    def test_env_overrides_alpaca_paper(self):
        os.environ["QNAI_ALPACA_PAPER"] = "false"
        s = _make_settings()
        self.assertFalse(s.alpaca_paper)

    def test_env_overrides_nvidia_base_url(self):
        os.environ["QNAI_NVIDIA_BASE_URL"] = "https://custom.nvidia.com/v1"
        s = _make_settings()
        self.assertEqual(s.nvidia_base_url, "https://custom.nvidia.com/v1")

    def test_env_overrides_cors_origins(self):
        os.environ["QNAI_CORS_ORIGINS"] = '["https://app.example.com"]'
        s = _make_settings()
        self.assertEqual(s.cors_origins, ["https://app.example.com"])

    def test_env_overrides_optional_api_key(self):
        os.environ["QNAI_OPENAI_API_KEY"] = "sk-test123"
        s = _make_settings()
        self.assertEqual(s.openai_api_key, "sk-test123")

    def test_env_overrides_optional_api_key_empty(self):
        os.environ["QNAI_OPENAI_API_KEY"] = ""
        s = _make_settings()
        self.assertEqual(s.openai_api_key, "")

    def test_env_overrides_sec_edgar_email(self):
        os.environ["QNAI_SEC_EDGAR_USER_EMAIL"] = "user@example.com"
        s = _make_settings()
        self.assertEqual(s.sec_edgar_user_email, "user@example.com")

    def test_env_overrides_data_cache_ttl(self):
        os.environ["QNAI_DATA_CACHE_TTL"] = "600"
        s = _make_settings()
        self.assertEqual(s.data_cache_ttl, 600)

    def test_env_overrides_data_provider_timeout(self):
        os.environ["QNAI_DATA_PROVIDER_TIMEOUT"] = "60"
        s = _make_settings()
        self.assertEqual(s.data_provider_timeout, 60)

    def test_env_ignores_unprefixed_vars(self):
        os.environ["UNRELATED_VAR"] = "should-be-ignored"
        s = _make_settings()
        self.assertNotEqual(s.app_name, "should-be-ignored")


class TestSettingsLogLevelValidator(_IsolatedEnvTest):
    def test_valid_log_levels(self):
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            with self.subTest(level=level):
                os.environ["QNAI_LOG_LEVEL"] = level
                s = _make_settings()
                self.assertEqual(s.log_level, level)

    def test_invalid_log_level_raises(self):
        os.environ["QNAI_LOG_LEVEL"] = "TRACE"
        with self.assertRaises(ValueError):
            Settings()

    def test_case_insensitive_log_level(self):
        os.environ["QNAI_LOG_LEVEL"] = "debug"
        s = _make_settings()
        self.assertEqual(s.log_level, "DEBUG")

    def test_invalid_log_level_lowercase_raises(self):
        os.environ["QNAI_LOG_LEVEL"] = "trace"
        with self.assertRaises(ValueError):
            Settings()


class TestSettingsFieldConstraints(_IsolatedEnvTest):
    def test_risk_max_per_trade_ge_0_1(self):
        os.environ["QNAI_RISK_MAX_PER_TRADE"] = "0.05"
        with self.assertRaises(ValueError):
            Settings()

    def test_risk_max_per_trade_le_2_0(self):
        os.environ["QNAI_RISK_MAX_PER_TRADE"] = "3.0"
        with self.assertRaises(ValueError):
            Settings()

    def test_risk_max_daily_loss_ge_0_5(self):
        os.environ["QNAI_RISK_MAX_DAILY_LOSS"] = "0.1"
        with self.assertRaises(ValueError):
            Settings()

    def test_risk_max_daily_loss_le_5_0(self):
        os.environ["QNAI_RISK_MAX_DAILY_LOSS"] = "10.0"
        with self.assertRaises(ValueError):
            Settings()

    def test_risk_max_weekly_loss_ge_1_0(self):
        os.environ["QNAI_RISK_MAX_WEEKLY_LOSS"] = "0.5"
        with self.assertRaises(ValueError):
            Settings()

    def test_risk_max_weekly_loss_le_10_0(self):
        os.environ["QNAI_RISK_MAX_WEEKLY_LOSS"] = "15.0"
        with self.assertRaises(ValueError):
            Settings()

    def test_risk_max_drawdown_ge_5_0(self):
        os.environ["QNAI_RISK_MAX_DRAWDOWN"] = "1.0"
        with self.assertRaises(ValueError):
            Settings()

    def test_risk_max_drawdown_le_20_0(self):
        os.environ["QNAI_RISK_MAX_DRAWDOWN"] = "30.0"
        with self.assertRaises(ValueError):
            Settings()

    def test_boundary_values_are_valid(self):
        os.environ["QNAI_RISK_MAX_PER_TRADE"] = "0.1"
        os.environ["QNAI_RISK_MAX_DRAWDOWN"] = "5.0"
        s = _make_settings()
        self.assertEqual(s.risk_max_per_trade, 0.1)
        self.assertEqual(s.risk_max_drawdown, 5.0)


class TestSettingsOptionalApiKeys(_IsolatedEnvTest):
    def test_api_keys_default_to_none(self):
        s = _make_settings()
        self.assertIsNone(s.alpaca_api_key)
        self.assertIsNone(s.alpaca_api_secret)
        self.assertIsNone(s.binance_api_key)
        self.assertIsNone(s.binance_api_secret)
        self.assertIsNone(s.alpha_vantage_api_key)
        self.assertIsNone(s.polygon_api_key)
        self.assertIsNone(s.fred_api_key)
        self.assertIsNone(s.coingecko_api_key)
        self.assertIsNone(s.finnhub_api_key)
        self.assertIsNone(s.twelvedata_api_key)
        self.assertIsNone(s.sec_edgar_user_email)
        self.assertIsNone(s.ecb_api_key)

    def test_nvidia_keys_default_to_none(self):
        s = _make_settings()
        self.assertIsNone(s.nvidia_api_key)
        self.assertIsNone(s.nvidia_nim_api_key)

    def test_alpaca_paper_defaults_true(self):
        s = _make_settings()
        self.assertTrue(s.alpaca_paper)


class TestSettingsExtraIgnored(_IsolatedEnvTest):
    def test_unknown_env_vars_ignored(self):
        os.environ["QNAI_SOME_UNKNOWN_FIELD"] = "value"
        s = _make_settings()
        self.assertFalse(hasattr(s, "some_unknown_field"))


class TestGetSettings(_IsolatedEnvTest):
    def setUp(self):
        super().setUp()
        get_settings.cache_clear()

    def tearDown(self):
        get_settings.cache_clear()
        super().tearDown()

    def test_get_settings_returns_settings_instance(self):
        s = get_settings()
        self.assertIsInstance(s, Settings)

    def test_get_settings_is_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        self.assertIs(s1, s2)

    def test_get_settings_cache_cleared(self):
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        self.assertIsNot(s1, s2)

    def test_get_settings_new_after_cache_clear(self):
        os.environ["QNAI_APP_NAME"] = "First"
        get_settings.cache_clear()
        s1 = get_settings()
        self.assertEqual(s1.app_name, "First")

        os.environ["QNAI_APP_NAME"] = "Second"
        get_settings.cache_clear()
        s2 = get_settings()
        self.assertEqual(s2.app_name, "Second")


if __name__ == "__main__":
    unittest.main(verbosity=2)
