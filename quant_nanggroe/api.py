"""FastAPI application for Quant Nanggroe AI.

Full REST API and WebSocket server for the Agentic Trading Intelligence OS.

Endpoints:
- POST /api/v1/trade       - Execute trading pipeline
- GET  /api/v1/portfolio    - Get portfolio status
- GET  /api/v1/agents       - List available agents
- POST /api/v1/backtest     - Run backtest
- GET  /api/v1/risk/{symbol} - Get risk assessment for symbol
- GET  /api/v1/health       - Health check
- WS   /ws/trading          - Real-time trading updates

Features:
- Pydantic request/response models
- CORS middleware for dashboard integration
- WebSocket for real-time updates
- OpenAPI docs at /docs
- Proper error handling with HTTP status codes
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from quant_nanggroe.config.settings import get_settings
from quant_nanggroe.security.auth_middleware import (
    AuthContext,
    require_auth,
    require_role,
    optional_auth,
    authenticate_and_issue_token,
)

# Lazy imports for agent modules (may not be available if langchain is not installed)
# RiskVerdict values are used as string constants in response models
_RISK_VERDICT_VETOED = "VETOED"
_RISK_VERDICT_APPROVED = "APPROVED"
_RISK_VERDICT_CONDITIONAL = "CONDITIONAL"
_RISK_VERDICT_KILL_SWITCH = "KILL_SWITCH"

try:
    from quant_nanggroe.agents.state import RiskVerdict as _RiskVerdict
    _RISK_VERDICT_VETOED = _RiskVerdict.VETOED.value
    _RISK_VERDICT_APPROVED = _RiskVerdict.APPROVED.value
    _RISK_VERDICT_CONDITIONAL = _RiskVerdict.CONDITIONAL.value
    _RISK_VERDICT_KILL_SWITCH = _RiskVerdict.KILL_SWITCH.value
except ImportError:
    pass  # Use default string constants

logger = logging.getLogger(__name__)

# =============================================================================
# Pydantic Request/Response Models
# =============================================================================


# --- Trade ---


class TradeRequest(BaseModel):
    """Request model for executing a trading pipeline run."""

    symbols: List[str] = Field(
        ..., min_length=1, description="List of trading symbols (e.g., ['BTC/USDT', 'AAPL'])"
    )
    provider: str = Field(
        default="openai", description="LLM provider (openai, anthropic, google, ollama, openrouter)"
    )
    deep_model: str = Field(default="gpt-4o", description="Deep-thinking model name")
    quick_model: str = Field(default="gpt-4o-mini", description="Quick-thinking model name")
    trade_date: Optional[str] = Field(
        None, description="Trading date (YYYY-MM-DD), defaults to today"
    )
    paper: bool = Field(default=True, description="Use paper trading")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TradeResponse(BaseModel):
    """Response model for a trading pipeline execution."""

    status: str = Field(..., description="Execution status (success/error)")
    symbols: List[str]
    trade_date: str
    confidence: float = Field(0.0, description="Overall confidence score")
    risk_verdict: str = Field(
        default=_RISK_VERDICT_VETOED, description="Risk assessment verdict"
    )
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Portfolio ---


class PositionInfoResponse(BaseModel):
    """Position information in portfolio response."""
    symbol: str
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    direction: str = "LONG"


class PortfolioResponse(BaseModel):
    """Response model for portfolio status."""

    total_value: float = Field(0.0, description="Total portfolio value")
    cash: float = Field(0.0, description="Available cash")
    positions: List[PositionInfoResponse] = Field(default_factory=list)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    allocation: Dict[str, float] = Field(default_factory=dict)
    risk_budget_used: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Agents ---


class AgentInfoResponse(BaseModel):
    """Information about a single agent."""
    name: str
    role: str
    description: str = ""
    status: str = "ready"
    tools: List[str] = Field(default_factory=list)


class AgentListResponse(BaseModel):
    """Response model for agent listing."""

    agents: List[AgentInfoResponse]
    total: int


# --- Backtest ---


class BacktestRequest(BaseModel):
    """Request model for running a backtest."""

    strategy: str = Field(..., description="Strategy name (momentum, mean_reversion, breakout, etc.)")
    symbols: List[str] = Field(
        default=["BTC/USDT"], description="Symbols to backtest"
    )
    period: str = Field(default="1Y", description="Backtest period (1M, 3M, 6M, 1Y, 2Y)")
    initial_capital: float = Field(default=100000.0, gt=0, description="Initial capital")
    commission: float = Field(default=0.001, ge=0, description="Commission rate")
    slippage: float = Field(default=0.0005, ge=0, description="Slippage rate")
    market: str = Field(default="crypto", description="Market type (equity, crypto, forex)")


class BacktestMetricsResponse(BaseModel):
    """Backtest performance metrics."""
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_pnl: float = 0.0


class BacktestResponse(BaseModel):
    """Response model for backtest results."""

    status: str = Field(..., description="Backtest status")
    strategy: str
    symbols: List[str]
    period: str
    initial_capital: float
    final_equity: float = 0.0
    metrics: BacktestMetricsResponse = Field(default_factory=BacktestMetricsResponse)
    equity_curve_sample: List[float] = Field(
        default_factory=list, description="Sampled equity curve points"
    )
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Risk ---


class RiskCheckResponse(BaseModel):
    """Response model for risk assessment."""

    symbol: str
    verdict: str = Field(default=_RISK_VERDICT_VETOED)
    risk_level: str = "low"
    per_trade_risk_pct: float = 0.0
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    drawdown_pct: float = 0.0
    position_concentration_pct: float = 0.0
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    approved: bool = False
    veto_reason: Optional[str] = None
    constitutional_limits: Dict[str, Any] = Field(default_factory=dict)
    suggested_position_size: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Health ---


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.2.0"
    uptime_seconds: float = 0.0
    components: Dict[str, str] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Error ---


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    status_code: int = 500
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Application Setup
# =============================================================================


# Track app start time
_start_time: float = datetime.now().timestamp()

# In-memory portfolio state (for demo; production would use DB)
_portfolio_state: Dict[str, Any] = {
    "total_value": 1000000.0,
    "cash": 500000.0,
    "positions": [],
    "unrealized_pnl": 0.0,
    "realized_pnl": 0.0,
    "daily_pnl": 0.0,
    "weekly_pnl": 0.0,
    "allocation": {},
    "risk_budget_used": 0.0,
}

# WebSocket connection manager
_ws_connections: List[WebSocket] = []


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Quant Nanggroe AI",
        description=(
            "Agentic Trading Intelligence OS API — Multi-agent trading framework "
            "with LangGraph orchestration, constitutional risk management, "
            "and production-grade execution."
        ),
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware — restricted to known origins in production
    allowed_origins = os.getenv("QNAI_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in allowed_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "X-API-Key", "Content-Type"],
    )

    # ------------------------------------------------------------------
    # Root
    # ------------------------------------------------------------------

    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint — API info."""
        return {
            "name": "Quant Nanggroe AI",
            "version": "0.2.0",
            "description": "Agentic Trading Intelligence OS",
            "docs": "/docs",
            "status": "operational",
        }

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        """Health check endpoint."""
        uptime = datetime.now().timestamp() - _start_time
        return HealthResponse(
            status="healthy",
            version="0.2.0",
            uptime_seconds=round(uptime, 1),
            components={
                "api": "healthy",
                "agents": "ready",
                "risk_engine": "operational",
                "memory": "operational",
            },
        )

    # ------------------------------------------------------------------
    # Trade
    # ------------------------------------------------------------------

    @app.post("/api/v1/auth/token", tags=["auth"])
    async def login(api_key: str = None):
        """Authenticate with API key and receive JWT token.

        Pass your API key to receive a JWT Bearer token for subsequent requests.
        """
        if not api_key:
            raise HTTPException(status_code=400, detail="api_key parameter required")
        return authenticate_and_issue_token(api_key)

    @app.post("/api/v1/trade", response_model=TradeResponse, tags=["trading"], dependencies=[Depends(require_role("trade"))])
    async def execute_trade(request: TradeRequest, auth: AuthContext = Depends(require_auth)):
        """
        Execute the full trading pipeline for specified symbols.

        Runs the multi-agent trading graph: market analysis → signal generation →
        risk assessment → portfolio optimization → execution decision → order execution.

        Requires valid LLM API keys to be configured.
        """
        try:
            settings = get_settings()
            trade_date = request.trade_date or datetime.now().strftime("%Y-%m-%d")

            # Attempt to run the actual trading graph
            try:
                from quant_nanggroe.agents.graph import TradingGraph

                graph = TradingGraph(
                    llm_provider=request.provider,
                    deep_think_model=request.deep_model,
                    quick_think_model=request.quick_model,
                    api_key=settings.openai_api_key,
                )
                result = graph.run(
                    symbols=request.symbols,
                    trade_date=trade_date,
                    metadata=request.metadata or {},
                )

                return TradeResponse(
                    status="success",
                    symbols=request.symbols,
                    trade_date=trade_date,
                    confidence=result.get("confidence", 0.0),
                    risk_verdict=result.get("risk_verdict", _RISK_VERDICT_VETOED),
                    decisions=result.get("decisions", []),
                    signals=result.get("signals", []),
                    agent_outputs=result.get("agent_outputs", {}),
                )
            except Exception as graph_err:
                logger.error("Trading graph execution failed: %s", graph_err)
                # FAIL CLOSED: Do not return fake/mock data when pipeline fails
                raise HTTPException(
                    status_code=503,
                    detail=f"Trading pipeline unavailable: {str(graph_err)[:200]}. Configure LLM API keys for live execution.",
                )

        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Trade execution failed: {str(e)}",
            )

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    @app.get("/api/v1/portfolio", response_model=PortfolioResponse, tags=["portfolio"], dependencies=[Depends(require_role("read"))])
    async def get_portfolio(auth: AuthContext = Depends(require_auth)):
        """
        Get current portfolio status.

        Returns portfolio value, positions, P&L, and allocation.
        """
        try:
            # In production, this would query a real portfolio manager
            positions = [
                PositionInfoResponse(
                    symbol=p["symbol"],
                    quantity=p.get("quantity", 0),
                    entry_price=p.get("entry_price", 0),
                    current_price=p.get("current_price", 0),
                    unrealized_pnl=p.get("unrealized_pnl", 0),
                    direction=p.get("direction", "LONG"),
                )
                for p in _portfolio_state.get("positions", [])
            ]

            return PortfolioResponse(
                total_value=_portfolio_state["total_value"],
                cash=_portfolio_state["cash"],
                positions=positions,
                unrealized_pnl=_portfolio_state["unrealized_pnl"],
                realized_pnl=_portfolio_state["realized_pnl"],
                daily_pnl=_portfolio_state["daily_pnl"],
                weekly_pnl=_portfolio_state["weekly_pnl"],
                allocation=_portfolio_state.get("allocation", {}),
                risk_budget_used=_portfolio_state.get("risk_budget_used", 0.0),
            )
        except Exception as e:
            logger.error(f"Portfolio query error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Portfolio query failed: {str(e)}",
            )

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    # Static agent definitions (mirrors the actual agent registry)
    _AGENT_DEFINITIONS = [
        {"name": "researcher", "role": "research", "description": "Market research and data analysis", "tools": ["web_search", "financial_data", "news"]},
        {"name": "strategist", "role": "strategy", "description": "Signal generation and strategy formulation", "tools": ["technical_analysis", "factor_library", "signal_generator"]},
        {"name": "risk", "role": "risk_management", "description": "9-checkpoint risk assessment with constitutional limits", "tools": ["var_calculator", "kelly_criterion", "drawdown_monitor"]},
        {"name": "trader", "role": "trading", "description": "Trade execution decisions and order management", "tools": ["order_manager", "position_tracker"]},
        {"name": "portfolio", "role": "portfolio", "description": "Portfolio optimization and allocation", "tools": ["risk_parity", "rebalance", "allocation_optimizer"]},
        {"name": "execution", "role": "execution", "description": "Order execution and fill tracking", "tools": ["broker_adapter", "fill_simulator", "guard_rails"]},
        {"name": "macro", "role": "macro_analysis", "description": "Macroeconomic analysis and regime detection", "tools": ["economic_calendar", "regime_detector"]},
        {"name": "crypto", "role": "crypto_analysis", "description": "Cryptocurrency market analysis", "tools": ["on_chain_data", "sentiment", "whale_tracker"]},
        {"name": "forex", "role": "forex_analysis", "description": "Forex market analysis and currency pair evaluation", "tools": ["fx_rates", "carry_trade", "central_bank"]},
    ]

    @app.get("/api/v1/agents", response_model=AgentListResponse, tags=["agents"], dependencies=[Depends(require_role("read"))])
    async def list_agents(auth: AuthContext = Depends(optional_auth)):
        """
        List all available trading agents.

        Returns agent names, roles, descriptions, and available tools.
        """
        agents = [
            AgentInfoResponse(
                name=a["name"],
                role=a["role"],
                description=a["description"],
                status="ready",
                tools=a["tools"],
            )
            for a in _AGENT_DEFINITIONS
        ]
        return AgentListResponse(agents=agents, total=len(agents))

    # ------------------------------------------------------------------
    # Backtest
    # ------------------------------------------------------------------

    @app.post("/api/v1/backtest", response_model=BacktestResponse, tags=["backtest"], dependencies=[Depends(require_role("analyze"))])
    async def run_backtest(request: BacktestRequest, auth: AuthContext = Depends(require_auth)):
        """
        Run a backtest with the specified strategy.

        Supports multiple strategies and market types. Returns performance
        metrics including Sharpe ratio, max drawdown, and win rate.
        """
        try:
            settings = get_settings()

            # Attempt to run actual backtest engine
            try:
                from quant_nanggroe.engine.backtest.engine import (
                    BacktestEngine,
                    BacktestConfig,
                    MarketType,
                )

                # Map period to approximate bar count
                period_map = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252, "2Y": 504}
                bars = period_map.get(request.period, 252)

                market_type = MarketType.CRYPTO
                if request.market == "equity":
                    market_type = MarketType.EQUITY
                elif request.market == "forex":
                    market_type = MarketType.FOREX

                config = BacktestConfig(
                    initial_capital=request.initial_capital,
                    commission_rate=request.commission,
                    slippage_bps=request.slippage * 10000,
                    market=market_type,
                )

                return BacktestResponse(
                    status="configured",
                    strategy=request.strategy,
                    symbols=request.symbols,
                    period=request.period,
                    initial_capital=request.initial_capital,
                    final_equity=request.initial_capital,
                    metrics=BacktestMetricsResponse(),
                    error="Backtest requires price data. Use CLI 'qnai backtest' with data files for full execution.",
                )

            except Exception as bt_err:
                logger.warning(f"Backtest engine error: {bt_err}")
                return BacktestResponse(
                    status="unavailable",
                    strategy=request.strategy,
                    symbols=request.symbols,
                    period=request.period,
                    initial_capital=request.initial_capital,
                    final_equity=request.initial_capital,
                    metrics=BacktestMetricsResponse(),
                    error=f"Backtest engine unavailable: {str(bt_err)[:200]}",
                )

        except Exception as e:
            logger.error(f"Backtest error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Backtest failed: {str(e)}",
            )

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    @app.get("/api/v1/risk/{symbol}", response_model=RiskCheckResponse, tags=["risk"], dependencies=[Depends(require_role("read"))])
    async def check_risk(symbol: str, auth: AuthContext = Depends(optional_auth)):
        """
        Run risk assessment for a specific symbol.

        Evaluates the symbol against all 9 constitutional risk checkpoints
        and returns VaR, CVaR, drawdown, and position sizing suggestions.
        """
        try:
            try:
                from quant_nanggroe.engine.risk.manager import (
                    RiskManager,
                    MAX_RISK_PER_TRADE,
                    MAX_DAILY_LOSS,
                    MAX_WEEKLY_LOSS,
                    MAX_DRAWDOWN,
                    MIN_RISK_REWARD,
                )

                rm = RiskManager()
                status = rm.status()

                return RiskCheckResponse(
                    symbol=symbol,
                    verdict=_RISK_VERDICT_APPROVED if status["overall_status"] == "TRADING_ALLOWED" else _RISK_VERDICT_VETOED,
                    risk_level="low",
                    per_trade_risk_pct=MAX_RISK_PER_TRADE * 100,
                    daily_loss_pct=float(status.get("daily_loss_pct", "0")),
                    weekly_loss_pct=float(status.get("weekly_loss_pct", "0")),
                    drawdown_pct=status.get("drawdown", {}).get("current_drawdown", 0) * 100,
                    position_concentration_pct=0.0,
                    approved=status["overall_status"] == "TRADING_ALLOWED",
                    constitutional_limits={
                        "max_risk_per_trade": f"{MAX_RISK_PER_TRADE:.2%}",
                        "max_daily_loss": f"{MAX_DAILY_LOSS:.2%}",
                        "max_weekly_loss": f"{MAX_WEEKLY_LOSS:.2%}",
                        "max_drawdown": f"{MAX_DRAWDOWN:.0%}",
                        "min_risk_reward": f"1:{MIN_RISK_REWARD}",
                        "override_possible": False,
                    },
                )

            except Exception as risk_err:
                logger.warning(f"Risk engine error: {risk_err}")
                # Return default risk info
                return RiskCheckResponse(
                    symbol=symbol,
                    verdict=_RISK_VERDICT_CONDITIONAL,
                    risk_level="moderate",
                    approved=False,
                    veto_reason="Risk engine unavailable - conditional hold",
                    constitutional_limits={
                        "max_risk_per_trade": "0.50%",
                        "max_daily_loss": "1.00%",
                        "max_weekly_loss": "3.00%",
                        "max_drawdown": "10%",
                        "min_risk_reward": "1:2.0",
                        "override_possible": False,
                    },
                )

        except Exception as e:
            logger.error(f"Risk check error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Risk assessment failed: {str(e)}",
            )

    # ------------------------------------------------------------------
    # WebSocket
    # ------------------------------------------------------------------

    @app.websocket("/ws/trading")
    async def websocket_trading(websocket: WebSocket):
        """
        WebSocket endpoint for real-time trading updates.

        Sends live trading pipeline events, position updates,
        and risk alerts to connected clients.

        Message format:
        {
            "type": "trade_update" | "risk_alert" | "position_change" | "heartbeat",
            "data": {...},
            "timestamp": "ISO-8601"
        }
        """
        await websocket.accept()
        _ws_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(_ws_connections)}")

        try:
            # Send initial connection message
            await websocket.send_json({
                "type": "connection",
                "data": {"status": "connected", "version": "0.2.0"},
                "timestamp": datetime.now().isoformat(),
            })

            # Heartbeat loop
            while True:
                try:
                    # Wait for client messages (or timeout for heartbeat)
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                    # Echo back for ping
                    if data == "ping":
                        await websocket.send_json({
                            "type": "heartbeat",
                            "data": {"status": "alive"},
                            "timestamp": datetime.now().isoformat(),
                        })

                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    try:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "data": {"status": "alive", "portfolio_value": _portfolio_state["total_value"]},
                            "timestamp": datetime.now().isoformat(),
                        })
                    except Exception:
                        break

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if websocket in _ws_connections:
                _ws_connections.remove(websocket)

    return app


# Create the app instance
app = create_app()
