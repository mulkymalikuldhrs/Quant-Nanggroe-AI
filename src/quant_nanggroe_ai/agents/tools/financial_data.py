"""
Financial Data Tools — FinancialDatasets.ai Integration
=======================================================
Ported from ai-financial-agent (C2-CORE merge, Task 8-c).

Provides 7 financial data tools that access the FinancialDatasets.ai API:
    1. get_stock_prices   — Snapshot + historical price data
    2. get_income_statements — Company income statements
    3. get_balance_sheets — Company balance sheets
    4. get_cash_flow_statements — Cash flow statements
    5. get_financial_metrics — Derived financial metrics (P/E, margins, etc.)
    6. search_stocks_by_filters — Stock screening with financial criteria
    7. get_news — Company news and events

All tools use httpx for async HTTP requests and return structured
Pydantic models. A duplicate-call cache prevents redundant API requests.

Usage::

    from quant_nanggroe_ai.agents.tools.financial_data import FinancialDataTool

    tool = FinancialDataTool(api_key="your-financialdatasets-api-key")

    # Get stock prices
    prices = await tool.get_stock_prices("AAPL")

    # Search for stocks
    results = await tool.search_stocks_by_filters([
        {"field": "revenue", "operator": "gt", "value": 50_000_000_000},
        {"field": "net_income", "operator": "gt", "value": 1_000_000_000},
    ])
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from enum import Enum
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════

BASE_URL = "https://api.financialdatasets.ai"

# Valid fields for stock search filter (ported from stock-filters.ts)
VALID_STOCK_SEARCH_FILTERS: list[str] = [
    # Income statement fields
    "cost_of_revenue",
    "dividends_per_common_share",
    "earnings_per_share",
    "earnings_per_share_diluted",
    "ebit",
    "gross_profit",
    "income_tax_expense",
    "interest_expense",
    "net_income",
    "operating_expense",
    "operating_income",
    "research_and_development",
    "revenue",
    "selling_general_and_administrative_expenses",
    "weighted_average_shares",
    # Balance sheet fields
    "accumulated_other_comprehensive_income",
    "cash_and_equivalents",
    "current_assets",
    "current_debt",
    "current_investments",
    "current_liabilities",
    "deferred_revenue",
    "deposit_liabilities",
    "goodwill_and_intangible_assets",
    "inventory",
    "investments",
    "non_current_assets",
    "non_current_debt",
    "non_current_investments",
    "non_current_liabilities",
    "outstanding_shares",
    "property_plant_and_equipment",
    "retained_earnings",
    "shareholders_equity",
    "tax_assets",
    "tax_liabilities",
    "total_assets",
    "total_debt",
    "total_liabilities",
    "trade_and_non_trade_payables",
    "trade_and_non_trade_receivables",
    # Cash flow fields
    "business_acquisitions_and_disposals",
    "capital_expenditure",
    "change_in_cash_and_equivalents",
    "depreciation_and_amortization",
    "dividends_and_other_cash_distributions",
    "effect_of_exchange_rate_changes",
    "investment_acquisitions_and_disposals",
    "issuance_or_purchase_of_equity_shares",
    "issuance_or_repayment_of_debt_securities",
    "net_cash_flow_from_financing",
    "net_cash_flow_from_investing",
    "net_cash_flow_from_operations",
    "share_based_compensation",
    # Derived metrics
    "market_cap",
    "enterprise_value",
    "price_to_earnings_ratio",
    "price_to_book_ratio",
    "price_to_sales_ratio",
    "enterprise_value_to_ebitda_ratio",
    "enterprise_value_to_revenue_ratio",
    "free_cash_flow_yield",
    "peg_ratio",
    # Margins
    "gross_margin",
    "operating_margin",
    "net_margin",
    # Returns
    "return_on_equity",
    "return_on_assets",
    "return_on_invested_capital",
    # Turnover ratios
    "asset_turnover",
    "inventory_turnover",
    "receivables_turnover",
    "days_sales_outstanding",
    "operating_cycle",
    "working_capital_turnover",
    # Liquidity
    "current_ratio",
    "quick_ratio",
    "cash_ratio",
    "operating_cash_flow_ratio",
    # Leverage
    "debt_to_equity",
    "debt_to_assets",
    "interest_coverage",
    # Growth
    "revenue_growth",
    "earnings_growth",
    "book_value_growth",
    "earnings_per_share_growth",
    "free_cash_flow_growth",
    "operating_income_growth",
    "ebitda_growth",
    # Per-share
    "payout_ratio",
    "earnings_per_share",
    "book_value_per_share",
    "free_cash_flow_per_share",
]


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class PriceInterval(str, Enum):
    """Valid intervals for historical price data."""

    SECOND = "second"
    MINUTE = "minute"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class FinancialPeriod(str, Enum):
    """Valid periods for financial statements."""

    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    TTM = "ttm"


class FilterOperator(str, Enum):
    """Valid operators for stock search filters."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"


