"""
Regression guard: COTProvider / COTAnalyzer interface must match what
cot_strategy.py calls (provider.fetch(), analyzer.generate_signal(symbol, price_series=...)).

If this breaks, AutonomousPipeline.run() crashes for any COT-auto-discovered strategy.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_nanggroe.engine.data.cot_provider import COTAnalyzer, COTProvider


@pytest.mark.skipif(
    not os.environ.get("QNA_TEST_LIVE_NETWORK"),
    reason="Skipped: requires live network (set QNA_TEST_LIVE_NETWORK=1 to enable)"
)
def test_cot_provider_has_fetch():
    assert hasattr(COTProvider(), "fetch")


@pytest.mark.skipif(
    not os.environ.get("QNA_TEST_LIVE_NETWORK"),
    reason="Skipped: requires live network (set QNA_TEST_LIVE_NETWORK=1 to enable)"
)
def test_analyzer_generate_signal_contract():
    provider = COTProvider()
    provider.fetch()
    sig = COTAnalyzer(provider).generate_signal("ES", price_series=None)
    assert isinstance(sig, dict)
    assert "signal" in sig
    assert sig["signal"] in ("buy", "sell", "neutral", "hold")
