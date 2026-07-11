import numpy as np


class StressReporter:
    def __init__(self):
        self.results = []

    def add_result(self, scenario_name: str, result: dict):
        self.results.append({"scenario": scenario_name, **result})

    def summary(self) -> dict:
        if not self.results:
            return {"total_scenarios": 0, "worst_case": None, "average_loss": 0}
        losses = [r.get("total_loss", r.get("loss", 0)) for r in self.results]
        worst = self.results[int(np.argmax(losses))] if losses else None
        return {
            "total_scenarios": len(self.results),
            "worst_case": worst,
            "average_loss": float(np.mean(losses)) if losses else 0,
            "max_loss": float(np.max(losses)) if losses else 0,
        }

    def table(self) -> str:
        lines = ["Stress Test Results:", "=" * 60]
        for r in self.results:
            lines.append(f"{r['scenario']:30s} | Loss: ${r.get('total_loss', 0):,.2f} | Pct: {r.get('loss_pct', 0):.1%}")
        return "\n".join(lines)
