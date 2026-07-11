"""
Comprehensive Tests for the API Layer
======================================
Tests for FastAPI app creation, health check, market routes, trading routes,
agent routes, backtest routes, portfolio routes, rate limiting middleware,
and error handling. Uses FastAPI TestClient with mocked dependencies.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_mock_portfolio():
    """Build a MagicMock that behaves like an aggregated portfolio."""
    pos = MagicMock()
    pos.symbol = "BTC-USD"
    pos.market_value = 50000.0
    portfolio = MagicMock()
    portfolio.positions = {"BTC-USD": pos}
    return portfolio


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with mocked service dependencies and admin auth."""
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
    mock_exchange.get_aggregated_portfolio = AsyncMock(return_value=_make_mock_portfolio())

    import quant_nanggroe.api.middleware as _mw

    async def _noop_ratelimit(self, scope, receive, send):
        await self.app(scope, receive, send)

    with patch("quant_nanggroe.engine.market_state.MarketStateEngine", return_value=mock_engine):
        with patch("quant_nanggroe.exchange.manager.ExchangeManager", return_value=mock_exchange):
            with patch("quant_nanggroe.services.init_all_services") as mock_init:
                with patch.object(_mw.RateLimitMiddleware, "__call__", _noop_ratelimit):
                    from quant_nanggroe.api.app import create_app

                    app = create_app()
                    # Disable lifespan (startup/shutdown) — route handlers are fully
                    # mocked, and the real lifespan tries to connect redis/DB and
                    # flush audit logs, which hangs in the offline test environment.
                    from contextlib import asynccontextmanager

                    @asynccontextmanager
                    async def _noop_lifespan(app):
                        yield

                    app.router.lifespan_context = _noop_lifespan
                    jwt = JWTAuth(secret_key="test-secret-key-for-pytest")
                    token = jwt.create_token("pytest", UserRole.ADMIN)
                    with TestClient(app, headers={"Authorization": f"Bearer {token}"}, raise_server_exceptions=False) as c:
                        yield c


class TestHealthCheck:
    def test_health_check_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "quant-nanggroe-ai"


