"""Regression tests for connectors.mt5_broker.MT5Broker.connect().

User mandate 2026-08-20: QNA must trade whatever account is ALREADY logged
into the MT5 terminal — never force a credential login that switches/breaks
the active session (root cause of "wrong account" trades, e.g. Exness #999 or
ValetaxIntl_Live-2 instead of the real ValetaxIntl-Live2 #372044706).

These tests mock the MetaTrader5 module only — no real terminal.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from quant_nanggroe.connectors.mt5_broker import MT5Broker


def _active_account_info(login=372044706, server="ValetaxIntl-Live2"):
    info = MagicMock()
    info.login = login
    info.server = server
    return info


def _make_mock_mt5(account_info=None, init_ok=True):
    mt5 = MagicMock()
    mt5.initialize.return_value = init_ok
    mt5.account_info.return_value = account_info
    mt5.last_error.return_value = (0, "No error")
    mt5.shutdown.return_value = None
    # constants used elsewhere (kept minimal for connect() path)
    mt5.TRADE_ACTION_DEAL = 1
    mt5.ORDER_TYPE_BUY = 0
    mt5.ORDER_TYPE_SELL = 1
    mt5.ORDER_FILLING_FOK = 2
    mt5.ORDER_TIME_GTC = 0
    mt5.TRADE_RETCODE_DONE = 10009
    return mt5


def test_connect_attaches_to_already_logged_in_account():
    """Wrong login passed, but terminal already authenticated -> adopt active."""
    mock = _make_mock_mt5(account_info=_active_account_info())
    with patch.dict("sys.modules", {"MetaTrader5": mock}):
        broker = MT5Broker(login=999, password="x", server="Exness-MT5Real2")
        assert broker.connect() is True
        # MUST adopt the active terminal account, NOT the bogus passed login.
        assert broker.login == 372044706
        assert broker.server == "ValetaxIntl-Live2"
        assert broker.connected is True


def test_connect_uses_active_account_when_no_creds_passed():
    """No login supplied, terminal already logged in -> attach, no raise."""
    mock = _make_mock_mt5(account_info=_active_account_info())
    with patch.dict("sys.modules", {"MetaTrader5": mock}):
        broker = MT5Broker()  # login defaults to 0
        assert broker.connect() is True
        assert broker.login == 372044706


def test_connect_raises_when_not_logged_in_and_no_login():
    """No active session AND no credentials -> fail-closed (no trades)."""
    mock = _make_mock_mt5(account_info=None)  # terminal up but not authenticated
    with patch.dict("sys.modules", {"MetaTrader5": mock}):
        broker = MT5Broker()  # login=0, no creds
        try:
            broker.connect()
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "no login provided" in str(e)


def test_connect_falls_back_to_credential_login_when_terminal_not_authed():
    """Terminal running but not logged in -> use supplied creds."""
    mock = _make_mock_mt5(account_info=None)
    with patch.dict("sys.modules", {"MetaTrader5": mock}):
        broker = MT5Broker(login=372044706, password="secret", server="ValetaxIntl-Live2")
        assert broker.connect() is True
        # credential-login branch: initialize called WITH login
        _, kwargs = mock.initialize.call_args
        assert kwargs.get("login") == 372044706
