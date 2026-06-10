"""
INTEGRATION MANAGER - Connects all integrated components
Combines quanta_ai, quant_hf, and FinceptTerminal components
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

class IntegrationManager:
    """Manages integration of all external components"""

    def __init__(self):
        self.quanta_components = {}
        self.quant_hf_components = {}
        self.fincept_components = {}
        self.initialized = False

    def initialize_integrations(self):
        """Initialize all integrated components"""
        try:
            # Import quanta_ai components (with fallback)
            try:
                from integrations.quanta_ai.orchestrator import Orchestrator
                from integrations.quanta_ai.autonomous import AutonomousTrader
                from integrations.quanta_ai.memory import MemoryManager

                self.quanta_components = {
                    'orchestrator': Orchestrator(),
                    'autonomous_trader': AutonomousTrader(),
                    'memory_manager': MemoryManager()
                }
            except ImportError:
                print("⚠️  quanta_ai components not available")
                self.quanta_components = {}

            # Import quant_hf components (with fallback)
            try:
                from integrations.quant_hf.sentiment_agent import SentimentAgent
                from integrations.quant_hf.trader_agent import TraderAgent

                self.quant_hf_components = {
                    'sentiment_agent': SentimentAgent(),
                    'trader_agent': TraderAgent()
                }
            except ImportError:
                print("⚠️  quant_hf components not available")
                self.quant_hf_components = {}

            # Import fincept components (with fallback)
            try:
                from integrations.fincept_terminal.alternateInvestment.risk_analyzer import RiskAnalyzer
                from integrations.fincept_terminal.alternateInvestment.performance_metrics import PerformanceMetrics

                self.fincept_components = {
                    'risk_analyzer': RiskAnalyzer(),
                    'performance_metrics': PerformanceMetrics()
                }
            except ImportError:
                print("⚠️  fincept_terminal components not available")
                self.fincept_components = {}

            self.initialized = True
            print("✅ All integrations initialized successfully")
            return True

        except ImportError as e:
            print(f"❌ Integration initialization failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during integration: {e}")
            return False

    def get_quanta_orchestrator(self):
        """Get quanta_ai orchestrator"""
        return self.quanta_components.get('orchestrator')

    def get_sentiment_agent(self):
        """Get quant_hf sentiment agent"""
        return self.quant_hf_components.get('sentiment_agent')

    def get_risk_analyzer(self):
        """Get fincept risk analyzer"""
        return self.fincept_components.get('risk_analyzer')

    def get_performance_metrics(self):
        """Get fincept performance metrics"""
        return self.fincept_components.get('performance_metrics')

    def get_autonomous_trader(self):
        """Get quanta_ai autonomous trader"""
        return self.quanta_components.get('autonomous_trader')

    def get_memory_manager(self):
        """Get quanta_ai memory manager"""
        return self.quanta_components.get('memory_manager')

    def get_trader_agent(self):
        """Get quant_hf trader agent"""
        return self.quant_hf_components.get('trader_agent')

# Global integration manager instance
integration_manager = IntegrationManager()

def initialize_integrations():
    """Initialize all integrations"""
    return integration_manager.initialize_integrations()

def get_integration_manager():
    """Get the global integration manager"""
    return integration_manager