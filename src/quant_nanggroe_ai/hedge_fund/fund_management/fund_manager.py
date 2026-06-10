"""
Hedge Fund Management System
Multi-account portfolio management, allocation, and risk control.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AllocationStrategy(Enum):
    """Fund allocation strategies"""

    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    VOLATILITY_TARGET = "volatility_target"
    BLACK_LITTERMAN = "black_litterman"
    MOMENTUM_WEIGHTED = "momentum_weighted"


class AccountType(Enum):
    """Account types in fund"""

    MASTER = "master"
    FEEDER = "feeder"
    INSTITUTIONAL = "institutional"
    RETAIL = "retail"


@dataclass
class FundAccount:
    """Individual fund account"""

    account_id: str
    account_type: AccountType
    broker: str
    balance: float
    equity: float
    allocated_capital: float
    current_exposure: float
    performance: Dict[str, float]
    risk_limit: Dict[str, float]
    is_active: bool = True


@dataclass
class FundPosition:
    """Fund-level position"""

    ticker: str
    total_quantity: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    allocation_by_account: Dict[str, float]  # {account_id: quantity}
    risk_metrics: Dict[str, float]


@dataclass
class FundAllocation:
    """Capital allocation result"""

    account: str
    ticker: str
    allocated_capital: float
    quantity: float
    allocation_pct: float
    strategy: AllocationStrategy


@dataclass
class FundPerformance:
    """Fund performance metrics"""

    total_aum: float  # Assets Under Management
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    win_rate: float
    profit_factor: float
    avg_hold_time: timedelta
    monthly_returns: Dict[str, float]
    performance_by_account: Dict[str, Dict]
    top_performers: List[Tuple[str, float]]
    worst_performers: List[Tuple[str, float]]


class HedgeFundManager:
    """
    Complete hedge fund management system.

    Features:
    - Multi-account management
    - Capital allocation
    - Risk management at fund level
    - Performance attribution
    - Rebalancing
    """

    def __init__(self, fund_name: str, total_capital: float = 10000000, default_risk_limit: float = 0.02, max_position_size: float = 0.10, max_sector_exposure: float = 0.30, max_correlation: float = 0.70):  # 2% per trade  # 10% max per position  # 30% max sector  # 70% max correlation
        """
        Initialize fund manager.

        Args:
            fund_name: Name of the fund
            total_capital: Total capital to manage
            default_risk_limit: Default risk per trade (2%)
            max_position_size: Maximum position size (10%)
            max_sector_exposure: Maximum sector exposure (30%)
            max_correlation: Maximum correlation threshold
        """
        self.fund_name = fund_name
        self.total_capital = total_capital
        self.default_risk_limit = default_risk_limit
        self.max_position_size = max_position_size
        self.max_sector_exposure = max_sector_exposure
        self.max_correlation = max_correlation

        self.accounts: Dict[str, FundAccount] = {}
        self.positions: Dict[str, FundPosition] = {}
        self.performance_history: List[Dict] = []

        self.allocation_strategy = AllocationStrategy.EQUAL_WEIGHT

    def add_account(self, account: FundAccount):
        """Add a trading account to the fund."""
        self.accounts[account.account_id] = account
        logger.info(f"Added account: {account.account_id} ({account.account_type.value})")

    def remove_account(self, account_id: str):
        """Remove an account from the fund."""
        if account_id in self.accounts:
            self.accounts[account_id].is_active = False
            logger.info(f"Removed account: {account_id}")

    def allocate_capital(self, tickers: List[str], target_returns: Dict[str, float] = None, strategy: AllocationStrategy = None) -> List[FundAllocation]:
        """
        Allocate capital across accounts and tickers.

        Args:
            tickers: List of tickers to allocate
            target_returns: Target return per ticker
            strategy: Allocation strategy to use

        Returns:
            List of FundAllocation results
        """
        strategy = strategy or self.allocation_strategy
        active_accounts = [a for a in self.accounts.values() if a.is_active]

        if not active_accounts:
            raise ValueError("No active accounts")

        # Calculate allocation
        if strategy == AllocationStrategy.EQUAL_WEIGHT:
            return self._equal_weight_allocation(tickers, active_accounts)
        elif strategy == AllocationStrategy.RISK_PARITY:
            return self._risk_parity_allocation(tickers, active_accounts)
        elif strategy == AllocationStrategy.VOLATILITY_TARGET:
            return self._volatility_target_allocation(tickers, active_accounts)
        elif strategy == AllocationStrategy.MOMENTUM_WEIGHTED:
            return self._momentum_weighted_allocation(tickers, active_accounts)
        else:
            return self._equal_weight_allocation(tickers, active_accounts)

    def _equal_weight_allocation(self, tickers: List[str], accounts: List[FundAccount]) -> List[FundAllocation]:
        """Equal weight allocation."""
        allocations = []
        capital_per_ticker = self.total_capital / len(tickers)
        capital_per_account = capital_per_ticker / len(accounts)

        for ticker in tickers:
            for account in accounts:
                allocations.append(FundAllocation(account=account.account_id, ticker=ticker, allocated_capital=capital_per_account, quantity=capital_per_account / 100, allocation_pct=1.0 / len(tickers) / len(accounts), strategy=AllocationStrategy.EQUAL_WEIGHT))  # Assuming $100 price

        return allocations

    def _risk_parity_allocation(self, tickers: List[str], accounts: List[FundAccount]) -> List[FundAllocation]:
        """Risk parity allocation based on volatility."""
        # Simplified - use equal for now
        return self._equal_weight_allocation(tickers, accounts)

    def _volatility_target_allocation(self, tickers: List[str], accounts: List[FundAccount]) -> List[FundAllocation]:
        """Volatility targeting allocation."""
        # Simplified - target 10% annualized vol
        target_vol = 0.10
        allocations = []

        for ticker in tickers:
            # Assume 30% annualized vol
            estimated_vol = 0.30
            weight = target_vol / estimated_vol
            weight = min(weight, self.max_position_size)

            for account in accounts:
                capital = self.total_capital / len(tickers)
                allocated_capital = capital * weight

                allocations.append(FundAllocation(account=account.account_id, ticker=ticker, allocated_capital=allocated_capital, quantity=allocated_capital / 100, allocation_pct=weight, strategy=AllocationStrategy.VOLATILITY_TARGET))

        return allocations

    def _momentum_weighted_allocation(self, tickers: List[str], accounts: List[FundAccount]) -> List[FundAllocation]:
        """Momentum-based allocation."""
        # Simplified - use equal for now
        return self._equal_weight_allocation(tickers, accounts)

    def calculate_position_size(self, ticker: str, entry_price: float, stop_loss: float, confidence: float = 1.0, account_id: str = None) -> Tuple[float, float]:
        """
        Calculate position size based on risk management.

        Returns:
            (position_size, risk_amount)
        """
        # Determine available capital
        if account_id and account_id in self.accounts:
            account = self.accounts[account_id]
            available_capital = account.allocated_capital * (1 - account.current_exposure)
        else:
            available_capital = self.total_capital

        # Calculate risk-based size
        risk_per_trade = self.default_risk_limit * available_capital
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share > 0:
            risk_based_size = risk_per_trade / risk_per_share * entry_price
        else:
            risk_based_size = available_capital

        # Apply max position limit
        max_size = self.max_position_size * available_capital
        position_size = min(risk_based_size, max_size)

        # Adjust for confidence
        position_size *= confidence

        return position_size, risk_per_trade

    def validate_trade(self, ticker: str, quantity: float, price: float, account_id: str = None) -> Tuple[bool, str]:
        """
        Validate if a trade is within risk limits.

        Returns:
            (is_valid, reason)
        """
        # Check total position size
        position_value = quantity * price
        position_pct = position_value / self.total_capital

        if position_pct > self.max_position_size:
            return False, f"Position size {position_pct:.1%} exceeds max {self.max_position_size:.1%}"

        # Check current exposure
        current_exposure = sum(p.unrealized_pnl for p in self.positions.values()) / self.total_capital

        if abs(current_exposure) > 0.5:  # 50% max exposure
            return False, f"Current exposure {current_exposure:.1%} too high"

        # Check account limits
        if account_id and account_id in self.accounts:
            account = self.accounts[account_id]
            account_exposure = position_value / account.allocated_capital

            for limit_name, limit_value in account.risk_limit.items():
                if limit_name == "max_position" and account_exposure > limit_value:
                    return False, f"Account {account_id} position {account_exposure:.1%} exceeds limit"

        return True, "Trade validated"

    def update_positions(self, positions: Dict[str, Dict[str, Any]]):
        """
        Update fund positions from broker data.

        Args:
            positions: Dict of {ticker: position_data}
        """
        for ticker, data in positions.items():
            current_price = data.get("current_price", 0)

            if ticker in self.positions:
                pos = self.positions[ticker]
                pos.current_price = current_price
                pos.unrealized_pnl = (current_price - pos.avg_entry_price) * pos.total_quantity
            else:
                self.positions[ticker] = FundPosition(ticker=ticker, total_quantity=data.get("quantity", 0), avg_entry_price=data.get("entry_price", 0), current_price=current_price, unrealized_pnl=0, allocation_by_account=data.get("allocations", {}), risk_metrics={})

    def get_fund_exposure(self) -> Dict[str, float]:
        """Get current fund exposure breakdown."""
        total_long = 0
        total_short = 0
        by_sector = {}

        for ticker, position in self.positions.items():
            value = position.total_quantity * position.current_price

            if value > 0:
                total_long += value
            else:
                total_short += abs(value)

        return {"total_long": total_long, "total_short": total_short, "net_exposure": total_long - total_short, "gross_exposure": total_long + total_short, "net_exposure_pct": (total_long - total_short) / self.total_capital, "gross_exposure_pct": (total_long + total_short) / self.total_capital}

    def calculate_performance(self, returns: pd.DataFrame = None) -> FundPerformance:
        """
        Calculate comprehensive fund performance.

        Args:
            returns: DataFrame of account returns (optional)

        Returns:
            FundPerformance metrics
        """
        # Calculate AUM
        total_aum = sum(a.equity for a in self.accounts.values())

        # Calculate returns
        if returns is not None and len(returns) > 0:
            total_return = returns.sum().sum()
            total_return_pct = (1 + total_return / total_aum) - 1

            # Volatility
            volatility = returns.std().mean() * np.sqrt(252)

            # Sharpe ratio
            mean_return = returns.mean().mean() * 252
            sharpe = mean_return / volatility if volatility > 0 else 0

            # Sortino ratio
            negative_returns = returns[returns < 0]
            downside_vol = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 1e-10
            sortino = mean_return / downside_vol if downside_vol > 0 else 0

            # Max drawdown
            cumulative = (1 + returns).cumprod()
            peak = cumulative.expanding().max()
            drawdown = (cumulative - peak) / peak
            max_drawdown = abs(drawdown.min().min())

            # Win rate
            positive_returns = returns[returns > 0]
            win_rate = len(positive_returns) / len(returns[returns != 0]) if len(returns[returns != 0]) > 0 else 0

            # Profit factor
            gross_profit = positive_returns.sum().sum()
            gross_loss = abs(returns[returns < 0].sum().sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        else:
            total_return = 0
            total_return_pct = 0
            volatility = 0
            sharpe = 0
            sortino = 0
            max_drawdown = 0
            win_rate = 0
            profit_factor = 0

        # Performance by account
        performance_by_account = {}
        for acc_id, account in self.accounts.items():
            performance_by_account[acc_id] = account.performance

        # Top/Worst performers
        sorted_perf = sorted([(k, v.get("total_return", 0)) for k, v in performance_by_account.items()], key=lambda x: x[1], reverse=True)
        top_performers = sorted_perf[:3]
        worst_performers = sorted_perf[-3:][::-1]

        return FundPerformance(
            total_aum=total_aum, total_return=total_return, total_return_pct=total_return_pct, sharpe_ratio=sharpe, sortino_ratio=sortino, max_drawdown=max_drawdown, volatility=volatility, win_rate=win_rate, profit_factor=profit_factor, avg_hold_time=timedelta(days=5), monthly_returns={}, performance_by_account=performance_by_account, top_performers=top_performers, worst_performers=worst_performers  # Placeholder
        )

    def rebalance(self, allocations: List[FundAllocation] = None):
        """
        Rebalance fund to target allocations.

        Args:
            allocations: Target allocations (auto-calculated if None)
        """
        if allocations is None:
            allocations = self.allocate_capital(list(self.positions.keys()))

        # Calculate rebalancing trades
        for allocation in allocations:
            account = self.accounts.get(allocation.account)
            if not account:
                continue

            current_value = account.allocated_capital * (1 - account.current_exposure)
            target_value = allocation.allocated_capital

            if abs(current_value - target_value) / target_value > 0.05:  # 5% threshold
                logger.info(f"Rebalancing {allocation.account}: {allocation.ticker}")
                # Would generate rebalancing trades here

    def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report."""
        exposure = self.get_fund_exposure()

        # VaR calculation (simplified)
        if self.positions:
            returns = pd.DataFrame([{"return": p.unrealized_pnl / (p.total_quantity * p.current_price + 1)} for p in self.positions.values()])
            var_95 = returns.quantile(0.05)["return"] if len(returns) > 0 else 0
        else:
            var_95 = 0

        return {
            "timestamp": datetime.now().isoformat(),
            "fund_name": self.fund_name,
            "total_aum": sum(a.equity for a in self.accounts.values()),
            "exposure": exposure,
            "var_95_daily": var_95,
            "var_95_portfolio": var_95 * self.total_capital,
            "num_positions": len(self.positions),
            "num_accounts": len([a for a in self.accounts.values() if a.is_active]),
            "largest_position": max([(ticker, pos.total_quantity * pos.current_price) for ticker, pos in self.positions.items()], key=lambda x: x[1], default=("", 0)),
            "risk_limits": {"max_position_size": self.max_position_size, "max_sector_exposure": self.max_sector_exposure, "max_correlation": self.max_correlation, "default_risk_per_trade": self.default_risk_limit},
        }


