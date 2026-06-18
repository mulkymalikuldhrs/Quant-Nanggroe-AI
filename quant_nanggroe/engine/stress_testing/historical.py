"""
Historical Scenario Stress Testing
Uses actual historical market events to stress test portfolios.
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

CRISIS_SCENARIOS = {
    "2008_Financial_Crisis": {
        "start": "2008-09-15",
        "end": "2009-03-09",
        "s&p_drawdown": -0.57,
        "description": "Lehman collapse, global financial crisis",
    },
    "2020_COVID_Flash": {
        "start": "2020-02-19",
        "end": "2020-03-23",
        "s&p_drawdown": -0.34,
        "description": "COVID-19 pandemic crash",
    },
    "2022_Rate_Hike": {
        "start": "2022-01-03",
        "end": "2022-10-12",
        "s&p_drawdown": -0.25,
        "description": "Fed rate hiking cycle",
    },
    "2000_DotCom": {
        "start": "2000-03-24",
        "end": "2002-10-09",
        "s&p_drawdown": -0.49,
        "description": "Dot-com bubble burst",
    },
    "1987_Black_Monday": {
        "start": "1987-10-19",
        "end": "1987-12-04",
        "s&p_drawdown": -0.33,
        "description": "Black Monday crash",
    },
}

@dataclass
class HistoricalShock:
    scenario_name: str
    shock_returns: Dict[str, float]
    shock_volatility: float
    max_drawdown: float
    recovery_days: int
    description: str = ""

@dataclass
class HistoricalScenarioResult:
    scenario: str
    portfolio_impact: float
    max_drawdown: float
    var_95: float
    var_99: float
    asset_impacts: Dict[str, float]
    shock_intensity: float
    recovery_estimate_days: int

class HistoricalScenarioAnalyzer:
    """Analyzes portfolio under historical crisis scenarios"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.scenarios = {**CRISIS_SCENARIOS, **self.config.get("custom_scenarios", {})}

    def analyze_portfolio(self, weights: Dict[str, float],
                           asset_returns: Dict[str, pd.Series]) -> List[HistoricalScenarioResult]:
        """Analyze portfolio under all historical scenarios"""
        results = []

        for scenario_name, scenario_info in self.scenarios.items():
            impact = self._compute_scenario_impact(weights, asset_returns, scenario_info)
            results.append(impact)

        return results

    def _compute_scenario_impact(self, weights: Dict[str, float],
                                    asset_returns: Dict[str, pd.Series],
                                    scenario: Dict) -> HistoricalScenarioResult:
        """Compute portfolio impact under a specific scenario"""
        impacts = {}
        portfolio_impact = 0.0

        for asset, weight in weights.items():
            if asset in asset_returns:
                returns = asset_returns[asset]
                impact = self._find_worst_period(returns, scenario)
                impacts[asset] = impact
                portfolio_impact += weight * impact

        worst_drawdown = min(impacts.values()) if impacts else 0.0
        shock_intensity = min(1.0, max(0.0, abs(portfolio_impact) / 0.5))

        return HistoricalScenarioResult(
            scenario=scenario.get("description", scenario),
            portfolio_impact=portfolio_impact,
            max_drawdown=worst_drawdown,
            var_95=np.percentile(list(impacts.values()), 5) if impacts else 0.0,
            var_99=np.percentile(list(impacts.values()), 1) if impacts else 0.0,
            asset_impacts=impacts,
            shock_intensity=shock_intensity,
            recovery_estimate_days=int(abs(portfolio_impact) * 500),
        )

    def _find_worst_period(self, returns: pd.Series, scenario: Dict) -> float:
        """Find the worst cumulative return period"""
        if len(returns) < 20:
            return float(returns.min() if len(returns) > 0 else 0.0)

        scenario_days = scenario.get("estimated_days", 60)
        cumulative = returns.rolling(window=min(scenario_days, len(returns))).sum()
        return float(cumulative.min() if len(cumulative) > 0 else 0.0)
