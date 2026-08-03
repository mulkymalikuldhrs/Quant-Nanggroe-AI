"""F014: QNAI_SSL_VERIFY=0 must only be effective in dev."""
from __future__ import annotations

import pytest

import quant_nanggroe.engine_bridge as engine_bridge_mod
import quant_nanggroe.backtest.backtester as backtester_mod
import quant_nanggroe.data.providers.data_manager as data_manager_mod


@pytest.mark.parametrize(
    "mod", [engine_bridge_mod, backtester_mod, data_manager_mod],
    ids=["engine_bridge", "backtester", "data_manager"],
)
def test_ssl_verify_forced_on_in_prod(monkeypatch, mod):
    monkeypatch.setenv("QNAI_SSL_VERIFY", "0")
    monkeypatch.setenv("QNAI_ENV", "production")
    ctx = mod._ssl_ctx()
    assert ctx.check_hostname is True
    assert ctx.verify_mode == __import__("ssl").CERT_REQUIRED


@pytest.mark.parametrize(
    "mod", [engine_bridge_mod, backtester_mod, data_manager_mod],
    ids=["engine_bridge", "backtester", "data_manager"],
)
def test_ssl_verify_allowed_in_dev(monkeypatch, mod):
    monkeypatch.setenv("QNAI_SSL_VERIFY", "0")
    monkeypatch.setenv("QNAI_ENV", "dev")
    ctx = mod._ssl_ctx()
    assert ctx.check_hostname is False
    assert ctx.verify_mode == __import__("ssl").CERT_NONE


@pytest.mark.parametrize(
    "mod", [engine_bridge_mod, backtester_mod, data_manager_mod],
    ids=["engine_bridge", "backtester", "data_manager"],
)
def test_ssl_verify_defaults_to_required(monkeypatch, mod):
    monkeypatch.delenv("QNAI_SSL_VERIFY", raising=False)
    monkeypatch.delenv("QNAI_ENV", raising=False)
    ctx = mod._ssl_ctx()
    assert ctx.check_hostname is True
    assert ctx.verify_mode == __import__("ssl").CERT_REQUIRED
