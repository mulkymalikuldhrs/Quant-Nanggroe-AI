"""Tests for TelegramSignalBot.alert_on_fail (C4 failure alert)."""

import json
import os
import urllib.request
from unittest import mock

import pytest

from quant_nanggroe.agents.telegram_bot import TelegramSignalBot


@pytest.fixture
def fake_urlopen():
    """Capture the Telegram sendMessage POST and return ok=True."""
    captured = {}

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(self._payload).encode()

    def _send(req, timeout=10):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        captured["headers"] = dict(req.headers)
        return _Resp({"ok": True, "result": {}})

    with mock.patch.object(urllib.request, "urlopen", _send):
        yield captured


@pytest.fixture(autouse=True)
def telegram_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "FAKE_TOKEN")
    monkeypatch.setenv("TELEGRAM_MULKY_CHAT_ID", "123456_MULKY")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)


def test_alert_targets_mulky_chat(fake_urlopen):
    bot = TelegramSignalBot()
    ok = bot.alert_on_fail("engine_execution", "RuntimeError: boom")
    assert ok is True
    assert fake_urlopen["body"]["chat_id"] == "123456_MULKY"
    assert fake_urlopen["body"]["parse_mode"] == "Markdown"
    assert "engine_execution" in fake_urlopen["body"]["text"]
    assert "RuntimeError: boom" in fake_urlopen["body"]["text"]


def test_cooldown_suppresses_repeat(fake_urlopen):
    bot = TelegramSignalBot()
    assert bot.alert_on_fail("engine_execution", "a") is True
    # Same subsystem within cooldown window -> suppressed, no second HTTP call
    assert bot.alert_on_fail("engine_execution", "b") is False
    # Different subsystem still fires
    assert bot.alert_on_fail("market_data", "c") is True


def test_fallback_to_telegram_chat_id(monkeypatch, fake_urlopen):
    monkeypatch.delenv("TELEGRAM_MULKY_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999_FALLBACK")
    bot = TelegramSignalBot()
    bot.alert_on_fail("x", "y")
    assert fake_urlopen["body"]["chat_id"] == "999_FALLBACK"


def test_unconfigured_token_fails_safe(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    bot = TelegramSignalBot()
    assert bot.alert_on_fail("x", "y") is False


def test_api_error_returns_false():
    captured = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({"ok": False, "description": "Forbidden"}).encode()

    def _send(req, timeout=10):
        captured["body"] = json.loads(req.data.decode())
        return _Resp()

    with mock.patch.object(urllib.request, "urlopen", _send):
        bot = TelegramSignalBot()
        assert bot.alert_on_fail("x", "y") is False


def test_network_failure_returns_false():
    def _send(req, timeout=10):
        raise OSError("network down")

    with mock.patch.object(urllib.request, "urlopen", _send):
        bot = TelegramSignalBot()
        assert bot.alert_on_fail("x", "y") is False