class StockPriceSnapshot(BaseModel):
    """Current price snapshot for a stock."""

    ticker: str = ""
    price: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    market_cap: float = 0.0
    volume: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class StockPricePoint(BaseModel):
    """A single historical price data point."""

    timestamp: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0


class StockPrices(BaseModel):
    """Combined snapshot and historical price data for a stock."""

    ticker: str = ""
    snapshot: StockPriceSnapshot = Field(default_factory=StockPriceSnapshot)
    historical: list[StockPricePoint] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class IncomeStatement(BaseModel):
    """A single income statement record."""

    ticker: str = ""
    report_period: str = ""
    period: str = ""
    revenue: float = 0.0
    cost_of_revenue: float = 0.0
    gross_profit: float = 0.0
    operating_income: float = 0.0
    net_income: float = 0.0
    earnings_per_share: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class BalanceSheet(BaseModel):
    """A single balance sheet record."""

    ticker: str = ""
    report_period: str = ""
    period: str = ""
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    shareholders_equity: float = 0.0
    cash_and_equivalents: float = 0.0
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    total_debt: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class CashFlowStatement(BaseModel):
    """A single cash flow statement record."""

    ticker: str = ""
    report_period: str = ""
    period: str = ""
    net_cash_flow_from_operations: float = 0.0
    net_cash_flow_from_investing: float = 0.0
    net_cash_flow_from_financing: float = 0.0
    capital_expenditure: float = 0.0
    free_cash_flow: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class FinancialMetric(BaseModel):
    """A single financial metrics record (derived ratios)."""

    ticker: str = ""
    report_period: str = ""
    period: str = ""
    market_cap: float = 0.0
    price_to_earnings_ratio: float = 0.0
    price_to_book_ratio: float = 0.0
    price_to_sales_ratio: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    return_on_equity: float = 0.0
    return_on_assets: float = 0.0
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class StockFilter(BaseModel):
    """A single filter criterion for stock search."""

    field: str
    operator: FilterOperator = FilterOperator.GT
    value: float = 0.0


class StockSearchResult(BaseModel):
    """A single stock matching a search filter."""

    ticker: str = ""
    name: str = ""
    market_cap: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class NewsArticle(BaseModel):
    """A single news article about a company."""

    title: str = ""
    date: str = ""
    url: str = ""
    source: str = ""
    summary: str = ""
    sentiment: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# FINANCIAL DATA TOOL
# ══════════════════════════════════════════════════════════════════════