class AutoExecutionEngine:
    """
    AI-driven automated execution engine.

    Features:
    - Signal processing
    - Order management
    - Risk validation
    - Multi-broker execution
    - Performance monitoring
    """

    def __init__(self, fund_manager: HedgeFundManager):
        """
        Initialize execution engine.

        Args:
            fund_manager: HedgeFundManager instance
        """
        self.fund_manager = fund_manager
        self.brokers: Dict[str, Any] = {}
        self.execution_queue: List[Dict] = []
        self.execution_history: List[Dict] = []
        self.signal_callbacks: List[Callable] = []

    def register_broker(self, name: str, broker: Any):
        """Register a broker for execution."""
        self.brokers[name] = broker
        logger.info(f"Registered broker: {name}")

    def register_signal_callback(self, callback: Callable):
        """Register callback for signal processing."""
        self.signal_callbacks.append(callback)

    async def process_signal(self, signal: Dict, account_id: str = None, validate: bool = True) -> Dict:
        """
        Process a trading signal.

        Args:
            signal: Signal dict with action, ticker, confidence, etc.
            account_id: Specific account (None = auto-allocate)
            validate: Whether to validate against risk limits

        Returns:
            Execution result
        """
        ticker = signal.get("ticker")
        action = signal.get("action", "").upper()
        confidence = signal.get("confidence", 0.5)
        strategy = signal.get("strategy", "unknown")

        if action not in ["BUY", "SELL"]:
            return {"status": "rejected", "reason": "Invalid action"}

        # Get current price
        price = signal.get("price", 100)  # Would fetch from broker

        # Calculate position size
        stop_loss = signal.get("stop_loss", price * 0.98 if action == "BUY" else price * 1.02)
        quantity, risk = self.fund_manager.calculate_position_size(ticker, price, stop_loss, confidence, account_id)

        if quantity <= 0:
            return {"status": "rejected", "reason": "Position size too small"}

        # Validate trade
        if validate:
            is_valid, reason = self.fund_manager.validate_trade(ticker, quantity, price, account_id)
            if not is_valid:
                return {"status": "rejected", "reason": reason}

        # Execute
        result = await self._execute_trade(ticker=ticker, action=action, quantity=quantity, price=price, stop_loss=stop_loss, take_profit=signal.get("take_profit"), account_id=account_id, confidence=confidence, strategy=strategy)

        return result

    async def _execute_trade(self, ticker: str, action: str, quantity: float, price: float, stop_loss: float, take_profit: float, account_id: str, confidence: float, strategy: str) -> Dict:
        """Execute trade on registered brokers."""
        results = {}

        # Determine execution accounts
        if account_id:
            accounts_to_use = [account_id]
        else:
            accounts_to_use = [acc for acc in self.fund_manager.accounts if self.fund_manager.accounts[acc].is_active]

        # Execute on each broker
        for broker_name in accounts_to_use:
            broker = self.brokers.get(broker_name)
            if not broker:
                continue

            try:
                order = await broker.place_trade(ticker=ticker, side=action, quantity=quantity / len(accounts_to_use), stop_loss=stop_loss, take_profit=take_profit)

                results[broker_name] = {"status": "executed", "order_id": order.broker_order_id, "quantity": order.quantity, "price": order.filled_price}

                self.execution_history.append({"timestamp": datetime.now().isoformat(), "ticker": ticker, "action": action, "quantity": quantity, "broker": broker_name, "order_id": order.broker_order_id, "confidence": confidence, "strategy": strategy})

            except Exception as e:
                results[broker_name] = {"status": "failed", "error": str(e)}
                logger.error(f"Execution failed for {broker_name}: {e}")

        return {"status": "completed" if results else "no_brokers", "results": results, "ticker": ticker, "action": action, "quantity": quantity, "total_executed": sum(1 for r in results.values() if r.get("status") == "executed")}

    async def close_all_positions(self) -> Dict[str, bool]:
        """Close all positions across all brokers."""
        results = {}

        for broker_name, broker in self.brokers.items():
            try:
                success = await broker.close_all_positions()
                results[broker_name] = success
            except Exception as e:
                logger.error(f"Close all failed for {broker_name}: {e}")
                results[broker_name] = False

        return results


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_fund_manager():
        # Create fund manager
        fund = HedgeFundManager(fund_name="AI Hedge Fund", total_capital=10000000, default_risk_limit=0.02, max_position_size=0.10)

        # Add accounts
        fund.add_account(FundAccount(account_id="ACC001", account_type=AccountType.MASTER, broker="MT5_Primary", balance=5000000, equity=5000000, allocated_capital=5000000, current_exposure=0, performance={}, risk_limit={"max_position": 0.20}))

        fund.add_account(FundAccount(account_id="ACC002", account_type=AccountType.FEEDER, broker="MT5_Secondary", balance=5000000, equity=5000000, allocated_capital=5000000, current_exposure=0, performance={}, risk_limit={"max_position": 0.20}))

        print("Hedge Fund Manager Test")
        print("=" * 50)
        print(f"Fund: {fund.fund_name}")
        print(f"Total AUM: ${fund.total_capital:,.0f}")
        print(f"Accounts: {len(fund.accounts)}")

        # Test allocation
        allocations = fund.allocate_capital(["AAPL", "GOOG", "MSFT"])
        print(f"\nAllocations created: {len(allocations)}")

        # Test position sizing
        size, risk = fund.calculate_position_size("AAPL", 150, 145)
        print(f"\nPosition sizing (AAPL @ $150, SL $145):")
        print(f"  Position size: ${size:,.0f}")
        print(f"  Risk amount: ${risk:,.0f}")

        # Test risk validation
        is_valid, reason = fund.validate_trade("AAPL", 1000, 150)
        print(f"\nTrade validation:")
        print(f"  Valid: {is_valid}")
        print(f"  Reason: {reason}")

        # Test exposure
        fund.positions["AAPL"] = FundPosition(ticker="AAPL", total_quantity=1000, avg_entry_price=145, current_price=150, unrealized_pnl=5000, allocation_by_account={}, risk_metrics={})
        exposure = fund.get_fund_exposure()
        print(f"\nFund exposure:")
        print(f"  Total Long: ${exposure['total_long']:,.0f}")
        print(f"  Total Short: ${exposure['total_short']:,.0f}")
        print(f"  Net Exposure: {exposure['net_exposure_pct']:.1%}")

        # Test performance calculation
        perf = fund.calculate_performance()
        print(f"\nPerformance:")
        print(f"  Total AUM: ${perf.total_aum:,.0f}")
        print(f"  Win Rate: {perf.win_rate:.1%}")

    asyncio.run(test_fund_manager())
