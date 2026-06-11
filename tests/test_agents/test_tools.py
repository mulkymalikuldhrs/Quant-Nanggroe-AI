"""
Tests for Agent Tools.

Validates all tool implementations for the 9 agent types.
Each tool should return valid JSON strings with expected fields.
"""

import json
import pytest

# Research tools
from quant_nanggroe.agents.researcher.tools import (
    web_search,
    sec_filing,
    news_fetch,
    financial_data,
    RESEARCH_TOOLS,
)

# Trader tools
from quant_nanggroe.agents.trader.tools import (
    place_order,
    get_position,
    get_portfolio,
    TRADER_TOOLS,
)

# Strategist tools
from quant_nanggroe.agents.strategist.tools import (
    compute_indicators,
    run_backtest,
    evaluate_strategy,
    STRATEGIST_TOOLS,
)

# Portfolio tools
from quant_nanggroe.agents.portfolio.tools import (
    optimize_portfolio,
    compute_allocation,
    rebalance,
    PORTFOLIO_TOOLS,
)

# Execution tools
from quant_nanggroe.agents.execution.tools import (
    submit_order,
    cancel_order,
    get_fills,
    EXECUTION_TOOLS,
)

# Macro tools
from quant_nanggroe.agents.macro.tools import (
    fetch_macro_data,
    detect_regime,
    analyze_correlations,
    MACRO_TOOLS,
)

# Crypto tools
from quant_nanggroe.agents.crypto.tools import (
    fetch_onchain,
    analyze_dex,
    check_contract_risk,
    CRYPTO_TOOLS,
)

# Forex tools
from quant_nanggroe.agents.forex.tools import (
    fetch_forex_data,
    analyze_carry,
    monitor_cbank,
    FOREX_TOOLS,
)


class TestResearchTools:
    """Test research agent tools."""

    def test_web_search(self):
        """Web search should return valid JSON."""
        result = json.loads(web_search.invoke({"query": "AAPL earnings"}))
        assert "query" in result
        assert "results" in result
        assert result["query"] == "AAPL earnings"

    def test_sec_filing(self):
        """SEC filing should return valid JSON."""
        result = json.loads(sec_filing.invoke({"symbol": "AAPL", "filing_type": "10-K"}))
        assert "symbol" in result
        assert result["symbol"] == "AAPL"
        assert "filings" in result

    def test_news_fetch(self):
        """News fetch should return valid JSON."""
        result = json.loads(news_fetch.invoke({"symbol": "MSFT", "days_back": 7}))
        assert "symbol" in result
        assert "articles" in result

    def test_financial_data(self):
        """Financial data should return valid JSON."""
        result = json.loads(financial_data.invoke({"symbol": "AAPL"}))
        assert "symbol" in result
        assert "metrics" in result

    def test_research_tools_list(self):
        """Should have all research tools."""
        assert len(RESEARCH_TOOLS) == 4
        names = [t.name for t in RESEARCH_TOOLS]
        assert "web_search" in names
        assert "sec_filing" in names
        assert "news_fetch" in names
        assert "financial_data" in names


class TestTraderTools:
    """Test trader agent tools."""

    def test_place_order(self):
        """Place order should return valid JSON."""
        result = json.loads(place_order.invoke({
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100,
        }))
        assert "order_id" in result
        assert result["symbol"] == "AAPL"
        assert result["status"] == "SUBMITTED"

    def test_get_position(self):
        """Get position should return valid JSON."""
        result = json.loads(get_position.invoke({"symbol": "AAPL"}))
        assert "symbol" in result
        assert "quantity" in result

    def test_get_portfolio(self):
        """Get portfolio should return valid JSON."""
        result = json.loads(get_portfolio.invoke({}))
        assert "total_value" in result
        assert "cash" in result

    def test_trader_tools_list(self):
        """Should have all trader tools."""
        assert len(TRADER_TOOLS) == 3


class TestStrategistTools:
    """Test strategist agent tools."""

    def test_compute_indicators(self):
        """Compute indicators should return valid JSON."""
        result = json.loads(compute_indicators.invoke({
            "symbol": "AAPL",
            "indicators": ["RSI", "MACD"],
        }))
        assert "symbol" in result
        assert "indicators" in result
        assert "RSI_14" in result["indicators"]

    def test_run_backtest(self):
        """Run backtest should return valid JSON."""
        result = json.loads(run_backtest.invoke({
            "symbol": "AAPL",
            "strategy": "momentum_crossover",
        }))
        assert "symbol" in result
        assert "sharpe_ratio" in result
        assert "total_return_pct" in result

    def test_evaluate_strategy(self):
        """Evaluate strategy should return valid JSON."""
        result = json.loads(evaluate_strategy.invoke({
            "strategy_name": "momentum",
        }))
        assert "strategy" in result
        assert "overall_score" in result

    def test_strategist_tools_list(self):
        """Should have all strategist tools."""
        assert len(STRATEGIST_TOOLS) == 3


