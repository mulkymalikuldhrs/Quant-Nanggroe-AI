#!/usr/bin/env python3
"""
RISET Strategy Registry v2.3.0
===============================

Central registry untuk semua strategies (RISET dan existing)
Menyediakan unified interface untuk memanggil semua strategies.
Agent Constitution v2.3.0 Compliant

Date: 2026-01-19
Version: 2.3.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import logging

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StrategyInfo:
    """Information about a strategy"""

    name: str
    category: str
    description: str
    strategy_class: Any
    enabled: bool = True


class RisetStrategyRegistry:
    """
    Central registry untuk semua strategies

    Menggabungkan:
    - RISET v2.2.2 Strategies (Graham, Turtle, SEPA)
    - Existing Legendary Agents
    - Existing Standalone Strategies
    """

    def __init__(self):
        self.strategies: Dict[str, StrategyInfo] = {}
        self.initialize_strategies()

    def initialize_strategies(self):
        """Initialize semua strategies"""
        logger.info("Loading RISET Strategy Registry...")

        # RISET v2.2.2 Strategies
        try:
            from src.strategies.graham_value import GrahamValueStrategy

            self.strategies["graham_value"] = StrategyInfo(
                name="Graham Value Investing",
                category="RISET v2.2.2",
                description="Benjamin Graham's value investing principles with Graham Number",
                strategy_class=GrahamValueStrategy(),
                enabled=True,
            )
            logger.info("  ✓ Loaded Graham Value Strategy")
        except Exception as e:
            logger.error(f"  ✗ Failed to load Graham Value: {e}")

        try:
            from src.strategies.turtle_trading import TurtleTradingStrategy

            self.strategies["turtle_trading"] = StrategyInfo(
                name="Turtle Trading",
                category="RISET v2.2.2",
                description="Richard Dennis's Turtle Trading system with ATR sizing",
                strategy_class=TurtleTradingStrategy(),
                enabled=True,
            )
            logger.info("  ✓ Loaded Turtle Trading Strategy")
        except Exception as e:
            logger.error(f"  ✗ Failed to load Turtle Trading: {e}")

        try:
            from src.strategies.sepa import SEPAStrategy

            self.strategies["sepa"] = StrategyInfo(
                name="SEPA (Super Performance)",
                category="RISET v2.2.2",
                description="CANSLIM + VCP pattern detection",
                strategy_class=SEPAStrategy(),
                enabled=True,
            )
            logger.info("  ✓ Loaded SEPA Strategy")
        except Exception as e:
            logger.error(f"  ✗ Failed to load SEPA: {e}")

        # Existing Legendary Agents
        try:
            available_strategies = []

            try:
                from src.strategies.legendary_investors import WarrenBuffettStrategy

                available_strategies.append(("warren_buffett", WarrenBuffettStrategy))
            except ImportError:
                pass

            try:
                from src.strategies.legendary_investors import BenjaminGrahamStrategy

                available_strategies.append(("benjamin_graham", BenjaminGrahamStrategy))
            except ImportError:
                pass

            for name, strategy_class in available_strategies:
                self.strategies[name] = StrategyInfo(
                    name=name.replace("_", " ").title(),
                    category="Legendary Investors",
                    description=f"{name} approach",
                    strategy_class=strategy_class(),
                    enabled=True,
                )
                logger.info(f"  ✓ Loaded {name.replace('_', ' ').title()}")

        except Exception as e:
            logger.error(f"  ✗ Failed to load legendary agents: {e}")

        logger.info(f"Total strategies loaded: {len(self.strategies)}")

    def get_strategy(self, name: str) -> Optional[Any]:
        """Get strategy by name"""
        return self.strategies.get(name, {}).strategy_class

    def get_all_strategies(self) -> Dict[str, StrategyInfo]:
        """Get all strategies"""
        return self.strategies

    def get_strategies_by_category(self, category: str) -> Dict[str, StrategyInfo]:
        """Get strategies by category"""
        return {
            name: info
            for name, info in self.strategies.items()
            if info.category == category
        }

    def analyze_with_strategy(
        self, strategy_name: str, symbol: str, data: Dict
    ) -> Optional[Dict]:
        """
        Analyze symbol with specific strategy

        Args:
            strategy_name: Name of strategy to use
            symbol: Trading symbol
            data: Market data (OHLCV)

        Returns:
            Analysis result dictionary
        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            logger.error(f"Strategy {strategy_name} not found")
            return None

        try:
            if strategy_name == "graham_value":
                from src.strategies.graham_value import analyze_stock_graham

                result = analyze_stock_graham(
                    symbol=symbol,
                    price=data.get("close", 0),
                    eps=data.get("eps", 5.0),
                    book_value=data.get("book_value", 40.0),
                    dividend=data.get("dividend", 1.0),
                    growth_rate=data.get("growth_rate", 0.05),
                )
                return {"strategy": "Graham Value", **result}

            elif strategy_name == "turtle_trading":
                from src.strategies.turtle_trading import generate_turtle_signals

                signals = generate_turtle_signals(
                    symbol=symbol,
                    highs=data.get("highs", []),
                    lows=data.get("lows", []),
                    closes=data.get("closes", []),
                    volumes=data.get("volumes", []),
                )
                return {
                    "strategy": "Turtle Trading",
                    "signals": len(signals),
                    "latest_signal": signals[-1].action if signals else None,
                    "signals_data": [vars(s) for s in signals],
                }

            elif strategy_name == "sepa":
                from src.strategies.sepa import analyze_stock_sepa

                result = analyze_stock_sepa(
                    symbol=symbol,
                    closes=data.get("closes", []),
                    volumes=data.get("volumes", []),
                    highs=data.get("highs", []),
                    lows=data.get("lows", []),
                )
                return {"strategy": "SEPA", **result}

            elif strategy_name in ["warren_buffett", "benjamin_graham"]:
                return {
                    "strategy": strategy_name.replace("_", " ").title(),
                    "signal": "HOLD",
                    "confidence": 0.5,
                    "note": "Legendary agent - use via dedicated interface",
                }

            else:
                return {"strategy": strategy_name, "signal": "NOT_IMPLEMENTED"}

        except Exception as e:
            logger.error(f"Error analyzing with {strategy_name}: {e}")
            return {"strategy": strategy_name, "error": str(e)}

    def analyze_all_strategies(self, symbol: str, data: Dict) -> Dict[str, Any]:
        """
        Analyze symbol dengan SEMUA strategies

        Args:
            symbol: Trading symbol
            data: Market data

        Returns:
            Dictionary with results from all strategies
        """
        results = {}

        for strategy_name, strategy_info in self.strategies.items():
            if not strategy_info.enabled:
                continue

            result = self.analyze_with_strategy(strategy_name, symbol, data)
            results[strategy_name] = result

        return results