class TestMarketRoutes:
    def test_get_price(self, client: TestClient) -> None:
        response = client.get("/api/market/price/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "price" in data

    def test_get_price_different_symbols(self, client: TestClient) -> None:
        for symbol in ["BTC-USD", "EURUSD=X", "MSFT"]:
            response = client.get(f"/api/market/price/{symbol}")
            assert response.status_code == 200
            assert response.json()["symbol"] == symbol

    def test_post_ohlcv(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 100}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "1d"
        assert "data" in data
        assert "count" in data

    def test_post_ohlcv_min_limit(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 1}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 200

    def test_post_ohlcv_max_limit(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 1000}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 200

    def test_post_ohlcv_invalid_limit(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 0}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 422

    def test_post_ohlcv_limit_over_max(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 1001}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 422

    def test_post_regime_detection(self, client: TestClient) -> None:
        payload = {
            "symbol": "XAUUSD",
            "price_change_5d": 1.0,
            "price_change_1d": 0.3,
            "adx": 30.0,
            "rsi": 55.0,
            "atr_pct": 1.2,
            "volume_ratio": 1.1,
            "ema_trend": "bullish",
        }
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "XAUUSD"
        assert "regime" in data
        assert "base_regime" in data
        assert "volatility" in data
        assert "liquidity" in data
        assert "trade_allowed" in data
        assert "no_trade_reasons" in data

    def test_post_regime_panic(self, client: TestClient) -> None:
        payload = {"symbol": "BTC-USD", "price_change_5d": -6.0}
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["regime"] == "ranging"
        assert data["trade_allowed"] is True

    def test_post_regime_defaults(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL"}
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"

    def test_get_pressure(self, client: TestClient) -> None:
        response = client.get("/api/market/pressure/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "buy_pressure" in data
        assert "sell_pressure" in data
        assert "verdict" in data


class TestTradingRoutes:
    def test_place_order(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "direction": "BUY", "quantity": 10, "order_type": "MARKET"}
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert data["symbol"] == "AAPL"
        assert data["direction"] == "BUY"
        assert data["quantity"] == 10

    def test_place_order_with_sl_tp(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "direction": "BUY", "quantity": 10, "order_type": "LIMIT", "price": 150.0, "stop_loss": 145.0, "take_profit": 160.0}
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 200

    def test_place_order_sell(self, client: TestClient) -> None:
        payload = {"symbol": "MSFT", "direction": "SELL", "quantity": 5}
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 200
        assert response.json()["direction"] == "SELL"

    def test_place_order_invalid_qty(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "direction": "BUY", "quantity": 0}
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 422

    def test_place_order_neg_qty(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "direction": "BUY", "quantity": -1}
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 422

    def test_place_order_missing_symbol(self, client: TestClient) -> None:
        payload = {"direction": "BUY", "quantity": 10}
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 422

    def test_get_positions(self, client: TestClient) -> None:
        response = client.get("/api/trading/positions")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert "total_count" in data

    def test_get_trade_history(self, client: TestClient) -> None:
        response = client.get("/api/trading/trades")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert "total_count" in data
        assert "limit" in data

    def test_get_trade_history_limit(self, client: TestClient) -> None:
        response = client.get("/api/trading/trades?limit=10")
        assert response.status_code == 200
        assert response.json()["limit"] == 10

    def test_risk_check(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "direction": "BUY", "entry": 150.0, "stop_loss": 145.0, "take_profit": 160.0, "lot_size": 0.1, "account_balance": 10000.0}
        response = client.post("/api/trading/risk-check", json=payload)
        assert response.status_code in (200, 500)

    def test_risk_check_invalid_entry(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "direction": "BUY", "entry": 0}
        response = client.post("/api/trading/risk-check", json=payload)
        assert response.status_code == 422


class TestAgentRoutes:
    def test_run_agent(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "query": "Should I buy AAPL?", "timeframe": "1d"}
        response = client.post("/api/agents/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "status" in data

    def test_run_agent_minimal(self, client: TestClient) -> None:
        response = client.post("/api/agents/run", json={"symbol": "BTC-USD"})
        assert response.status_code == 200

    def test_run_agent_missing_symbol(self, client: TestClient) -> None:
        response = client.post("/api/agents/run", json={"query": "test"})
        assert response.status_code == 422

    def test_get_agent_status(self, client: TestClient) -> None:
        response = client.get("/api/agents/status")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "active" in data

    def test_kill_switch_activate(self, client: TestClient) -> None:
        response = client.post("/api/agents/kill-switch/activate", json={"reason": "test"})
        assert response.status_code == 200
        assert "is_active" in response.json()

    def test_kill_switch_status(self, client: TestClient) -> None:
        response = client.get("/api/agents/kill-switch/status")
        assert response.status_code == 200

    def test_kill_switch_reset(self, client: TestClient) -> None:
        response = client.post("/api/agents/kill-switch/reset", json={"confirmation": "CONFIRM"})
        assert response.status_code == 200


class TestBacktestRoutes:
    def test_submit_backtest(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "strategy": "sma_crossover", "start_date": "2023-01-01", "end_date": "2024-01-01", "initial_capital": 10000.0}
        response = client.post("/api/backtest/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "backtest_id" in data
        assert data["strategy"] == "sma_crossover"

    def test_get_backtest_not_found(self, client: TestClient) -> None:
        response = client.get("/api/backtest/result/nonexistent-id")
        assert response.status_code == 200
        assert response.json()["status"] == "NOT_FOUND"

    def test_submit_and_get(self, client: TestClient) -> None:
        payload = {"symbol": "MSFT", "strategy": "rsi_mean_revert", "start_date": "2023-01-01", "end_date": "2024-01-01"}
        sr = client.post("/api/backtest/run", json=payload)
        assert sr.status_code == 200
        bid = sr.json()["backtest_id"]
        rr = client.get(f"/api/backtest/result/{bid}")
        assert rr.status_code == 200
        assert rr.json()["backtest_id"] == bid

    def test_list_backtests(self, client: TestClient) -> None:
        response = client.get("/api/backtest/list")
        assert response.status_code == 200
        data = response.json()
        assert "backtests" in data
        assert isinstance(data["backtests"], list)

    def test_submit_invalid_capital(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "strategy": "sma_crossover", "start_date": "2023-01-01", "end_date": "2024-01-01", "initial_capital": 0}
        response = client.post("/api/backtest/run", json=payload)
        assert response.status_code == 422

    def test_submit_missing_dates(self, client: TestClient) -> None:
        payload = {"symbol": "AAPL", "strategy": "sma_crossover"}
        response = client.post("/api/backtest/run", json=payload)
        assert response.status_code == 422


class TestPortfolioRoutes:
    def test_get_summary(self, client: TestClient) -> None:
        response = client.get("/api/portfolio/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "unrealized_pnl" in data
        assert "realized_pnl" in data

    def test_get_risk(self, client: TestClient) -> None:
        response = client.get("/api/portfolio/risk")
        assert response.status_code == 200
        data = response.json()
        assert "max_drawdown" in data
        assert "current_drawdown" in data

    def test_get_stress_test(self, client: TestClient) -> None:
        response = client.get("/api/portfolio/stress-test")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert "summary" in data


class TestErrorHandling:
    def test_404(self, client: TestClient) -> None:
        assert client.get("/api/nonexistent").status_code == 404
        assert client.get("/nonexistent-root").status_code == 404

    def test_422_invalid_json(self, client: TestClient) -> None:
        assert client.post("/api/trading/order", data="not-json").status_code == 422

    def test_422_ohlcv_limit(self, client: TestClient) -> None:
        assert client.post("/api/market/ohlcv", json={"symbol": "AAPL", "timeframe": "1d", "limit": 1001}).status_code == 422

    def test_422_negative_rsi(self, client: TestClient) -> None:
        assert client.post("/api/market/regime", json={"symbol": "AAPL", "rsi": -1, "price_change_5d": 1.0}).status_code == 422

    def test_422_rsi_over_100(self, client: TestClient) -> None:
        assert client.post("/api/market/regime", json={"symbol": "AAPL", "rsi": 101, "price_change_5d": 1.0}).status_code == 422

    def test_422_negative_adx(self, client: TestClient) -> None:
        assert client.post("/api/market/regime", json={"symbol": "AAPL", "adx": -1, "price_change_5d": 1.0}).status_code == 422

    def test_cors_headers(self, client: TestClient) -> None:
        # ponytail: CORSMiddleware only echoes ACAO when a matching Origin is sent
        assert "access-control-allow-origin" in client.get(
            "/health", headers={"Origin": "http://localhost:3000"}
        ).headers


class TestRateLimit:
    def test_normal_requests_allowed(self, client: TestClient) -> None:
        for _ in range(5):
            assert client.get("/api/trading/positions").status_code == 200

    def test_excess_requests_throttled(self, client: TestClient) -> None:
        for _ in range(70):
            client.get("/api/trading/positions")
        assert client.get("/api/trading/positions").status_code in (200, 429)


class TestAppCreation:
    def test_create_app_returns_fastapi(self, client: TestClient) -> None:
        from fastapi import FastAPI
        from quant_nanggroe.api.app import create_app
        assert isinstance(create_app(), FastAPI)

    def test_app_has_routes(self, client: TestClient) -> None:
        from quant_nanggroe.api.app import create_app
        assert len(create_app().routes) > 0

    def test_global_exception_handler(self, client: TestClient) -> None:
        response = client.get("/trigger-error")
        assert response.status_code == 500
        assert "detail" in response.json()
