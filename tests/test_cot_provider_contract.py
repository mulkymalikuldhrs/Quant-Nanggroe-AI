"""
Regression guard: COTProvider / COTAnalyzer interface must match what
cot_strategy.py calls (provider.fetch(), analyzer.generate_signal(symbol, price_series=...)).

If this breaks, AutonomousPipeline.run() crashes for any COT-auto-discovered strategy.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_nanggroe.engine.data.cot_provider import COTProvider, COTAnalyzer


def test_cot_provider_has_fetch():
    assert hasattr(COTProvider(), "fetch")


def test_analyzer_generate_signal_contract():
    provider = COTProvider()
    provider.fetch()
    sig = COTAnalyzer(provider).generate_signal("ES", price_series=None)
    assert isinstance(sig, dict)
    assert "signal" in sig
    assert sig["signal"] in ("buy", "sell", "neutral", "hold")
