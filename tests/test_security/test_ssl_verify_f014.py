"""F014: QNAI_SSL_VERIFY=0 must only be effective in dev."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from typing import Dict

import pytest


ROOT = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
FILES = [
    ROOT / "quant_nanggroe" / "engine_bridge.py",
    ROOT / "quant_nanggroe" / "backtest" / "backtester.py",
    ROOT / "quant_nanggroe" / "data" / "providers" / "data_manager.py",
]


def _ensure_pkg(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


def _make_stub(mod_name: str, attrs: Dict[str, object]) -> types.ModuleType:
    mod = _ensure_pkg(mod_name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _prep_data_manager_import():
    """Mock the relative imports inside data_manager.py."""
    # Ensure parent packages exist
    _ensure_pkg("quant_nanggroe")
    _ensure_pkg("quant_nanggroe.data")
    _ensure_pkg("quant_nanggroe.data.providers")

    # Stub provider modules imported by data_manager
    _make_stub("quant_nanggroe.data.providers.crypto_provider", {"CryptoProvider": object})
    _make_stub("quant_nanggroe.data.providers.finnhub_provider", {"FinnhubProvider": object})
    _make_stub("quant_nanggroe.data.providers.macro_provider", {"MacroProvider": object})


def _load(path: pathlib.Path):
    name = ".".join(path.relative_to(ROOT).with_suffix("").parts)
    if name in sys.modules:
        del sys.modules[name]
    if path == ROOT / "quant_nanggroe" / "data" / "providers" / "data_manager.py":
        _prep_data_manager_import()
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None:
        raise RuntimeError(f"spec_from_file_location failed for {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _ssl_ctx(path: pathlib.Path):
    mod = _load(path)
    assert hasattr(mod, "_ssl_ctx"), f"_ssl_ctx missing in {path}"
    return mod._ssl_ctx()


def test_ssl_verify_forced_on_in_prod(monkeypatch):
    monkeypatch.setenv("QNAI_SSL_VERIFY", "0")
    monkeypatch.setenv("QNAI_ENV", "production")
    for p in FILES:
        ctx = _ssl_ctx(p)
        assert ctx.check_hostname is True
        assert ctx.verify_mode == __import__("ssl").CERT_REQUIRED


def test_ssl_verify_allowed_in_dev(monkeypatch):
    monkeypatch.setenv("QNAI_SSL_VERIFY", "0")
    monkeypatch.setenv("QNAI_ENV", "dev")
    for p in FILES:
        ctx = _ssl_ctx(p)
        assert ctx.check_hostname is False
        assert ctx.verify_mode == __import__("ssl").CERT_NONE


def test_ssl_verify_defaults_to_required(monkeypatch):
    monkeypatch.delenv("QNAI_SSL_VERIFY", raising=False)
    monkeypatch.delenv("QNAI_ENV", raising=False)
    for p in FILES:
        ctx = _ssl_ctx(p)
        assert ctx.check_hostname is True
        assert ctx.verify_mode == __import__("ssl").CERT_REQUIRED