class TestPortfolioTools:
    """Test portfolio agent tools."""

    def test_optimize_portfolio(self):
        """Optimize portfolio should return valid JSON."""
        result = json.loads(optimize_portfolio.invoke({
            "symbols": ["AAPL", "MSFT", "GOOGL"],
        }))
        assert "allocation" in result
        assert "method" in result

    def test_compute_allocation(self):
        """Compute allocation should return valid JSON."""
        result = json.loads(compute_allocation.invoke({
            "current_positions": {"AAPL": 30000},
            "target_allocation": {"AAPL": 40.0, "MSFT": 30.0, "GOOGL": 30.0},
            "total_value": 100000,
        }))
        assert "required_trades" in result

    def test_rebalance(self):
        """Rebalance should return valid JSON."""
        result = json.loads(rebalance.invoke({
            "current_allocation": {"AAPL": 45.0, "MSFT": 25.0},
            "target_allocation": {"AAPL": 40.0, "MSFT": 30.0},
        }))
        assert "needs_rebalance" in result
        assert "drifts" in result

    def test_portfolio_tools_list(self):
        """Should have all portfolio tools."""
        assert len(PORTFOLIO_TOOLS) == 3


class TestExecutionTools:
    """Test execution agent tools."""

    def test_submit_order(self):
        """Submit order should return valid JSON."""
        result = json.loads(submit_order.invoke({
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100,
            "order_type": "limit",
            "price": 150.0,
        }))
        assert "order_id" in result
        assert result["status"] == "SUBMITTED"

    def test_cancel_order(self):
        """Cancel order should return valid JSON."""
        result = json.loads(cancel_order.invoke({
            "order_id": "ORD-123",
            "reason": "User request",
        }))
        assert result["status"] == "CANCELLED"

    def test_get_fills(self):
        """Get fills should return valid JSON."""
        result = json.loads(get_fills.invoke({}))
        assert "fills" in result

    def test_execution_tools_list(self):
        """Should have all execution tools."""
        assert len(EXECUTION_TOOLS) == 3


class TestMacroTools:
    """Test macro agent tools."""

    def test_fetch_macro_data(self):
        """Fetch macro data should return valid JSON."""
        result = json.loads(fetch_macro_data.invoke({}))
        assert "indicators" in result
        assert "GDP_growth_yoy" in result["indicators"]

    def test_detect_regime(self):
        """Detect regime should return valid JSON."""
        result = json.loads(detect_regime.invoke({
            "vix_level": 35.0,
        }))
        assert "regime" in result
        assert "confidence" in result

    def test_analyze_correlations(self):
        """Analyze correlations should return valid JSON."""
        result = json.loads(analyze_correlations.invoke({
            "symbols": ["SPY", "TLT", "GLD"],
        }))
        assert "correlations" in result

    def test_macro_tools_list(self):
        """Should have all macro tools."""
        assert len(MACRO_TOOLS) == 3


class TestCryptoTools:
    """Test crypto agent tools."""

    def test_fetch_onchain(self):
        """Fetch on-chain data should return valid JSON."""
        result = json.loads(fetch_onchain.invoke({"symbol": "BTC"}))
        assert "metrics" in result
        assert "active_addresses_24h" in result["metrics"]

    def test_analyze_dex(self):
        """Analyze DEX should return valid JSON."""
        result = json.loads(analyze_dex.invoke({"symbol": "ETH"}))
        assert "analysis" in result
        assert "total_volume_24h_usd" in result["analysis"]

    def test_check_contract_risk(self):
        """Check contract risk should return valid JSON."""
        result = json.loads(check_contract_risk.invoke({
            "address": "0x1234567890abcdef",
        }))
        assert "risk_assessment" in result

    def test_crypto_tools_list(self):
        """Should have all crypto tools."""
        assert len(CRYPTO_TOOLS) == 3


class TestForexTools:
    """Test forex agent tools."""

    def test_fetch_forex_data(self):
        """Fetch forex data should return valid JSON."""
        result = json.loads(fetch_forex_data.invoke({"pair": "EURUSD"}))
        assert "pair" in result
        assert "support_levels" in result

    def test_analyze_carry(self):
        """Analyze carry should return valid JSON."""
        result = json.loads(analyze_carry.invoke({
            "base_currency": "JPY",
            "quote_currency": "USD",
        }))
        assert "interest_differential" in result
        assert "carry_direction" in result

    def test_monitor_cbank(self):
        """Monitor central bank should return valid JSON."""
        result = json.loads(monitor_cbank.invoke({"central_bank": "FED"}))
        assert "current_rate" in result
        assert "next_meeting_date" in result

    def test_forex_tools_list(self):
        """Should have all forex tools."""
        assert len(FOREX_TOOLS) == 3


class TestToolCounts:
    """Verify the total number of tools across all agents."""

    def test_total_tools(self):
        """Should have tools for all 9 agents."""
        total = (
            len(RESEARCH_TOOLS) +
            len(TRADER_TOOLS) +
            len(STRATEGIST_TOOLS) +
            len(PORTFOLIO_TOOLS) +
            len(EXECUTION_TOOLS) +
            len(MACRO_TOOLS) +
            len(CRYPTO_TOOLS) +
            len(FOREX_TOOLS)
        )
        # 8 agents with tools (risk tools are in their own test)
        assert total >= 24  # At least 3 tools per agent × 8 agents
