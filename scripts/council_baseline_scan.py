"""Council follow-up #2: alpha-vs-beta. Run buy&hold through the SAME WF engine
used by scan4 so its OOS Sharpe is directly comparable to the 8 Tier-A strategies.

If BuyHold OOS Sharpe ≈ a strategy's, that strategy's "edge" is just crypto drift.
Inline class — keep it out of the package (ponytail: deletion > addition).
Shadow only, no capital. Reuses BacktestEngine + WalkForwardAnalyzer verbatim.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

from quant_nanggroe.engine.backtest.engine import BacktestEngine
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from quant_nanggroe.types.signals import Signal, SignalType


class BuyHoldStrategy:  # ponytail: constant-long baseline; mirror real Signal fields
    name = "BuyHoldBaseline"

    def required_columns(self):
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self):
        return 1

    def generate_signal(self, data: pd.DataFrame):
        return Signal(
            symbol=self.name, signal_type=SignalType.BUY, confidence=0.99,
            source_agent=self.name, source_strategy=self.name,
            reasoning="buy&hold baseline",
        )


ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]


def main():
    eng = BacktestEngine()
    ana = WalkForwardAnalyzer(engine=eng, train_window=300, test_window=200,
                              purge_gap=5, embargo=2, mode="rolling")
    out = {}
    for sym in ASSETS:
        try:
            px = yf.download(sym, period="2y", interval="1h",
                             auto_adjust=True, progress=False)
            px = px[["Open", "High", "Low", "Close", "Volume"]]
            px.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in px.columns]
            res = ana.analyze_strategy(px, BuyHoldStrategy)
            agg = res["aggregate"]
            out[sym] = {
                "windows": res["n_folds"],
                "total_oos_trades": agg.get("total_oos_trades", 0),
                "under_sampled": agg.get("under_sampled", True),
                "avg_oos_sharpe": round(agg.get("avg_oos_sharpe", 0.0), 4),
                "degradation_pass_rate": round(res.get("degradation_stats", {}).get("pass_rate", 0.0), 3),
            }
        except Exception as e:
            out[sym] = {"error": repr(e)}
        print(f"BuyHold {sym}: {out[sym]}", flush=True)
    Path("data/baseline_expectancy.json").write_text(json.dumps(out, indent=2))
    print("WROTE data/baseline_expectancy.json")


if __name__ == "__main__":
    main()
