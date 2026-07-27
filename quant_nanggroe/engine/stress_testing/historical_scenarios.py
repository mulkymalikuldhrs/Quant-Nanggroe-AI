from dataclasses import dataclass


@dataclass
class ScenarioDefinition:
    name: str
    description: str
    shock_vector: dict[str, float]
    date_range: tuple[str, str]

SCENARIO_LIBRARY = {
    "2008_FINANCIAL_CRISIS": ScenarioDefinition("2008 Financial Crisis", "Global financial crisis - credit crunch, bank failures", {"equities": -0.55, "credit": -0.30, "vol": 3.5}, ("2008-09-01", "2009-03-01")),
    "COVID_2020": ScenarioDefinition("COVID-19 Pandemic", "Global pandemic lockdowns", {"equities": -0.34, "vol": 4.0, "commodities": -0.20}, ("2020-02-19", "2020-03-23")),
    "2022_RATE_HIKE": ScenarioDefinition("2022 Rate Hike", "Aggressive Fed tightening", {"equities": -0.25, "bonds": -0.15, "tech": -0.40}, ("2022-01-01", "2022-10-01")),
    "1987_BLACK_MONDAY": ScenarioDefinition("1987 Black Monday", "Flash crash - portfolio insurance unwind", {"equities": -0.25, "vol": 5.0}, ("1987-10-19", "1987-10-19")),
}

class HistoricalScenarioRunner:
    def __init__(self):
        self.library = SCENARIO_LIBRARY

    def run_scenario(self, scenario_name: str, portfolio_value: float, exposures: dict[str, float]) -> dict:
        scenario = self.library.get(scenario_name)
        if not scenario:
            return {"error": f"Scenario {scenario_name} not found", "loss": 0.0}
        total_loss = 0.0
        details = {}
        for asset_class, shock in scenario.shock_vector.items():
            exposure = exposures.get(asset_class, 0.0)
            loss = exposure * abs(shock)
            total_loss += loss
            details[asset_class] = {"exposure": exposure, "shock": shock, "loss": loss}
        return {"scenario": scenario_name, "portfolio_value": portfolio_value, "total_loss": total_loss, "loss_pct": total_loss / max(portfolio_value, 1), "details": details}

    def run_all_scenarios(self, portfolio_value: float, exposures: dict[str, float]) -> list[dict]:
        return [self.run_scenario(name, portfolio_value, exposures) for name in self.library]
