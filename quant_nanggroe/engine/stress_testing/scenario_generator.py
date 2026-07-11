from dataclasses import dataclass


@dataclass
class SyntheticScenario:
    name: str
    description: str
    shocks: dict[str, float]
    probability: float

class ScenarioGenerator:
    def __init__(self):
        self.scenarios = []

    def add_rate_shock(self, name: str, rate_change: float, equity_impact: float = -0.02) -> SyntheticScenario:
        return SyntheticScenario(name, f"Rate shock: {rate_change:+.1%}", {"rates": rate_change, "equities": equity_impact}, 0.1)

    def add_equity_crash(self, name: str, crash_size: float = -0.20) -> SyntheticScenario:
        return SyntheticScenario(name, f"Equity crash: {crash_size:+.1%}", {"equities": crash_size, "vol": 0.5}, 0.05)

    def generate_standard_set(self) -> list[SyntheticScenario]:
        return [
            self.add_rate_shock("RATE_HIKE_50BP", 0.005, -0.03),
            self.add_rate_shock("RATE_CUT_25BP", -0.0025, 0.02),
            self.add_equity_crash("CRASH_10PCT", -0.10),
            self.add_equity_crash("CRASH_20PCT", -0.20),
            SyntheticScenario("VOL_SPIKE", "Volatility spike +3x", {"vol": 3.0, "equities": -0.05}, 0.1),
            SyntheticScenario("FX_DEVALUATION", "Currency devaluation 10%", {"fx": -0.10, "equities": -0.03}, 0.05),
        ]
