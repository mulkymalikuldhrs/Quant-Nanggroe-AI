"""Deep-audit tests: execution-backend honest health (GAP-D1) + builder status flag."""

from quant_nanggroe.engine.execution.builder import (
    build_execution_manager,
    get_execution_backend_status,
)


def test_builder_status_unavailable_when_mt5_unconfigured():
    """REAL-ONLY mode with no MT5 -> raises AND status flips to 'unavailable'."""
    import pytest

    try:
        build_execution_manager(allow_live=False)
        pytest.fail("expected RuntimeError in REAL-ONLY mode")
    except RuntimeError:
        pass
    assert get_execution_backend_status() == "unavailable"


def test_health_endpoint_exposes_execution_backend():
    """GET /health (app.py:432) must include execution_backend key + degrade logic.

    Source-level assertion (no full app build) to avoid prometheus double-register
    when the suite imports create_app repeatedly across test files.
    """
    import os

    app_file = os.path.join(
        os.path.dirname(__file__), "..", "quant_nanggroe", "api", "app.py"
    )
    src = open(app_file, encoding="utf-8").read()
    assert "execution_backend" in src, "app.py /health must expose execution_backend"
    assert "get_execution_backend_status" in src, "health must read builder status"
    assert 'if execution_backend == "unavailable":' in src, "health must degrade on unavailable"
