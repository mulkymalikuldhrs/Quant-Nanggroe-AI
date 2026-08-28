"""GATE-4 regression: Export Center API (csv/xlsx/md/json + summary)."""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch as mpatch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def tmp_file_dir():
    base = Path(r"C:\Users\Hi\AppData\Local\Temp\opencode")
    base.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(dir=str(base)))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def client(tmp_file_dir):
    """TestClient with admin JWT + temp journal DB seeded with sample trades."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    from quant_nanggroe.security.auth import JWTAuth, UserRole

    mock_engine = MagicMock()
    mock_exchange = MagicMock()
    pos = MagicMock(); pos.symbol = "BTC-USD"; pos.market_value = 50000.0
    portfolio = MagicMock(); portfolio.positions = {"BTC-USD": pos}
    mock_exchange.get_aggregated_portfolio = AsyncMock(return_value=portfolio)

    import quant_nanggroe.api.middleware as _mw
    async def _noop_rl(self, scope, receive, send):
        await self.app(scope, receive, send)

    # seed temp journal db
    db = tmp_file_dir / "qna_trade_journal.db"
    con = sqlite3.connect(str(db))
    con.execute("""CREATE TABLE trades (
        ticket TEXT, strategy TEXT, symbol TEXT, side TEXT, entry REAL,
        sl REAL, tp REAL, confidence REAL, open_time TEXT, close_time TEXT,
        exit_price REAL, pnl REAL, outcome TEXT, comment TEXT, hypothesis TEXT,
        setup_ctx TEXT, close_reason TEXT, hit_type TEXT, market_ctx TEXT,
        tf_category TEXT)""")
    con.executemany("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("1", "archive_aroon", "XAUUSD.vx", "buy", 2000, 1980, 2060, 0.8,
         "2026-08-01T10:00", "2026-08-02T12:00", 2040, 40.0, "win", "",
         "h1", "ctx", "take_profit", "tp", "bull", "H1"),
        ("2", "archive_amdx", "EURUSD.vx", "sell", 1.09, 1.095, 1.08, 0.7,
         "2026-08-05T10:00", "2026-08-06T15:00", 1.085, -25.0, "loss", "",
         "h2", "ctx", "stop_loss", "sl", "bear", "H1"),
        ("3", "archive_aroon", "BTCUSD.vx", "buy", 60000, 59000, 63000, 0.9,
         "2026-08-10T08:00", "2026-08-11T09:00", 62500, 250.0, "win", "",
         "h3", "ctx", "take_profit", "tp", "bull", "D1"),
    ])
    con.commit(); con.close()

    with mpatch("quant_nanggroe.engine.market_state.MarketStateEngine", return_value=mock_engine), \
         mpatch("quant_nanggroe.exchange.manager.ExchangeManager", return_value=mock_exchange), \
         mpatch("quant_nanggroe.services.init_all_services"), \
         mpatch.object(_mw.RateLimitMiddleware, "__call__", _noop_rl):
        from quant_nanggroe.api.app import create_app
        app = create_app()

        @asynccontextmanager
        async def _noop_ls(app):
            yield
        app.router.lifespan_context = _noop_ls

        # point export route at the temp db
        from quant_nanggroe.api.routes import export as exp
        mpatch.object(exp, "_JOURNAL_DB_CANDIDATES", [db]).start()

        jwt = JWTAuth(secret_key="test-secret-key-for-pytest")
        token = jwt.create_token("pytest", UserRole.ADMIN)
        with TestClient(app, headers={"Authorization": f"Bearer {token}"},
                        raise_server_exceptions=False) as c:
            yield c


class TestExportCenter:
    def test_csv(self, client: TestClient):
        r = client.get("/api/export/trades?format=csv")
        assert r.status_code == 200
        assert b"ticket" in r.content and b"archive_aroon" in r.content

    def test_json_filter_by_strategy(self, client: TestClient):
        r = client.get("/api/export/trades?format=json&strategy=archive_aroon")
        assert r.status_code == 200
        rows = json.loads(r.content)
        assert len(rows) == 2
        assert all(x["strategy"] == "archive_aroon" for x in rows)

    def test_date_range(self, client: TestClient):
        r = client.get("/api/export/trades?format=json&date_from=2026-08-05&date_to=2026-08-06")
        rows = json.loads(r.content)
        assert len(rows) == 1 and rows[0]["strategy"] == "archive_amdx"

    def test_xlsx(self, client: TestClient):
        r = client.get("/api/export/trades?format=xlsx")
        assert r.status_code == 200
        assert r.content[:2] == b"PK"  # zip magic

    def test_md(self, client: TestClient):
        r = client.get("/api/export/trades?format=md")
        assert r.status_code == 200 and b"# QNA Trade History" in r.content

    def test_summary(self, client: TestClient):
        r = client.get("/api/export/summary")
        assert r.status_code == 200
        d = json.loads(r.content)
        assert d["total_trades"] == 3 and d["strategies"] == 2
        top = d["rows"][0]
        assert top["strategy"] == "archive_aroon" and top["total_pnl"] == 290.0

    def test_bad_format_400(self, client: TestClient):
        r = client.get("/api/export/trades?format=docx")
        assert r.status_code == 400