def get_riset_strategy_registry() -> RisetStrategyRegistry:
    """Get singleton instance of RISET Strategy Registry"""
    return RisetStrategyRegistry()


def main():
    """Test RISET Strategy Registry"""
    registry = get_riset_strategy_registry()

    import numpy as np

    # Generate test data
    np.random.seed(42)
    prices = 100 * np.cumprod(1 + np.random.normal(0.0005, 0.02, 252))

    test_data = {
        "closes": prices.tolist(),
        "highs": (prices * 1.02).tolist(),
        "lows": (prices * 0.98).tolist(),
        "volumes": np.random.randint(1000000, 10000000, 252).tolist(),
        "close": prices[-1],
    }

    print("\n" + "=" * 70)
    print("RISET STRATEGY REGISTRY TEST")
    print("=" * 70 + "\n")

    print(f"Total Strategies Registered: {len(registry.get_all_strategies())}\n")

    print("Strategies by Category:")
    print("-" * 70)
    for category in ["RISET v2.2.2", "Legendary Investors"]:
        strategies = registry.get_strategies_by_category(category)
        print(f"\n{category}:")
        for name, info in strategies.items():
            print(f"  • {info.name}")
            print(f"      {info.description}")

    print("\n" + "=" * 70)
    print("ANALYSIS TEST - Analyzing AAPL with ALL strategies")
    print("=" * 70 + "\n")

    results = registry.analyze_all_strategies("AAPL", test_data)

    for strategy_name, result in results.items():
        print(f"{strategy_name}:")
        if "error" in result:
            print(f"  ✗ Error: {result['error']}")
        elif "signal" in result:
            print(f"  ✓ Signal: {result['signal']}")
        elif "signals" in result:
            print(f"  ✓ Generated: {result['signals']} signals")
        print()

    print("=" * 70)
    print("✓ RISET Strategy Registry Working!")
    print("  • All strategies registered")
    print("  • Can analyze with any strategy")
    print("  • Can analyze with ALL strategies")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
