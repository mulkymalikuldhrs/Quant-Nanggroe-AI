"""
ENHANCED AUTONOMOUS TRADER - Integrates quanta_ai autonomous trading
Combines autonomous decision making with memory management
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class EnhancedAutonomousTrader:
    """Enhanced autonomous trader using quanta_ai components"""

    def __init__(self):
        self.autonomous_trader = None
        self.memory_manager = None
        self.orchestrator = None
        self.trading_history = []
        self.active_strategies = []
        self.initialized = False

    def initialize(self):
        """Initialize autonomous trading components"""
        try:
            from integrations.quanta_ai.autonomous import AutonomousTrader
            from integrations.quanta_ai.memory import MemoryManager
            from integrations.quanta_ai.orchestrator import Orchestrator

            self.autonomous_trader = AutonomousTrader()
            self.memory_manager = MemoryManager()
            self.orchestrator = Orchestrator()

            print("✅ Enhanced Autonomous Trader initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize autonomous trader: {e}")
            # Fallback to basic implementation
            self.autonomous_trader = None
            self.memory_manager = None
            self.orchestrator = None
            return False

    def analyze_market_conditions(self, market_data):
        """Analyze current market conditions"""
        if self.orchestrator and hasattr(self.orchestrator, "analyze_market"):
            return self.orchestrator.analyze_market(market_data)
        else:
            # Basic market analysis
            return {"trend": "sideways", "volatility": "medium", "momentum": "neutral", "risk_level": "medium"}

    def generate_autonomous_decision(self, ticker, market_data, portfolio_state):
        """Generate autonomous trading decision"""
        if self.autonomous_trader and hasattr(self.autonomous_trader, "make_decision"):
            decision = self.autonomous_trader.make_decision(ticker, market_data, portfolio_state)

            # Store in memory
            if self.memory_manager:
                self.memory_manager.store_decision(ticker, decision)

            return decision
        else:
            # Fallback decision logic
            market_analysis = self.analyze_market_conditions(market_data)

            # Simple decision based on market analysis
            if market_analysis["trend"] == "bullish" and portfolio_state.get("cash", 0) > 1000:
                decision = {"action": "buy", "quantity": min(10, int(portfolio_state.get("cash", 0) / market_data.get("price", 100))), "reasoning": "Bullish trend detected", "confidence": 0.7}
            elif market_analysis["trend"] == "bearish" and portfolio_state.get("positions", {}).get(ticker, 0) > 0:
                decision = {"action": "sell", "quantity": portfolio_state["positions"][ticker], "reasoning": "Bearish trend detected", "confidence": 0.7}
            else:
                decision = {"action": "hold", "quantity": 0, "reasoning": "Market conditions neutral", "confidence": 0.5}

            # Store decision in history
            self.trading_history.append({"ticker": ticker, "decision": decision, "timestamp": "current", "market_analysis": market_analysis})

            return decision

    def update_strategy_performance(self, ticker, pnl):
        """Update strategy performance in memory"""
        if self.memory_manager and hasattr(self.memory_manager, "update_performance"):
            self.memory_manager.update_performance(ticker, pnl)
        else:
            # Basic performance tracking
            if not hasattr(self, "performance"):
                self.performance = {}
            if ticker not in self.performance:
                self.performance[ticker] = []
            self.performance[ticker].append(pnl)

    def get_strategy_stats(self, ticker=None):
        """Get strategy performance statistics"""
        if ticker:
            history = [h for h in self.trading_history if h["ticker"] == ticker]
            return {"total_trades": len(history), "win_rate": sum(1 for h in history if h.get("pnl", 0) > 0) / max(len(history), 1), "avg_pnl": sum(h.get("pnl", 0) for h in history) / max(len(history), 1)}
        else:
            return {"total_trades": len(self.trading_history), "active_strategies": len(self.active_strategies), "memory_size": len(self.trading_history)}


# Global instance
enhanced_autonomous_trader = EnhancedAutonomousTrader()
