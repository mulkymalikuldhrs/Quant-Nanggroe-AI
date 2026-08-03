"""F012: Kronos path must be env-driven, no hardcoded Windows path."""
from __future__ import annotations

import os
import importlib
import sys

import pytest


def _reload_kronos_module():
    for name in list(sys.modules):
        if "quant_nanggroe.engine.strategies.kronos_wrapper" == name or name.startswith(
            "quant_nanggroe.engine.strategies.kronos_wrapper."
        ):
            del sys.modules[name]
    return importlib.import_module("quant_nanggroe.engine.strategies.kronos_wrapper")


def test_kronos_missing_path_defaults_to_fallback(monkeypatch):
    monkeypatch.delenv("QNA_KRONOS_PATH", raising=False)
    mod = _reload_kronos_module()
    assert mod.KRONOS_AVAILABLE is False


def test_kronos_invalid_path_defaults_to_fallback(monkeypatch):
    monkeypatch.setenv("QNA_KRONOS_PATH", "Z:\\nonexistent\\kronos")
    mod = _reload_kronos_module()
    assert mod.KRONOS_AVAILABLE is False
