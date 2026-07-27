"""
QNA Auto-Aware
==============
The autonomous intelligence layer for Quant Nanggroe:
- Loads top strategies from backtester (1000+ variants → top 20)
- Detects market regime (trending/ranging/volatile/declining)
- Aggregates signals from multiple strategies (weighted by Sharpe)
- Monitors rolling performance, rotates out underperformers
- Triggers periodic backtest re-runs

Usage:
  from auto_aware import AutoAware
  aa = AutoAware(db, connector, risk)
  aa.initialize()  # Load backtest results & deploy strategies
  signals = aa.get_signals(candles)
  regime = aa.detect_regime(candles)
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

log = logging.getLogger("QNA-AutoAware")

QNA_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = QNA_DIR / "data"
DEPLOY_FILE = DATA_DIR / "deployed_strategies.json"
BACKTEST_RESULTS = DATA_DIR / "backtest_results.json"


class AutoAware:
    """Autonomous awareness layer for QNA hedge fund."""

    ROLLBACK_WINDOW = 20  # Trades to evaluate per strategy
    REGIME_WINDOW = 30  # Candles for regime detection
    MIN_STRATEGIES = 3
    MAX_STRATEGIES = 20

    def __init__(self, db=None, connector=None, risk=None):
        self.db = db
        self.connector = connector
        self.risk = risk
        self.active_strategies = []
        self.regime = "unknown"
        self.regime_history = []
        self.rolling_stats = {}
        self.last_backtest_time = 0
        self.backtest_interval = 86400  # Re-run backtest every 24h
        self.last_regime_change = 0
        self.total_cycles = 0
        self._load_strategies()

    def initialize(self, force_backtest=False):
        """Initialize: load or run backtest."""
        if force_backtest or not DEPLOY_FILE.exists():
            self._run_backtest()
        self._load_strategies()
        log.info(f"AutoAware initialized: {len(self.active_strategies)} strategies, "
                 f"regime={self.regime}")

    def _load_strategies(self):
        """Load deployed strategies from backtest results."""
        from quant_nanggroe.backtest.strategy_factory import StrategyFactory

        if not DEPLOY_FILE.exists():
            log.warning("No deployed strategies found, running backtest...")
            self._run_backtest()
            return

        data = json.loads(DEPLOY_FILE.read_text())
        deployed = data.get("strategies", [])

        if not deployed:
            log.warning("Deployed strategies list empty, running backtest...")
            self._run_backtest()
            return

        factory = StrategyFactory()
        all_variants = factory.generate()
        name_to_variant = {v.name: v for v in all_variants}

        loaded = []
        for s in deployed:
            variant = name_to_variant.get(s["name"])
            if variant:
                variant.sharpe = s.get("sharpe", 0)
                variant.weight = max(0.05, min(1.0, s.get("sharpe", 0)))
                variant.coin_id = s.get("coin_id", "bitcoin")
                loaded.append(variant)

        loaded.sort(key=lambda s: s.sharpe, reverse=True)
        self.active_strategies = loaded[:self.MAX_STRATEGIES]
        log.info(f"Loaded {len(self.active_strategies)} strategies from backtest results")

    def _run_backtest(self):
        """Run full backtest pipeline."""
        try:
            from quant_nanggroe.backtest.runner import BacktestRunner
            runner = BacktestRunner()
            runner.run_pipeline(days=365, top_n=20)
            self.last_backtest_time = time.time()
            self._load_strategies()
        except Exception as e:
            log.error(f"Backtest failed: {e}")

    def detect_regime(self, candles: List[Dict]) -> str:
        """Detect market regime using numpy-powered calculations."""
        import numpy as np
        if len(candles) < self.REGIME_WINDOW:
            return self.regime

        closes = np.array([c["close"] for c in candles[-self.REGIME_WINDOW:]])
        n = len(closes)

        returns = np.diff(closes) / closes[:-1]
        volatility = float(np.std(returns))

        x = np.arange(n, dtype=np.float64)
        slope, _ = np.polyfit(x, closes, 1)
        trend_pct = slope / float(np.mean(closes)) * 100

        direction = np.sum(np.diff(closes) > 0)
        adx_like = abs(direction) / n

        old_regime = self.regime
        if volatility > 0.035:
            self.regime = "volatile"
        elif abs(trend_pct) > 0.08 and adx_like > 0.6:
            self.regime = "trending_up" if trend_pct > 0 else "trending_down"
        elif volatility < 0.015:
            self.regime = "ranging"
        else:
            self.regime = "neutral"

        if self.regime != old_regime:
            self.last_regime_change = self.total_cycles
            log.info(f"Regime change: {old_regime} → {self.regime} "
                     f"(vol={volatility:.1%}, trend={trend_pct:.2f}%)")

        self.regime_history.append((time.time(), self.regime))
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]

        return self.regime

    def get_aggregate_signal(self, candles: List[Dict],
                             asset_symbol: str = "BTCUSDT") -> Tuple[str, float]:
        """Aggregate signals from all strategies, weighted by Sharpe.

        Returns: (signal, confidence) where signal is buy/sell/hold
        """
        if not self.active_strategies:
            return "hold", 0.0

        votes = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        total_weight = 0.0
        voting_strategies = 0

        for strategy in self.active_strategies:
            coin_id = getattr(strategy, 'coin_id', 'bitcoin')
            asset_map = {
                "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum",
                "SOLUSDT": "solana", "BNBUSDT": "binancecoin"
            }
            mapped = asset_map.get(asset_symbol, "bitcoin")
            if coin_id != mapped:
                continue

            try:
                signals = strategy.generate_signals(candles)
                if signals and len(signals) > 0:
                    latest = signals[-1]
                    weight = getattr(strategy, 'weight', 0.5)
                    if latest == 1:
                        votes["buy"] += weight
                    elif latest == -1:
                        votes["sell"] += weight
                    else:
                        votes["hold"] += weight * 0.3
                    total_weight += weight
                    voting_strategies += 1
            except Exception:
                continue

        if voting_strategies == 0 or total_weight == 0:
            return "hold", 0.0

        for k in votes:
            votes[k] /= total_weight

        if votes["buy"] > 0.5:
            return "buy", votes["buy"]
        elif votes["sell"] > 0.5:
            return "sell", votes["sell"]
        elif votes["buy"] > votes["sell"] * 1.5:
            return "buy", votes["buy"] - votes["sell"]
        elif votes["sell"] > votes["buy"] * 1.5:
            return "sell", votes["sell"] - votes["buy"]

        return "hold", max(votes["buy"], votes["sell"])

    def record_trade_result(self, strategy_name: str, pnl: float):
        """Record trade result for rolling performance tracking."""
        if strategy_name not in self.rolling_stats:
            self.rolling_stats[strategy_name] = {
                "trades": 0, "wins": 0, "losses": 0,
                "total_pnl": 0.0, "recent_pnls": []
            }

        stats = self.rolling_stats[strategy_name]
        stats["trades"] += 1
        stats["total_pnl"] += pnl
        stats["recent_pnls"].append(pnl)
        if len(stats["recent_pnls"]) > self.ROLLBACK_WINDOW:
            stats["recent_pnls"].pop(0)

        if pnl > 0:
            stats["wins"] += 1
        else:
            stats["losses"] += 1

    def rotate_strategies(self):
        """Check strategy performance and rotate underperformers."""
        to_remove = []
        for strategy in list(self.active_strategies):
            stats = self.rolling_stats.get(strategy.name, {})
            trades = stats.get("trades", 0)
            if trades >= self.ROLLBACK_WINDOW:
                recent_pnls = stats.get("recent_pnls", [])
                if recent_pnls:
                    recent_win_rate = sum(1 for p in recent_pnls if p > 0) / len(recent_pnls)
                    if recent_win_rate < 0.35:
                        log.info(f"Rotating out {strategy.name}: "
                                 f"rolling WR={recent_win_rate:.0%} below threshold")
                        to_remove.append(strategy)

        for s in to_remove:
            self.active_strategies.remove(s)

        # If too few strategies remain, re-run backtest
        if len(self.active_strategies) < self.MIN_STRATEGIES:
            log.warning(f"Only {len(self.active_strategies)} strategies left, "
                        f"re-running backtest")
            self._run_backtest()

    def should_backtest(self) -> bool:
        """Check if it's time to re-run backtest."""
        if not self.active_strategies:
            return True
        return (time.time() - self.last_backtest_time) > self.backtest_interval

    def tick(self, candles: Dict[str, List[Dict]]):
        """Called every trading cycle — auto-awareness update."""
        self.total_cycles += 1

        # Detect regime for each asset
        for symbol, sym_candles in candles.items():
            if sym_candles and len(sym_candles) >= self.REGIME_WINDOW:
                self.detect_regime(sym_candles)
                break

        # Rotate underperformers
        if self.total_cycles % 10 == 0:
            self.rotate_strategies()

        # Re-run backtest periodically
        if self.should_backtest():
            log.info("Auto-backtest triggered")
            self._run_backtest()

    def status(self) -> Dict:
        """Return status dict for dashboard."""
        strategy_stats = []
        for s in self.active_strategies[:5]:
            rs = self.rolling_stats.get(s.name, {})
            strategy_stats.append({
                "name": s.name[:40],
                "sharpe": round(getattr(s, 'sharpe', 0), 2),
                "trades": rs.get("trades", 0),
                "rolling_wr": (sum(1 for p in rs.get("recent_pnls", []) if p > 0)
                              / max(len(rs.get("recent_pnls", [])), 1)),
            })

        return {
            "regime": self.regime,
            "active_strategies": len(self.active_strategies),
            "total_cycles": self.total_cycles,
            "last_backtest": datetime.fromtimestamp(
                self.last_backtest_time).isoformat() if self.last_backtest_time else "never",
            "top_strategies": strategy_stats,
        }
