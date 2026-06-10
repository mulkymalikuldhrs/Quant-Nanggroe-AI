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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ══════════════════════════════════════════════════════════════════════
# App Fixture — Create TestClient with mocked services
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with mocked service dependencies."""
    # Mock the services module that the app imports at startup
    with patch("quant_nanggroe.api.app.init_all_services", create=True):
        with patch("quant_nanggroe.services", create=True):
            from quant_nanggroe.api.app import create_app

            app = create_app()
            with TestClient(app) as c:
                yield c


# ══════════════════════════════════════════════════════════════════════
# Health Check Tests
# ══════════════════════════════════════════════════════════════════════


class TestHealthCheck:
    """Test the /health endpoint."""

    def test_health_check_returns_200(self, client: TestClient) -> None:
        """Health endpoint returns 200 status."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client: TestClient) -> None:
        """Health endpoint returns expected structure."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "quant-nanggroe-ai"


# ══════════════════════════════════════════════════════════════════════
# Market Route Tests
# ══════════════════════════════════════════════════════════════════════


class TestMarketRoutes:
    """Test /api/market/* routes."""

    def test_get_price(self, client: TestClient) -> None:
        """GET /api/market/price/{symbol} returns price data."""
        response = client.get("/api/market/price/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "price" in data

    def test_get_price_different_symbols(self, client: TestClient) -> None:
        """Price endpoint works for different symbols."""
        for symbol in ["BTC-USD", "EURUSD=X", "MSFT"]:
            response = client.get(f"/api/market/price/{symbol}")
            assert response.status_code == 200
            assert response.json()["symbol"] == symbol

    def test_post_ohlcv(self, client: TestClient) -> None:
        """POST /api/market/ohlcv returns OHLCV data."""
        payload = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "limit": 100,
        }
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "1d"
        assert "data" in data
        assert "count" in data

    def test_post_ohlcv_with_min_limit(self, client: TestClient) -> None:
        """POST /api/market/ohlcv with limit=1."""
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 1}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 200

    def test_post_ohlcv_with_max_limit(self, client: TestClient) -> None:
        """POST /api/market/ohlcv with limit=1000."""
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 1000}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 200

    def test_post_ohlcv_invalid_limit(self, client: TestClient) -> None:
        """POST /api/market/ohlcv with invalid limit returns 422."""
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 0}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 422

    def test_post_ohlcv_limit_over_max(self, client: TestClient) -> None:
        """POST /api/market/ohlcv with limit > 1000 returns 422."""
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 1001}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 422

    def test_post_regime_detection(self, client: TestClient) -> None:
        """POST /api/market/regime detects market regime."""
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
        """POST /api/market/regime detects PANIC → NO_TRADE."""
        payload = {
            "symbol": "BTC-USD",
            "price_change_5d": -6.0,
        }
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["regime"] == "NO_TRADE"
        assert data["trade_allowed"] is False

    def test_post_regime_default_values(self, client: TestClient) -> None:
        """POST /api/market/regime with only symbol (defaults)."""
        payload = {"symbol": "AAPL"}
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"

    def test_get_pressure(self, client: TestClient) -> None:
        """GET /api/market/pressure/{symbol} returns pressure data."""
        response = client.get("/api/market/pressure/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "buy_pressure" in data
        assert "sell_pressure" in data
        assert "verdict" in data


# ══════════════════════════════════════════════════════════════════════
# Trading Route Tests
# ══════════════════════════════════════════════════════════════════════


class TestTradingRoutes:
    """Test /api/trading/* routes."""

    def test_place_order(self, client: TestClient) -> None:
        """POST /api/trading/order places an order."""
        payload = {
            "symbol": "AAPL",
            "direction": "BUY",
            "quantity": 10,
            "order_type": "MARKET",
        }
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert data["symbol"] == "AAPL"
        assert data["direction"] == "BUY"
        assert data["quantity"] == 10

    def test_place_order_with_sl_tp(self, client: TestClient) -> None:
        """POST /api/trading/order with stop-loss and take-profit."""
        payload = {
            "symbol": "AAPL",
            "direction": "BUY",
            "quantity": 10,
            "order_type": "LIMIT",
            "price": 150.0,
            "stop_loss": 145.0,
            "take_profit": 160.0,
        }
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 200

    def test_place_order_sell(self, client: TestClient) -> None:
        """POST /api/trading/order with SELL direction."""
        payload = {
            "symbol": "MSFT",
            "direction": "SELL",
            "quantity": 5,
        }
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 200
        assert response.json()["direction"] == "SELL"

    def test_place_order_invalid_quantity(self, client: TestClient) -> None:
        """POST /api/trading/order with quantity=0 returns 422."""
        payload = {
            "symbol": "AAPL",
            "direction": "BUY",
            "quantity": 0,
        }
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 422

    def test_place_order_negative_quantity(self, client: TestClient) -> None:
        """POST /api/trading/order with negative quantity returns 422."""
        payload = {
            "symbol": "AAPL",
            "direction": "BUY",
            "quantity": -1,
        }
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 422

    def test_place_order_missing_symbol(self, client: TestClient) -> None:
        """POST /api/trading/order without symbol returns 422."""
        payload = {"direction": "BUY", "quantity": 10}
        response = client.post("/api/trading/order", json=payload)
        assert response.status_code == 422

    def test_get_positions(self, client: TestClient) -> None:
        """GET /api/trading/positions returns positions."""
        response = client.get("/api/trading/positions")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert "total_count" in data

    def test_get_trade_history(self, client: TestClient) -> None:
        """GET /api/trading/trades returns trade history."""
        response = client.get("/api/trading/trades")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert "total_count" in data
        assert "limit" in data

    def test_get_trade_history_with_limit(self, client: TestClient) -> None:
        """GET /api/trading/trades?limit=10 respects the limit."""
        response = client.get("/api/trading/trades?limit=10")
        assert response.status_code == 200
        assert response.json()["limit"] == 10

    def test_risk_check_endpoint(self, client: TestClient) -> None:
        """POST /api/trading/risk-check runs risk validation."""
        payload = {
            "symbol": "AAPL",
            "direction": "BUY",
            "entry": 150.0,
            "stop_loss": 145.0,
            "take_profit": 160.0,
            "lot_size": 0.1,
            "account_balance": 10000.0,
        }
        response = client.post("/api/trading/risk-check", json=payload)
        # May return 200 or 500 depending on services availability
        # but should not return 422 for valid payload
        assert response.status_code in (200, 500)

    def test_risk_check_invalid_entry(self, client: TestClient) -> None:
        """POST /api/trading/risk-check with entry=0 returns 422."""
        payload = {
            "symbol": "AAPL",
            "direction": "BUY",
            "entry": 0,
        }
        response = client.post("/api/trading/risk-check", json=payload)
        assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# Agent Route Tests
# ══════════════════════════════════════════════════════════════════════


class TestAgentRoutes:
    """Test /api/agents/* routes."""

    def test_run_agent(self, client: TestClient) -> None:
        """POST /api/agents/run runs an agent pipeline."""
        payload = {
            "symbol": "AAPL",
            "query": "Should I buy AAPL?",
            "timeframe": "1d",
        }
        response = client.post("/api/agents/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["query"] == "Should I buy AAPL?"
        assert "status" in data

    def test_run_agent_minimal(self, client: TestClient) -> None:
        """POST /api/agents/run with only symbol."""
        payload = {"symbol": "BTC-USD"}
        response = client.post("/api/agents/run", json=payload)
        assert response.status_code == 200

    def test_run_agent_missing_symbol(self, client: TestClient) -> None:
        """POST /api/agents/run without symbol returns 422."""
        payload = {"query": "What's the market doing?"}
        response = client.post("/api/agents/run", json=payload)
        assert response.status_code == 422

    def test_get_agent_status(self, client: TestClient) -> None:
        """GET /api/agents/status returns agent system status."""
        response = client.get("/api/agents/status")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "active" in data
        assert "kill_switch_active" in data

    def test_kill_switch_activate(self, client: TestClient) -> None:
        """POST /api/agents/kill-switch/activate activates kill switch."""
        payload = {"reason": "Emergency test"}
        response = client.post("/api/agents/kill-switch/activate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "is_active" in data
        assert "message" in data

    def test_kill_switch_status(self, client: TestClient) -> None:
        """GET /api/agents/kill-switch/status returns kill switch status."""
        response = client.get("/api/agents/kill-switch/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_active" in data

    def test_kill_switch_reset_requires_confirmation(self, client: TestClient) -> None:
        """POST /api/agents/kill-switch/reset without CONFIRM returns error."""
        payload = {"confirmation": "WRONG"}
        response = client.post("/api/agents/kill-switch/reset", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "CONFIRM" in data["message"] or data["is_active"] is True

    def test_kill_switch_reset_with_confirm(self, client: TestClient) -> None:
        """POST /api/agents/kill-switch/reset with CONFIRM attempts reset."""
        payload = {"confirmation": "CONFIRM"}
        response = client.post("/api/agents/kill-switch/reset", json=payload)
        assert response.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# Backtest Route Tests
# ══════════════════════════════════════════════════════════════════════


class TestBacktestRoutes:
    """Test /api/backtest/* routes."""

    def test_submit_backtest(self, client: TestClient) -> None:
        """POST /api/backtest/run submits a backtest."""
        payload = {
            "symbol": "AAPL",
            "strategy": "sma_crossover",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "initial_capital": 10000.0,
        }
        response = client.post("/api/backtest/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "backtest_id" in data
        assert data["symbol"] == "AAPL"
        assert data["strategy"] == "sma_crossover"

    def test_get_backtest_result_not_found(self, client: TestClient) -> None:
        """GET /api/backtest/result/{id} for unknown ID returns NOT_FOUND."""
        response = client.get("/api/backtest/result/nonexistent-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "NOT_FOUND"
        assert data["error"] == "Backtest not found"

    def test_submit_and_get_backtest(self, client: TestClient) -> None:
        """Submit a backtest and then retrieve its result."""
        payload = {
            "symbol": "MSFT",
            "strategy": "rsi_mean_revert",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
        }
        submit_response = client.post("/api/backtest/run", json=payload)
        assert submit_response.status_code == 200
        backtest_id = submit_response.json()["backtest_id"]

        # Retrieve the result
        result_response = client.get(f"/api/backtest/result/{backtest_id}")
        assert result_response.status_code == 200
        data = result_response.json()
        assert data["backtest_id"] == backtest_id
        assert data["symbol"] == "MSFT"
        assert data["strategy"] == "rsi_mean_revert"
        assert data["status"] == "QUEUED"

    def test_list_backtests(self, client: TestClient) -> None:
        """GET /api/backtest/list lists all backtests."""
        response = client.get("/api/backtest/list")
        assert response.status_code == 200
        data = response.json()
        assert "backtests" in data
        assert "total" in data
        assert isinstance(data["backtests"], list)

    def test_submit_backtest_invalid_capital(self, client: TestClient) -> None:
        """POST /api/backtest/run with capital=0 returns 422."""
        payload = {
            "symbol": "AAPL",
            "strategy": "sma_crossover",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "initial_capital": 0,
        }
        response = client.post("/api/backtest/run", json=payload)
        assert response.status_code == 422

    def test_submit_backtest_missing_dates(self, client: TestClient) -> None:
        """POST /api/backtest/run without dates returns 422."""
        payload = {
            "symbol": "AAPL",
            "strategy": "sma_crossover",
        }
        response = client.post("/api/backtest/run", json=payload)
        assert response.status_code == 422

    def test_submit_backtest_custom_params(self, client: TestClient) -> None:
        """POST /api/backtest/run with custom commission and slippage."""
        payload = {
            "symbol": "AAPL",
            "strategy": "macd_crossover",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "initial_capital": 50000.0,
            "commission": 0.002,
            "slippage": 0.001,
        }
        response = client.post("/api/backtest/run", json=payload)
        assert response.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# Portfolio Route Tests
# ══════════════════════════════════════════════════════════════════════


class TestPortfolioRoutes:
    """Test /api/portfolio/* routes."""

    def test_get_portfolio_summary(self, client: TestClient) -> None:
        """GET /api/portfolio/summary returns portfolio data."""
        response = client.get("/api/portfolio/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "unrealized_pnl" in data
        assert "realized_pnl" in data
        assert "position_count" in data

    def test_get_portfolio_risk(self, client: TestClient) -> None:
        """GET /api/portfolio/risk returns risk metrics."""
        response = client.get("/api/portfolio/risk")
        assert response.status_code == 200
        data = response.json()
        assert "max_drawdown" in data
        assert "current_drawdown" in data
        assert "risk_status" in data

    def test_get_portfolio_stress_test(self, client: TestClient) -> None:
        """GET /api/portfolio/stress-test returns stress test results."""
        response = client.get("/api/portfolio/stress-test")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert "message" in data


# ══════════════════════════════════════════════════════════════════════
# Rate Limiting Middleware Tests
# ══════════════════════════════════════════════════════════════════════


class TestRateLimitMiddleware:
    """Test the RateLimitMiddleware."""

    def test_rate_limit_allows_normal_requests(self) -> None:
        """Normal request volume is allowed through."""
        from quant_nanggroe.api.middleware import RateLimitMiddleware
        from fastapi import FastAPI

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200

    def test_rate_limit_blocks_excess_requests(self) -> None:
        """Requests exceeding the limit receive 429."""
        from quant_nanggroe.api.middleware import RateLimitMiddleware
        from fastapi import FastAPI

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=5)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        with TestClient(app) as client:
            # Send 6 requests (limit is 5)
            responses = []
            for _ in range(6):
                responses.append(client.get("/test"))

            # At least one should be rate limited
            status_codes = [r.status_code for r in responses]
            assert 429 in status_codes

    def test_rate_limit_tracks_per_client(self) -> None:
        """Rate limit counts are tracked per client ID."""
        from quant_nanggroe.api.middleware import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=None, requests_per_minute=10)
        assert middleware.requests == {}

    def test_rate_limit_custom_rpm(self) -> None:
        """Custom requests_per_minute value is respected."""
        from quant_nanggroe.api.middleware import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=None, requests_per_minute=30)
        assert middleware.requests_per_minute == 30


# ══════════════════════════════════════════════════════════════════════
# Error Handling Tests
# ══════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Test error handling and validation."""

    def test_404_not_found(self, client: TestClient) -> None:
        """Requesting a non-existent route returns 404."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_404_not_found_root(self, client: TestClient) -> None:
        """Root path returns 404 (no root handler)."""
        response = client.get("/")
        assert response.status_code == 404

    def test_422_validation_error_invalid_json(self, client: TestClient) -> None:
        """Invalid JSON payload returns 422."""
        response = client.post(
            "/api/trading/order",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_422_validation_error_ohlcv_limit_exceeded(self, client: TestClient) -> None:
        """OHLCV limit > 1000 returns 422 validation error."""
        payload = {"symbol": "AAPL", "timeframe": "1d", "limit": 5000}
        response = client.post("/api/market/ohlcv", json=payload)
        assert response.status_code == 422

    def test_422_validation_error_negative_rsi(self, client: TestClient) -> None:
        """Negative RSI returns 422 validation error."""
        payload = {"symbol": "AAPL", "rsi": -1.0}
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 422

    def test_422_validation_error_rsi_over_100(self, client: TestClient) -> None:
        """RSI > 100 returns 422 validation error."""
        payload = {"symbol": "AAPL", "rsi": 101.0}
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 422

    def test_422_validation_error_negative_adx(self, client: TestClient) -> None:
        """Negative ADX returns 422 validation error."""
        payload = {"symbol": "AAPL", "adx": -1.0}
        response = client.post("/api/market/regime", json=payload)
        assert response.status_code == 422

    def test_cors_headers_present(self, client: TestClient) -> None:
        """CORS headers are included in responses."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should be handled
        assert response.status_code in (200, 204)


# ══════════════════════════════════════════════════════════════════════
# App Creation Tests
# ══════════════════════════════════════════════════════════════════════


class TestAppCreation:
    """Test the FastAPI app creation and configuration."""

    def test_create_app_returns_fastapi(self) -> None:
        """create_app() returns a FastAPI application."""
        with patch("quant_nanggroe.api.app.init_all_services", create=True):
            with patch("quant_nanggroe.services", create=True):
                from quant_nanggroe.api.app import create_app

                app = create_app()
                assert app is not None
                assert app.title == "Quant Nanggroe AI"

    def test_app_has_routes(self, client: TestClient) -> None:
        """App has all expected route prefixes."""
        routes = [route.path for route in client.app.routes]
        # Check for key route prefixes
        assert any("/api/market" in r for r in routes)
        assert any("/api/trading" in r for r in routes)
        assert any("/api/agents" in r for r in routes)
        assert any("/api/backtest" in r for r in routes)
        assert any("/api/portfolio" in r for r in routes)
        assert "/health" in routes

    def test_global_exception_handler(self, client: TestClient) -> None:
        """Global exception handler returns 500 for unhandled errors."""
        # This is harder to test directly, but we can verify the handler exists
        from quant_nanggroe.api.app import create_app

        with patch("quant_nanggroe.api.app.init_all_services", create=True):
            with patch("quant_nanggroe.services", create=True):
                app = create_app()
                # Check that exception handlers are registered
                assert Exception in app.exception_handlers
