"""Tests for generic config-files backend (dashboard Config Center).

Covers the whitelist, path-traversal guard, YAML/JSON round-trip,
mt5_accounts validation, and the FastAPI routes.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def tmp_file_dir():
    base = Path(r"C:\Users\Hi\AppData\Local\Temp\opencode")
    base.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(dir=str(base)))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def client():
    """TestClient with admin JWT — mirrors tests/test_api/test_api.py."""
    from contextlib import asynccontextmanager
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock
    from unittest.mock import patch as mpatch

    from quant_nanggroe.security.auth import JWTAuth, UserRole

    def _mock_detect_regime(**kwargs):
        mr = MagicMock()
        mr.symbol = kwargs.get("symbol", "UNKNOWN")
        mr.regime.value = "ranging"
        mr.base_regime.value = "ranging"
        mr.volatility.value = "normal"
        mr.liquidity.value = "normal"
        mr.no_trade_reasons = []
        mr.trade_allowed = True
        mr.inputs = kwargs
        mr.timestamp = datetime.now(timezone.utc)
        return mr

    mock_engine = MagicMock()
    mock_engine.detect_regime.side_effect = _mock_detect_regime
    mock_exchange = MagicMock()
    # portfolio mock
    pos = MagicMock()
    pos.symbol = "BTC-USD"
    pos.market_value = 50000.0
    portfolio = MagicMock()
    portfolio.positions = {"BTC-USD": pos}
    mock_exchange.get_aggregated_portfolio = AsyncMock(return_value=portfolio)

    import quant_nanggroe.api.middleware as _mw

    async def _noop_ratelimit(self, scope, receive, send):  # type: ignore[no-untyped-def]
        await self.app(scope, receive, send)

    with mpatch("quant_nanggroe.engine.market_state.MarketStateEngine", return_value=mock_engine):
        with mpatch("quant_nanggroe.exchange.manager.ExchangeManager", return_value=mock_exchange):
            with mpatch("quant_nanggroe.services.init_all_services"):
                with mpatch.object(_mw.RateLimitMiddleware, "__call__", _noop_ratelimit):
                    from quant_nanggroe.api.app import create_app

                    app = create_app()

                    @asynccontextmanager
                    async def _noop_lifespan(app):  # type: ignore[no-untyped-def]
                        yield

                    app.router.lifespan_context = _noop_lifespan  # type: ignore[attr-defined]
                    jwt = JWTAuth(secret_key="test-secret-key-for-pytest")
                    token = jwt.create_token("pytest", UserRole.ADMIN)
                    with TestClient(
                        app,
                        headers={"Authorization": f"Bearer {token}"},
                        raise_server_exceptions=False,
                    ) as c:
                        yield c


# ── config_manager unit tests ─────────────────────────────────────

class TestConfigManager:
    def test_list_returns_whitelisted(self):
        from quant_nanggroe.config_manager import list_config_files
        files = list_config_files()
        names = {f["name"] for f in files}
        assert "mt5_accounts.yaml" in names
        assert "system_config.yaml" in names
        assert "prompts.yaml" in names

    def test_read_unknown_raises(self):
        from quant_nanggroe.config_manager import read_config_file
        with pytest.raises(FileNotFoundError, match="Unknown config"):
            read_config_file("../../etc/passwd")

    def test_write_unknown_raises(self):
        from quant_nanggroe.config_manager import write_config_file
        with pytest.raises(FileNotFoundError, match="Unknown config"):
            write_config_file("evil.yaml", raw="x: 1")

    def test_write_readonly_raises(self):
        from quant_nanggroe.config_manager import write_config_file
        with pytest.raises(PermissionError, match="not editable"):
            write_config_file("credentials.json", raw='{"x":1}')

    def test_mt5_validation_rejects_missing_login(self, tmp_file_dir: Path):
        from quant_nanggroe import config_manager as cm
        fake = tmp_file_dir / "mt5_accounts.yaml"
        fake.write_text("accounts:\n  - server: foo\n", encoding="utf-8")
        with patch.dict(cm._ALLOWED, {"mt5_accounts.yaml": cm.ConfigFileDef("mt5_accounts.yaml", fake, "yaml", "test")}):
            with pytest.raises(ValueError, match="login is required"):
                cm.write_config_file("mt5_accounts.yaml", raw="accounts:\n  - server: foo\n")

    def test_roundtrip_yaml(self, tmp_file_dir: Path):
        from quant_nanggroe import config_manager as cm
        fake = tmp_file_dir / "mt5_accounts.yaml"
        with patch.dict(cm._ALLOWED, {"mt5_accounts.yaml": cm.ConfigFileDef("mt5_accounts.yaml", fake, "yaml", "test")}):
            raw = "accounts:\n  - name: acc1\n    login: 123\n    server: Srv\n    password: '${QNA_MT5_PASSWORD}'\n    paper: false\n"
            cm.write_config_file("mt5_accounts.yaml", raw=raw)
            got = cm.read_config_file("mt5_accounts.yaml", mask=False)
            assert got["parsed"]["accounts"][0]["login"] == 123

    def test_invalid_yaml_rejected(self, tmp_file_dir: Path):
        from quant_nanggroe import config_manager as cm
        fake = tmp_file_dir / "mt5_accounts.yaml"
        with patch.dict(cm._ALLOWED, {"mt5_accounts.yaml": cm.ConfigFileDef("mt5_accounts.yaml", fake, "yaml", "test")}):
            with pytest.raises(ValueError, match="Invalid YAML"):
                cm.write_config_file("mt5_accounts.yaml", raw=": : :")


# ── FastAPI route tests ───────────────────────────────────────────

class TestConfigFilesRoutes:
    def test_list(self, client: TestClient):
        r = client.get("/api/config/files")
        assert r.status_code == 200
        assert "files" in r.json()
        assert any(f["name"] == "mt5_accounts.yaml" for f in r.json()["files"])

    def test_read_existing(self, client: TestClient):
        r = client.get("/api/config/files/system_config.yaml")
        assert r.status_code == 200
        assert r.json()["name"] == "system_config.yaml"
        assert "raw" in r.json()

    def test_read_unknown_404(self, client: TestClient):
        r = client.get("/api/config/files/evil.yaml")
        assert r.status_code == 404

    def test_path_traversal_404(self, client: TestClient):
        r = client.get("/api/config/files/..%2F..%2Fetc%2Fpasswd")
        assert r.status_code in (404, 422)

    def test_write_readonly_403(self, client: TestClient):
        r = client.put("/api/config/files/credentials.json", json={"raw": "{}"})
        assert r.status_code == 403

    def test_write_invalid_yaml_422(self, client: TestClient, tmp_file_dir: Path):
        from quant_nanggroe import config_manager as cm
        fake = tmp_file_dir / "system_config.yaml"
        fake.write_text("x: 1\n", encoding="utf-8")
        with patch.dict(cm._ALLOWED, {"system_config.yaml": cm.ConfigFileDef("system_config.yaml", fake, "yaml", "test")}):
            r = client.put("/api/config/files/system_config.yaml", json={"raw": ": : :"})
            assert r.status_code == 422

    def test_write_and_read_back(self, client: TestClient, tmp_file_dir: Path):
        from quant_nanggroe import config_manager as cm
        fake = tmp_file_dir / "mt5_accounts.yaml"
        with patch.dict(cm._ALLOWED, {"mt5_accounts.yaml": cm.ConfigFileDef("mt5_accounts.yaml", fake, "yaml", "test")}):
            raw = "accounts:\n  - name: test-acc\n    login: 999\n    server: TestSrv\n    password: x\n"
            r = client.put("/api/config/files/mt5_accounts.yaml", json={"raw": raw})
            assert r.status_code == 200
            r2 = client.get("/api/config/files/mt5_accounts.yaml")
            assert "test-acc" in r2.json()["raw"]
