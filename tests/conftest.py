"""
Pytest Configuration — Shared Fixtures for Quant-Nanggroe-AI Test Suite
=======================================================================
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

# Set test environment BEFORE importing app modules — must match config.py
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_qna.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("QNAI_JWT_SECRET", "test-secret-key-for-pytest")

# ── PRODUCTION STATE ISOLATION (2026-08-25 incident) ─────────────────────
# A test activation ("reason": "test") leaked into data/kill_switch_state.json
# and BLOCKED ALL LIVE TRADING for the rest of the day (same-day level_1 has
# no auto-expiry). Every test process MUST point the cross-process kill
# switch at a throwaway location. Set at import time so it applies even to
# modules that create KillSwitch() during collection.
_KS_TMP = tempfile.mkdtemp(prefix="qna-test-ks-")
os.environ["QNA_KILL_SWITCH_STATE_FILE"] = os.path.join(_KS_TMP, "ks_state.json")
os.environ["QNA_KILL_SWITCH_AUDIT_LOG"] = os.path.join(_KS_TMP, "ks_audit.jsonl")


@pytest.fixture(autouse=True)
def _isolate_kill_switch_file(monkeypatch):
    """Belt-and-suspenders: per-test KS state file, restored after each test.

    NOTE: deliberately NOT using pytest's tmp_path — its shared
    C:\\...\\Temp\\pytest-of-Hi root can be access-denied when it was created
    by an elevated process, which would error every test.
    """
    import shutil
    import tempfile as _tf
    ks_dir = _tf.mkdtemp(prefix="qna-ks-")
    monkeypatch.setenv(
        "QNA_KILL_SWITCH_STATE_FILE", os.path.join(ks_dir, "ks_state.json"))
    monkeypatch.setenv(
        "QNA_KILL_SWITCH_AUDIT_LOG", os.path.join(ks_dir, "ks_audit.jsonl"))
    yield
    shutil.rmtree(ks_dir, ignore_errors=True)


@pytest.fixture
def sample_closes() -> list[float]:
    """100-bar sample close price series for indicator testing."""
    np.random.seed(42)
    # Generate a realistic price series with trend + noise
    returns = np.random.normal(0.0002, 0.015, 100)
    prices = 100.0 * np.cumprod(1 + returns)
    return [round(float(p), 2) for p in prices]


@pytest.fixture
def sample_ohlcv() -> dict[str, list[float]]:
    """100-bar OHLCV sample data."""
    np.random.seed(42)
    returns = np.random.normal(0.0002, 0.015, 100)
    closes = 100.0 * np.cumprod(1 + returns)

    highs = [round(float(c) * (1 + abs(float(np.random.normal(0, 0.005)))), 2) for c in closes]
    lows = [round(float(c) * (1 - abs(float(np.random.normal(0, 0.005)))), 2) for c in closes]
    volumes = [round(float(max(np.random.lognormal(15, 1), 1000)), 0) for _ in range(100)]

    return {
        "opens": [round(float(c) * (1 + float(np.random.normal(0, 0.002))), 2) for c in closes],
        "highs": highs,
        "lows": lows,
        "closes": [round(float(c), 2) for c in closes],
        "volumes": volumes,
    }


@pytest.fixture
def rsi_overbought_closes() -> list[float]:
    """Price series that should produce RSI > 70 (overbought)."""
    return [100.0 + i * 0.5 for i in range(30)]


@pytest.fixture
def rsi_oversold_closes() -> list[float]:
    """Price series that should produce RSI < 30 (oversold)."""
    return [100.0 - i * 0.5 for i in range(30)]


@pytest.fixture
def trending_up_closes() -> list[float]:
    """Strong uptrend price series."""
    return [100.0 + i * 2.0 for i in range(50)]


@pytest.fixture
def ranging_closes() -> list[float]:
    """Sideways/ranging price series."""
    import math
    return [100.0 + 5.0 * math.sin(i * 0.2) for i in range(50)]


@pytest.fixture
def sample_portfolio_state() -> dict:
    """Sample portfolio state for risk management tests."""
    return {
        "total_equity": 100000.0,
        "cash": 60000.0,
        "positions": {
            "AAPL": {"quantity": 50, "entry_price": 180.0, "current_price": 185.0},
            "MSFT": {"quantity": 30, "entry_price": 380.0, "current_price": 375.0},
            "GOOGL": {"quantity": 20, "entry_price": 140.0, "current_price": 145.0},
        },
        "daily_pnl": -150.0,
        "weekly_pnl": 1200.0,
        "max_drawdown_pct": 2.1,
    }


# ── Engine Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def risk_guard():
    """ConstitutionalRiskGuard instance for testing."""
    from quant_nanggroe.engine.risk.checks import RiskCheckGate
    return RiskCheckGate()


@pytest.fixture
def kill_switch():
    """KillSwitch instance for testing."""
    from quant_nanggroe.engine.risk.kill_switch import KillSwitch
    return KillSwitch()