class FinancialDataTool:
    """
    Financial data tools using the FinancialDatasets.ai API.

    Ported from ai-financial-agent TypeScript (C2-CORE merge, Task 8-c).
    Provides 7 tools for stock prices, financials, screening, and news.

    Args:
        api_key: FinancialDatasets.ai API key
        base_url: API base URL (default: https://api.financialdatasets.ai)
        timeout: Request timeout in seconds
        cache_enabled: Whether to cache duplicate requests

    Example::

        tool = FinancialDataTool(api_key="fd-...")
        prices = await tool.get_stock_prices("AAPL")
        income = await tool.get_income_statements("MSFT", period="annual")
        news = await tool.get_news("TSLA", limit=3)
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        cache_enabled: bool = True,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._cache_enabled = cache_enabled
        self._call_cache: set[str] = set()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._api_key:
                headers["X-API-Key"] = self._api_key
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=headers,
            )
        return self._http_client

    def _should_execute(self, tool_name: str, params: Any) -> bool:
        """Check if a tool call should be executed (dedup cache)."""
        if not self._cache_enabled:
            return True
        key = f"{tool_name}:{str(params)}"
        if key in self._call_cache:
            logger.debug("Skipping duplicate call: %s", key)
            return False
        self._call_cache.add(key)
        return True

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a GET request."""
        client = await self._get_client()
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, json: dict[str, Any]) -> Any:
        """Execute a POST request."""
        client = await self._get_client()
        response = await client.post(path, json=json)
        response.raise_for_status()
        return response.json()

    # ── Tool 1: get_stock_prices ────────────────────────────────────

    async def get_stock_prices(
        self,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
        interval: PriceInterval = PriceInterval.DAY,
        interval_multiplier: int = 1,
    ) -> StockPrices:
        """
        Get stock prices (snapshot + historical).

        Ported from ai-financial-agent getStockPrices tool.

        Args:
            ticker: Stock ticker symbol (e.g. "AAPL")
            start_date: Start date for historical data (YYYY-MM-DD), default 1 month ago
            end_date: End date for historical data (YYYY-MM-DD), default today
            interval: Price interval (second, minute, day, week, month, year)
            interval_multiplier: Interval multiplier (e.g. 5 for 5-minute bars)

        Returns:
            StockPrices with snapshot and historical data
        """
        if not self._should_execute("get_stock_prices", (ticker, start_date, end_date, interval, interval_multiplier)):
            return StockPrices(ticker=ticker)

        today = date.today()
        one_month_ago = today - timedelta(days=30)

        try:
            # Get snapshot price
            snapshot_data = await self._get(f"/prices/snapshot", {"ticker": ticker})
            snapshot = StockPriceSnapshot(
                ticker=ticker,
                price=float(snapshot_data.get("price", 0)),
                change=float(snapshot_data.get("change", 0)),
                change_percent=float(snapshot_data.get("change_percent", 0)),
                market_cap=float(snapshot_data.get("market_cap", 0)),
                volume=float(snapshot_data.get("volume", 0)),
                raw_response=snapshot_data,
            )
        except Exception as exc:
            logger.warning("Snapshot price failed for %s: %s", ticker, exc)
            snapshot = StockPriceSnapshot(ticker=ticker)

        try:
            # Get historical prices
            params = {
                "ticker": ticker,
                "start_date": start_date or one_month_ago.isoformat(),
                "end_date": end_date or today.isoformat(),
                "interval": interval.value,
                "interval_multiplier": str(interval_multiplier),
            }
            hist_data = await self._get("/prices/", params)
            prices_list = hist_data if isinstance(hist_data, list) else hist_data.get("prices", [])

            historical = []
            for p in prices_list:
                historical.append(StockPricePoint(
                    timestamp=p.get("time", p.get("timestamp", "")),
                    open=float(p.get("open", 0)),
                    high=float(p.get("high", 0)),
                    low=float(p.get("low", 0)),
                    close=float(p.get("close", 0)),
                    volume=float(p.get("volume", 0)),
                ))
        except Exception as exc:
            logger.error("Historical prices failed for %s: %s", ticker, exc)
            historical = []

        return StockPrices(
            ticker=ticker,
            snapshot=snapshot,
            historical=historical,
            raw_response={"snapshot": snapshot_data if 'snapshot_data' in dir() else {}, "historical_count": len(historical)},
        )

    # ── Tool 2: get_income_statements ──────────────────────────────

    async def get_income_statements(
        self,
        ticker: str,
        period: FinancialPeriod = FinancialPeriod.TTM,
        limit: int = 5,
        report_period_lte: str | None = None,
        report_period_gte: str | None = None,
    ) -> list[IncomeStatement]:
        """
        Get income statements for a company.

        Ported from ai-financial-agent getIncomeStatements tool.

        Args:
            ticker: Stock ticker symbol
            period: "quarterly", "annual", or "ttm"
            limit: Number of statements to return (min 4)
            report_period_lte: Upper bound date (YYYY-MM-DD)
            report_period_gte: Lower bound date (YYYY-MM-DD)

        Returns:
            List of IncomeStatement
        """
        if not self._should_execute("get_income_statements", (ticker, period, limit)):
            return []

        params: dict[str, Any] = {
            "ticker": ticker,
            "period": period.value,
            "limit": max(limit, 4),
        }
        if report_period_lte:
            params["report_period_lte"] = report_period_lte
        if report_period_gte:
            params["report_period_gte"] = report_period_gte

        try:
            data = await self._get("/financials/income-statements/", params)
            items = data if isinstance(data, list) else data.get("income_statements", [])
            return [
                IncomeStatement(
                    ticker=s.get("ticker", ticker),
                    report_period=s.get("report_period", ""),
                    period=s.get("period", period.value),
                    revenue=float(s.get("revenue", 0)),
                    cost_of_revenue=float(s.get("cost_of_revenue", 0)),
                    gross_profit=float(s.get("gross_profit", 0)),
                    operating_income=float(s.get("operating_income", 0)),
                    net_income=float(s.get("net_income", 0)),
                    earnings_per_share=float(s.get("earnings_per_share", 0)),
                    raw_response=s,
                )
                for s in items
            ]
        except Exception as exc:
            logger.error("Get income statements failed for %s: %s", ticker, exc)
            return []

    # ── Tool 3: get_balance_sheets ─────────────────────────────────

    async def get_balance_sheets(
        self,
        ticker: str,
        period: FinancialPeriod = FinancialPeriod.TTM,
        limit: int = 5,
        report_period_lte: str | None = None,
        report_period_gte: str | None = None,
    ) -> list[BalanceSheet]:
        """
        Get balance sheets for a company.

        Ported from ai-financial-agent getBalanceSheets tool.

        Args:
            ticker: Stock ticker symbol
            period: "quarterly", "annual", or "ttm"
            limit: Number of statements to return (min 4)
            report_period_lte: Upper bound date (YYYY-MM-DD)
            report_period_gte: Lower bound date (YYYY-MM-DD)

        Returns:
            List of BalanceSheet
        """
        if not self._should_execute("get_balance_sheets", (ticker, period, limit)):
            return []

        params: dict[str, Any] = {
            "ticker": ticker,
            "period": period.value,
            "limit": max(limit, 4),
        }
        if report_period_lte:
            params["report_period_lte"] = report_period_lte
        if report_period_gte:
            params["report_period_gte"] = report_period_gte

        try:
            data = await self._get("/financials/balance-sheets/", params)
            items = data if isinstance(data, list) else data.get("balance_sheets", [])
            return [
                BalanceSheet(
                    ticker=b.get("ticker", ticker),
                    report_period=b.get("report_period", ""),
                    period=b.get("period", period.value),
                    total_assets=float(b.get("total_assets", 0)),
                    total_liabilities=float(b.get("total_liabilities", 0)),
                    shareholders_equity=float(b.get("shareholders_equity", 0)),
                    cash_and_equivalents=float(b.get("cash_and_equivalents", 0)),
                    current_assets=float(b.get("current_assets", 0)),
                    current_liabilities=float(b.get("current_liabilities", 0)),
                    total_debt=float(b.get("total_debt", 0)),
                    raw_response=b,
                )
                for b in items
            ]
        except Exception as exc:
            logger.error("Get balance sheets failed for %s: %s", ticker, exc)
            return []

    # ── Tool 4: get_cash_flow_statements ───────────────────────────

    async def get_cash_flow_statements(
        self,
        ticker: str,
        period: FinancialPeriod = FinancialPeriod.TTM,
        limit: int = 5,
        report_period_lte: str | None = None,
        report_period_gte: str | None = None,
    ) -> list[CashFlowStatement]:
        """
        Get cash flow statements for a company.

        Ported from ai-financial-agent getCashFlowStatements tool.

        Args:
            ticker: Stock ticker symbol
            period: "quarterly", "annual", or "ttm"
            limit: Number of statements to return (min 4)
            report_period_lte: Upper bound date (YYYY-MM-DD)
            report_period_gte: Lower bound date (YYYY-MM-DD)

        Returns:
            List of CashFlowStatement
        """
        if not self._should_execute("get_cash_flow_statements", (ticker, period, limit)):
            return []

        params: dict[str, Any] = {
            "ticker": ticker,
            "period": period.value,
            "limit": max(limit, 4),
        }
        if report_period_lte:
            params["report_period_lte"] = report_period_lte
        if report_period_gte:
            params["report_period_gte"] = report_period_gte

        try:
            data = await self._get("/financials/cash-flow-statements/", params)
            items = data if isinstance(data, list) else data.get("cash_flow_statements", [])
            return [
                CashFlowStatement(
                    ticker=c.get("ticker", ticker),
                    report_period=c.get("report_period", ""),
                    period=c.get("period", period.value),
                    net_cash_flow_from_operations=float(c.get("net_cash_flow_from_operations", 0)),
                    net_cash_flow_from_investing=float(c.get("net_cash_flow_from_investing", 0)),
                    net_cash_flow_from_financing=float(c.get("net_cash_flow_from_financing", 0)),
                    capital_expenditure=float(c.get("capital_expenditure", 0)),
                    free_cash_flow=float(c.get("free_cash_flow", 0)),
                    raw_response=c,
                )
                for c in items
            ]
        except Exception as exc:
            logger.error("Get cash flow statements failed for %s: %s", ticker, exc)
            return []

    # ── Tool 5: get_financial_metrics ──────────────────────────────

    async def get_financial_metrics(
        self,
        ticker: str,
        period: FinancialPeriod = FinancialPeriod.TTM,
        limit: int = 5,
        report_period_lte: str | None = None,
        report_period_gte: str | None = None,
    ) -> list[FinancialMetric]:
        """
        Get derived financial metrics for a company.

        Includes ratios like P/E, margins, returns, leverage, etc.
        that cannot be found in standard financial statements.

        Ported from ai-financial-agent getFinancialMetrics tool.

        Args:
            ticker: Stock ticker symbol
            period: "quarterly", "annual", or "ttm"
            limit: Number of metric records to return (min 4)
            report_period_lte: Upper bound date (YYYY-MM-DD)
            report_period_gte: Lower bound date (YYYY-MM-DD)

        Returns:
            List of FinancialMetric
        """
        if not self._should_execute("get_financial_metrics", (ticker, period, limit)):
            return []

        params: dict[str, Any] = {
            "ticker": ticker,
            "period": period.value,
            "limit": max(limit, 4),
        }
        if report_period_lte:
            params["report_period_lte"] = report_period_lte
        if report_period_gte:
            params["report_period_gte"] = report_period_gte

        try:
            data = await self._get("/financial-metrics/", params)
            items = data if isinstance(data, list) else data.get("financial_metrics", [])
            return [
                FinancialMetric(
                    ticker=m.get("ticker", ticker),
                    report_period=m.get("report_period", ""),
                    period=m.get("period", period.value),
                    market_cap=float(m.get("market_cap", 0)),
                    price_to_earnings_ratio=float(m.get("price_to_earnings_ratio", 0)),
                    price_to_book_ratio=float(m.get("price_to_book_ratio", 0)),
                    price_to_sales_ratio=float(m.get("price_to_sales_ratio", 0)),
                    gross_margin=float(m.get("gross_margin", 0)),
                    operating_margin=float(m.get("operating_margin", 0)),
                    net_margin=float(m.get("net_margin", 0)),
                    return_on_equity=float(m.get("return_on_equity", 0)),
                    return_on_assets=float(m.get("return_on_assets", 0)),
                    debt_to_equity=float(m.get("debt_to_equity", 0)),
                    current_ratio=float(m.get("current_ratio", 0)),
                    raw_response=m,
                )
                for m in items
            ]
        except Exception as exc:
            logger.error("Get financial metrics failed for %s: %s", ticker, exc)
            return []

    # ── Tool 6: search_stocks_by_filters ───────────────────────────

    async def search_stocks_by_filters(
        self,
        filters: list[StockFilter | dict[str, Any]],
        period: FinancialPeriod = FinancialPeriod.TTM,
        limit: int = 5,
        order_by: str = "-report_period",
    ) -> list[StockSearchResult]:
        """
        Search for stocks based on financial criteria.

        Use this tool when asked to find or screen stocks based on
        financial metrics like revenue, net_income, debt, etc.

        Ported from ai-financial-agent searchStocksByFilters tool.

        Args:
            filters: List of filter criteria, e.g.
                [{"field": "revenue", "operator": "gt", "value": 50000000000}]
            period: "quarterly", "annual", or "ttm"
            limit: Number of stocks to return
            order_by: Sort order (default: newest first)

        Returns:
            List of StockSearchResult
        """
        # Normalize filters
        normalized_filters = []
        for f in filters:
            if isinstance(f, StockFilter):
                normalized_filters.append({
                    "field": f.field,
                    "operator": f.operator.value,
                    "value": f.value,
                })
            elif isinstance(f, dict):
                normalized_filters.append({
                    "field": f.get("field", ""),
                    "operator": f.get("operator", "gt"),
                    "value": float(f.get("value", 0)),
                })

        if not self._should_execute("search_stocks_by_filters", (str(normalized_filters), period, limit)):
            return []

        # Validate filter fields
        for nf in normalized_filters:
            if nf["field"] not in VALID_STOCK_SEARCH_FILTERS:
                logger.warning("Unknown filter field: %s", nf["field"])

        try:
            data = await self._post("/financials/search/", {
                "filters": normalized_filters,
                "period": period.value,
                "limit": limit,
            })
            items = data if isinstance(data, list) else data.get("results", data.get("stocks", []))
            return [
                StockSearchResult(
                    ticker=s.get("ticker", ""),
                    name=s.get("name", ""),
                    market_cap=float(s.get("market_cap", 0)),
                    raw_response=s,
                )
                for s in items
            ]
        except Exception as exc:
            logger.error("Search stocks by filters failed: %s", exc)
            return []

    # ── Tool 7: get_news ───────────────────────────────────────────

    async def get_news(
        self,
        ticker: str,
        limit: int = 5,
    ) -> list[NewsArticle]:
        """
        Get news and latest events for a company.

        Ported from ai-financial-agent getNews tool.

        Args:
            ticker: Stock ticker symbol
            limit: Number of articles to return

        Returns:
            List of NewsArticle
        """
        if not self._should_execute("get_news", (ticker, limit)):
            return []

        try:
            data = await self._get("/news/", {"ticker": ticker, "limit": limit})
            items = data if isinstance(data, list) else data.get("news", [])
            return [
                NewsArticle(
                    title=a.get("title", ""),
                    date=a.get("date", a.get("published_at", "")),
                    url=a.get("url", ""),
                    source=a.get("source", ""),
                    summary=a.get("summary", a.get("description", "")),
                    sentiment=a.get("sentiment", ""),
                    raw_response=a,
                )
                for a in items
            ]
        except Exception as exc:
            logger.error("Get news failed for %s: %s", ticker, exc)
            return []

    # ── Utility ────────────────────────────────────────────────────

    def clear_cache(self) -> None:
        """Clear the duplicate-call cache."""
        self._call_cache.clear()

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


def create_financial_data_tool_from_env() -> FinancialDataTool:
    """
    Create a FinancialDataTool from environment variables.

    Requires: FINANCIAL_DATASETS_API_KEY
    Optional: FINANCIAL_DATASETS_BASE_URL, FINANCIAL_DATASETS_TIMEOUT
    """
    import os

    api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY", "")
    base_url = os.environ.get("FINANCIAL_DATASETS_BASE_URL", BASE_URL)
    timeout = float(os.environ.get("FINANCIAL_DATASETS_TIMEOUT", "30"))

    return FinancialDataTool(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )
