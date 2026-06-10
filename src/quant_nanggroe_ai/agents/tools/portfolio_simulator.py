"""
Portfolio Simulator — adapted from ai-engineering-hub stock-portfolio-analysis-agent.

Provides:
  - Single-shot and DCA (dollar-cost averaging) investment simulation
  - SPY benchmark comparison
  - Portfolio allocation & return calculations
  - Bull/bear insight generation scaffolding

All imports use quant_nanggroe_ai.* package paths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class InvestmentStrategy(str, Enum):
    """Supported investment strategies."""
    SINGLE_SHOT = "single_shot"
    DCA_1D = "1d"
    DCA_5D = "5d"
    DCA_7D = "7d"
    DCA_1MO = "1mo"
    DCA_3MO = "3mo"
    DCA_6MO = "6mo"
    DCA_1Y = "1y"


@dataclass
class InvestmentRequest:
    """Structured investment request parsed from user input."""
    ticker_symbols: List[str]
    investment_date: str  # ISO date string, e.g. "2023-01-01"
    amounts: List[float]  # one per ticker
    strategy: InvestmentStrategy = InvestmentStrategy.SINGLE_SHOT
    add_to_portfolio: bool = True


@dataclass
class HoldingResult:
    """Result for a single ticker holding."""
    ticker: str
    shares: float
    invested: float
    current_price: float
    current_value: float
    absolute_return: float
    percent_return: float
    percent_allocation: float


@dataclass
class SimulationResult:
    """Complete result of a portfolio simulation run."""
    holdings: List[HoldingResult] = field(default_factory=list)
    total_invested: float = 0.0
    total_value: float = 0.0
    remaining_cash: float = 0.0
    investment_log: List[str] = field(default_factory=list)
    add_funds_needed: bool = False
    add_funds_dates: List[Tuple[str, str, float, float]] = field(default_factory=list)
    performance_data: List[Dict[str, Any]] = field(default_factory=list)
    spy_total_value: float = 0.0
    spy_total_invested: float = 0.0
    spy_percent_return: float = 0.0


# ---------------------------------------------------------------------------
# Portfolio Simulator
# ---------------------------------------------------------------------------

class PortfolioSimulator:
    """
    Simulates investment strategies and benchmarks against SPY.

    Adapted from ai-engineering-hub/stock-portfolio-analysis-agent with:
      - Standalone design (no CrewAI/AG-UI/CopilotKit dependencies)
      - Pydantic-compatible dataclasses
      - Flexible price data input (DataFrame or callable fetcher)
      - Proper error handling and logging
    """

    DEFAULT_BENCHMARK = "SPY"
    MAX_HISTORY_YEARS = 4

    def __init__(
        self,
        price_data: Optional[pd.DataFrame] = None,
        benchmark_ticker: str = DEFAULT_BENCHMARK,
        benchmark_data: Optional[pd.Series] = None,
    ) -> None:
        """
        Args:
            price_data: DataFrame with DatetimeIndex and ticker columns (Close prices).
                        If None, must be provided via simulate().
            benchmark_ticker: Ticker symbol for benchmark comparison.
            benchmark_data: Series with DatetimeIndex for benchmark prices.
        """
        self.price_data = price_data
        self.benchmark_ticker = benchmark_ticker
        self.benchmark_data = benchmark_data

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def simulate(
        self,
        request: InvestmentRequest,
        existing_holdings: Optional[Dict[str, float]] = None,
        available_cash: Optional[float] = None,
        price_data: Optional[pd.DataFrame] = None,
    ) -> SimulationResult:
        """
        Run a full portfolio simulation.

        Args:
            request: Parsed investment request.
            existing_holdings: Dict of {ticker: shares} already held.
            available_cash: Cash available for investment. If None, sums request amounts.
            price_data: Override price data for this simulation.

        Returns:
            SimulationResult with complete analysis.
        """
        data = price_data or self.price_data
        if data is None or data.empty:
            logger.error("No price data available for simulation.")
            return SimulationResult()

        # Validate and adjust investment date
        investment_date = self._validate_date(request.investment_date)
        data = data.sort_index()

        # Filter data to investment period
        date_mask = data.index >= investment_date
        if not date_mask.any():
            logger.error("Investment date is after all available price data.")
            return SimulationResult()
        data = data.loc[date_mask]

        if data.empty:
            logger.error("No price data available after investment date filter.")
            return SimulationResult()

        # Initialize
        total_cash = available_cash if available_cash is not None else sum(request.amounts)
        holdings: Dict[str, float] = dict(existing_holdings or {})
        for t in request.ticker_symbols:
            holdings.setdefault(t, 0.0)

        investment_log: List[str] = []
        add_funds_needed = False
        add_funds_dates: List[Tuple[str, str, float, float]] = []

        # Distribute amounts if single amount for multiple tickers
        amounts = list(request.amounts)
        if len(amounts) == 1 and len(request.ticker_symbols) > 1:
            per_ticker = amounts[0] / len(request.ticker_symbols)
            amounts = [per_ticker] * len(request.ticker_symbols)

        # Execute investment strategy
        if request.strategy == InvestmentStrategy.SINGLE_SHOT:
            total_cash, add_funds_needed = self._execute_single_shot(
                data, request.ticker_symbols, amounts, holdings,
                total_cash, investment_log, add_funds_dates,
            )
        else:
            total_cash, add_funds_needed = self._execute_dca(
                data, request.ticker_symbols, amounts, holdings,
                total_cash, investment_log, add_funds_dates,
            )

        # Calculate final metrics
        result = self._calculate_results(
            data, holdings, amounts, request.ticker_symbols,
            total_cash, investment_log, add_funds_needed, add_funds_dates,
            request.strategy,
        )

        # Run benchmark comparison
        self._run_benchmark(data, result, request.strategy, sum(a for a in amounts))

        return result

    # -----------------------------------------------------------------------
    # Investment Strategies
    # -----------------------------------------------------------------------

    def _execute_single_shot(
        self,
        data: pd.DataFrame,
        tickers: List[str],
        amounts: List[float],
        holdings: Dict[str, float],
        total_cash: float,
        investment_log: List[str],
        add_funds_dates: List[Tuple[str, str, float, float]],
    ) -> Tuple[float, bool]:
        """Execute single-shot (lump-sum) investment strategy."""
        add_funds_needed = False
        first_date = data.index[0]
        row = data.loc[first_date]

        for idx, ticker in enumerate(tickers):
            if ticker not in row or pd.isna(row[ticker]):
                investment_log.append(
                    f"{first_date.date()}: No price data for {ticker}."
                )
                add_funds_needed = True
                continue

            price = float(row[ticker])
            allocated = amounts[idx]

            if total_cash >= allocated and allocated >= price:
                shares_to_buy = allocated // price
                if shares_to_buy > 0:
                    cost = shares_to_buy * price
                    holdings[ticker] = holdings.get(ticker, 0.0) + shares_to_buy
                    total_cash -= cost
                    investment_log.append(
                        f"{first_date.date()}: Bought {shares_to_buy:.2f} shares "
                        f"of {ticker} at ${price:.2f} (cost: ${cost:.2f})"
                    )
                else:
                    investment_log.append(
                        f"{first_date.date()}: Allocated ${allocated:.2f} insufficient "
                        f"for {ticker} at ${price:.2f}."
                    )
                    add_funds_needed = True
                    add_funds_dates.append(
                        (str(first_date.date()), ticker, price, allocated)
                    )
            else:
                investment_log.append(
                    f"{first_date.date()}: Insufficient cash for {ticker} "
                    f"at ${price:.2f}. Available: ${total_cash:.2f}"
                )
                add_funds_needed = True
                add_funds_dates.append(
                    (str(first_date.date()), ticker, price, total_cash)
                )

        return total_cash, add_funds_needed

    def _execute_dca(
        self,
        data: pd.DataFrame,
        tickers: List[str],
        amounts: List[float],
        holdings: Dict[str, float],
        total_cash: float,
        investment_log: List[str],
        add_funds_dates: List[Tuple[str, str, float, float]],
    ) -> Tuple[float, bool]:
        """Execute dollar-cost averaging investment strategy."""
        add_funds_needed = False
        total_invested = sum(amounts)
        dca_per_date = total_invested / max(len(data), 1)

        for date, row in data.iterrows():
            for i, ticker in enumerate(tickers):
                if ticker not in row or pd.isna(row[ticker]):
                    continue
                price = float(row[ticker])
                if total_cash >= price:
                    shares_to_buy = dca_per_date / price
                    if shares_to_buy > 0:
                        cost = shares_to_buy * price
                        holdings[ticker] = holdings.get(ticker, 0.0) + shares_to_buy
                        total_cash -= cost
                        investment_log.append(
                            f"{date.date()}: DCA bought {shares_to_buy:.4f} shares "
                            f"of {ticker} at ${price:.2f} (cost: ${cost:.2f})"
                        )
                else:
                    add_funds_needed = True
                    add_funds_dates.append(
                        (str(date.date()), ticker, price, total_cash)
                    )

        return total_cash, add_funds_needed

    # -----------------------------------------------------------------------
    # Results Calculation
    # -----------------------------------------------------------------------

    def _calculate_results(
        self,
        data: pd.DataFrame,
        holdings: Dict[str, float],
        amounts: List[float],
        tickers: List[str],
        total_cash: float,
        investment_log: List[str],
        add_funds_needed: bool,
        add_funds_dates: List[Tuple[str, str, float, float]],
        strategy: InvestmentStrategy,
    ) -> SimulationResult:
        """Calculate portfolio metrics from simulation results."""
        final_prices = data.iloc[-1]
        total_invested = 0.0
        total_value = 0.0
        holding_results: List[HoldingResult] = []

        # Calculate per-ticker invested amount
        invested_per_ticker: Dict[str, float] = {}
        for log_entry in investment_log:
            if "Bought" in log_entry or "DCA bought" in log_entry:
                for ticker in tickers:
                    if f"shares of {ticker}" in log_entry or f"of {ticker} at" in log_entry:
                        try:
                            cost_str = log_entry.split("(cost: $")[-1].split(")")[0]
                            invested_per_ticker[ticker] = invested_per_ticker.get(ticker, 0.0) + float(cost_str)
                        except (ValueError, IndexError):
                            pass

        for ticker, shares in holdings.items():
            if ticker not in final_prices.index and ticker not in final_prices:
                continue
            price = float(final_prices[ticker]) if ticker in final_prices else 0.0
            if pd.isna(price):
                price = 0.0
            invested = invested_per_ticker.get(ticker, 0.0)
            current_value = shares * price
            total_invested += invested
            total_value += current_value

            pct_return = ((current_value - invested) / invested * 100) if invested > 0 else 0.0
            pct_allocation = (invested / total_invested * 100) if total_invested > 0 else 0.0

            holding_results.append(HoldingResult(
                ticker=ticker,
                shares=shares,
                invested=invested,
                current_price=price,
                current_value=current_value,
                absolute_return=current_value - invested,
                percent_return=pct_return,
                percent_allocation=pct_allocation,
            ))

        total_value += total_cash

        return SimulationResult(
            holdings=holding_results,
            total_invested=total_invested,
            total_value=total_value,
            remaining_cash=total_cash,
            investment_log=investment_log,
            add_funds_needed=add_funds_needed,
            add_funds_dates=add_funds_dates,
        )

    # -----------------------------------------------------------------------
    # Benchmark Comparison
    # -----------------------------------------------------------------------

    def _run_benchmark(
        self,
        data: pd.DataFrame,
        result: SimulationResult,
        strategy: InvestmentStrategy,
        total_invested: float,
    ) -> None:
        """Run benchmark comparison against SPY or other index."""
        if self.benchmark_data is None or self.benchmark_data.empty:
            logger.info("No benchmark data available, skipping comparison.")
            return

        spy_prices = self.benchmark_data.reindex(data.index, method="ffill")
        if spy_prices.empty:
            return

        # Align dates
        if spy_prices.index[0] > data.index[0]:
            data = data.loc[spy_prices.index[0]:]

        spy_shares = 0.0
        spy_cash = total_invested

        if strategy == InvestmentStrategy.SINGLE_SHOT:
            first_date = data.index[0]
            spy_price = self._safe_price(spy_prices, first_date)
            if spy_price and spy_price > 0:
                spy_shares = spy_cash / spy_price
                spy_cash -= spy_shares * spy_price
        else:
            dca_amount = total_invested / max(len(data), 1)
            for date in data.index:
                spy_price = self._safe_price(spy_prices, date)
                if spy_price and spy_price > 0:
                    shares = dca_amount / spy_price
                    spy_cash -= shares * spy_price
                    spy_shares += shares

        # Build performance comparison
        last_spy_price = self._safe_price(spy_prices, data.index[-1]) or 0.0
        spy_total_value = spy_shares * last_spy_price

        performance_data: List[Dict[str, Any]] = []
        all_tickers = [h.ticker for h in result.holdings]
        for date in data.index:
            port_value = sum(
                h.shares * self._safe_price(data, date, h.ticker)
                for h in result.holdings
                if self._safe_price(data, date, h.ticker) is not None
            )
            spy_val = spy_shares * (self._safe_price(spy_prices, date) or 0.0)
            performance_data.append({
                "date": str(date.date()),
                "portfolio": float(port_value) if port_value else None,
                "spy": float(spy_val) if spy_val else None,
            })

        result.performance_data = performance_data
        result.spy_total_value = spy_total_value
        result.spy_total_invested = total_invested
        result.spy_percent_return = (
            ((spy_total_value - total_invested) / total_invested * 100)
            if total_invested > 0 else 0.0
        )

    # -----------------------------------------------------------------------
    # Utility Methods
    # -----------------------------------------------------------------------

    def _validate_date(self, date_str: str) -> str:
        """Validate and cap investment date to MAX_HISTORY_YEARS."""
        try:
            current_year = datetime.now().year
            year = int(date_str[:4])
            if current_year - year > self.MAX_HISTORY_YEARS:
                adjusted = f"{current_year - self.MAX_HISTORY_YEARS}-01-01"
                logger.info(f"Investment date capped from {date_str} to {adjusted}")
                return adjusted
            return date_str
        except (ValueError, IndexError):
            logger.warning(f"Invalid date format: {date_str}, defaulting to 1 year ago")
            return f"{datetime.now().year - 1}-01-01"

    @staticmethod
    def _safe_price(
        data: pd.DataFrame | pd.Series,
        date: Any,
        ticker: Optional[str] = None,
    ) -> Optional[float]:
        """Safely extract a price from data, handling NaN and missing values."""
        try:
            if date not in data.index:
                return None
            val = data.loc[date, ticker] if ticker else data.loc[date]
            if isinstance(val, pd.Series):
                val = val.iloc[0]
            return None if pd.isna(val) else float(val)
        except (KeyError, IndexError, TypeError):
            return None

    @staticmethod
    def distribute_amount(
        total_amount: float,
        tickers: List[str],
        weights: Optional[Dict[str, float]] = None,
    ) -> List[float]:
        """
        Distribute investment amount across tickers.

        Args:
            total_amount: Total amount to distribute.
            tickers: List of ticker symbols.
            weights: Optional dict of {ticker: weight}. Equal weight if None.

        Returns:
            List of amounts, one per ticker.
        """
        if not weights:
            per_ticker = total_amount / len(tickers)
            return [per_ticker] * len(tickers)

        total_weight = sum(weights.get(t, 1.0) for t in tickers)
        return [
            total_amount * weights.get(t, 1.0) / total_weight
            for t in tickers
        ]


# ---------------------------------------------------------------------------
# Insight scaffolding (from ai-engineering-hub bull/bear pattern)
# ---------------------------------------------------------------------------

@dataclass
class Insight:
    """A single bull or bear insight about a stock or portfolio."""
    title: str
    description: str
    emoji: str = ""


@dataclass
class BullBearInsights:
    """Bull and bear insights for a stock or portfolio."""
    bull_insights: List[Insight] = field(default_factory=list)
    bear_insights: List[Insight] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bullInsights": [
                {"title": i.title, "description": i.description, "emoji": i.emoji}
                for i in self.bull_insights
            ],
            "bearInsights": [
                {"title": i.title, "description": i.description, "emoji": i.emoji}
                for i in self.bear_insights
            ],
        }
