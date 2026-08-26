"""
Autonomous Self-Loop Orchestrator
Implements continuous trade → evaluate → evolve → validate → redeploy cycle
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve repo root reliably regardless of CWD (qna.py sets PROJECT_ROOT,
# but this module may be imported directly by tests/cron with a different cwd).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class SelfLoopState:
    """Tracks autonomous system state"""
    last_evaluation: Optional[datetime] = None
    last_evolution: Optional[datetime] = None
    last_validation: Optional[datetime] = None
    cycle_count: int = 0
    total_trades_evaluated: int = 0
    strategies_evolved: int = 0
    strategies_validated: int = 0
    capital_deployed: float = 0.0
    current_equity: float = 0.0
    drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    is_running: bool = False
    error_count: int = 0
    last_error: Optional[str] = None


class AutonomousSelfLoopOrchestrator:
    """
    Implements the complete self-loop:
    1. Monitor live trades and PnL
    2. Evaluate strategy performance
    3. Evolve underperforming strategies
    4. Validate via walk-forward
    5. Redeploy improved strategies
    6. Adjust capital allocation
    7. Repeat continuously
    """
    
    def __init__(
        self,
        evaluation_interval_minutes: int = 30,
        evolution_interval_hours: int = 6,
        validation_interval_hours: int = 12,
        min_trades_for_evaluation: int = 10,
        max_strategies_to_evolve: int = 5,
        capital_allocation_pct: float = 0.8,
    ):
        self.evaluation_interval = timedelta(minutes=evaluation_interval_minutes)
        self.evolution_interval = timedelta(hours=evolution_interval_hours)
        self.validation_interval = timedelta(hours=validation_interval_hours)
        self.min_trades = min_trades_for_evaluation
        self.max_evolve = max_strategies_to_evolve
        self.capital_pct = capital_allocation_pct
        
        self.state = SelfLoopState()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Lazy-loaded components
        self._pnl_evaluator = None
        self._strategy_evolver = None
        self._walk_forward_analyzer = None
        self._auto_tuner = None
        self._self_aware = None
        self._council_debate = None
        self._risk_manager = None
        self._kill_switch = None
        self._execution_manager = None
        
    async def _lazy_load_components(self):
        """Load components lazily to avoid circular imports"""
        if self._pnl_evaluator is None:
            try:
                from quant_nanggroe.engine.analytics.pnl_evaluator import PnLEvaluator
                self._pnl_evaluator = PnLEvaluator()
            except Exception as e:
                logger.warning(f"PnLEvaluator unavailable: {e}")
        
        if self._strategy_evolver is None:
            try:
                from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
                self._strategy_evolver = StrategyEvolver()
            except Exception as e:
                logger.warning(f"StrategyEvolver unavailable: {e}")
        
        if self._walk_forward_analyzer is None:
            try:
                from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
                from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
                engine = BacktestEngine(BacktestConfig(
                    initial_capital=10000.0,
                    commission_rate=0.001,
                    slippage_bps=5.0,
                ))
                self._walk_forward_analyzer = WalkForwardAnalyzer(
                    engine=engine,
                    train_window=120,
                    test_window=60,
                )
            except Exception as e:
                logger.warning(f"WalkForwardAnalyzer unavailable: {e}")
        
        # AutoTuner is per-use (requires strategy_name, param_grid, data)
        # Not a singleton — created on-demand in _evolve_strategies if needed
        
        if self._self_aware is None:
            try:
                from quant_nanggroe.engine.self_aware import SelfAware, SelfState
                self._self_aware = SelfAware(state_provider=self._build_self_state)
            except Exception as e:
                logger.warning(f"SelfAware unavailable: {e}")
        
        if self._council_debate is None:
            try:
                from quant_nanggroe.agents.debate.engine import DebateEngine
                self._council_debate = DebateEngine()
            except Exception as e:
                logger.warning(f"DebateEngine unavailable: {e}")
        
        if self._risk_manager is None:
            try:
                from quant_nanggroe.engine.risk import RiskManager
                self._risk_manager = RiskManager()
            except Exception as e:
                logger.warning(f"RiskManager unavailable: {e}")
        
        if self._execution_manager is None:
            try:
                from quant_nanggroe.engine.execution import ExecutionManager
                self._execution_manager = ExecutionManager()
                from quant_nanggroe.engine.risk.kill_switch import KillSwitch, configure_kill_switch_file
                from quant_nanggroe.engine.risk.manager import RiskManager
                configure_kill_switch_file()
                if self._kill_switch is None:
                    self._kill_switch = KillSwitch()
                if self._risk_manager is None:
                    self._risk_manager = RiskManager()
                self._execution_manager.set_kill_switch(self._kill_switch)
                self._execution_manager.set_risk_manager(self._risk_manager)
            except Exception as e:
                logger.warning(f"ExecutionManager unavailable: {e}")
    
    async def start(self):
        """Start the autonomous self-loop"""
        if self._running:
            logger.warning("Self-loop already running")
            return
        
        await self._lazy_load_components()
        self._running = True
        self.state.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Autonomous self-loop started")
    
    async def stop(self):
        """Stop the autonomous self-loop"""
        self._running = False
        self.state.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Autonomous self-loop stopped")
    
    async def _run_loop(self):
        """Main self-loop execution"""
        while self._running:
            try:
                now = datetime.utcnow()
                
                # Step 1: Self-Awareness (every cycle)
                if self._self_aware:
                    await self._perform_self_awareness()
                
                # Step 2: Performance Evaluation (every N minutes)
                if (self.state.last_evaluation is None or 
                    now - self.state.last_evaluation >= self.evaluation_interval):
                    await self._evaluate_performance()
                    self.state.last_evaluation = now
                
                # Step 3: Strategy Evolution (every N hours)
                if (self.state.last_evolution is None or
                    now - self.state.last_evolution >= self.evolution_interval):
                    await self._evolve_strategies()
                    self.state.last_evolution = now
                
                # Step 4: Walk-Forward Validation (every N hours)
                if (self.state.last_validation is None or
                    now - self.state.last_validation >= self.validation_interval):
                    await self._validate_strategies()
                    self.state.last_validation = now
                
                # Step 5: Capital Reallocation (after validation)
                await self._reallocate_capital()
                
                # Step 6: Council Debate for Low-Confidence Signals
                await self._debate_low_confidence_signals()
                
                self.state.cycle_count += 1
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.state.error_count += 1
                self.state.last_error = str(e)
                logger.error(f"Self-loop error: {e}", exc_info=True)
                await asyncio.sleep(300)  # Wait 5 min on error
    
    async def _perform_self_awareness(self):
        """Self-awareness: reflect on current state"""
        try:
            if not self._self_aware:
                return
            
            # Self-reflect (uses state_provider internally)
            reflection = self._self_aware.reflect()
            logger.info(f"Self-awareness: {reflection.verdict}")
            
        except Exception as e:
            logger.debug(f"Self-awareness failed: {e}")
    
    def _build_self_state(self):
        """Build SelfState for SelfAware module"""
        from quant_nanggroe.engine.self_aware import SelfState
        return SelfState(
            equity=self.state.current_equity,
            peak_equity=max(self.state.current_equity, 10000.0),
            daily_pnl=0.0,
            total_trades=self.state.total_trades_evaluated,
            open_positions=0,
            veto_count=0,
            approval_count=0,
            losing_streak=0,
            winning_streak=0,
            last_strategy="",
            last_symbol="",
            last_run_ts=self.state.last_evaluation.timestamp() if self.state.last_evaluation else 0.0,
            strategy_last_evolved_ts=self.state.last_evolution.timestamp() if self.state.last_evolution else 0.0,
        )
    
    async def _evaluate_performance(self):
        """Evaluate recent trade performance"""
        try:
            # Get recent trades
            trades = await self._get_recent_trades()
            if len(trades) < self.min_trades:
                logger.debug(f"Only {len(trades)} trades, need {self.min_trades} for evaluation")
                return
            
            # Aggregate PnL per strategy from raw trade dicts
            strategy_pnl: Dict[str, Dict] = {}
            for trade in trades:
                sname = trade.get("strategy", trade.get("Strategy", "unknown"))
                if sname not in strategy_pnl:
                    strategy_pnl[sname] = {"equity": 0.0, "trades": 0, "wins": 0}
                pnl_raw = trade.get("pnl", trade.get("realized_pnl", 0))
                try:
                    pnl = float(pnl_raw) if pnl_raw else 0.0
                except (ValueError, TypeError):
                    pnl = 0.0
                strategy_pnl[sname]["equity"] += pnl
                strategy_pnl[sname]["trades"] += 1
                if pnl > 0:
                    strategy_pnl[sname]["wins"] += 1
            
            self.state.total_trades_evaluated += len(trades)
            self.state.current_equity = sum(s.get("equity", 0) for s in strategy_pnl.values())
            
            logger.info(f"Evaluated {len(trades)} trades across {len(strategy_pnl)} strategies")
            
        except Exception as e:
            logger.error(f"Performance evaluation failed: {e}")
    
    async def _evolve_strategies(self):
        """Evolve underperforming strategies"""
        try:
            if not self._strategy_evolver:
                return
            
            # Get strategy performance
            strategy_perf = await self._get_strategy_performance()
            
            # Sort by performance, evolve worst performers
            sorted_strats = sorted(strategy_perf.items(), key=lambda x: x[1].get("sharpe", 0))
            to_evolve = sorted_strats[:self.max_evolve]
            
            evolved_count = 0
            for strategy_name, perf in to_evolve:
                if perf.get("sharpe", 0) < 0.5:  # Only evolve if Sharpe < 0.5
                    try:
                        self._strategy_evolver.evolve(strategy_name)
                        evolved_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to evolve {strategy_name}: {e}")
            
            self.state.strategies_evolved += evolved_count
            logger.info(f"Evolved {evolved_count} strategies")
            
        except Exception as e:
            logger.error(f"Strategy evolution failed: {e}")
    
    async def _validate_strategies(self):
        """Validate evolved strategies via walk-forward"""
        try:
            if not self._walk_forward_analyzer:
                return
            
            # Get recently evolved strategies
            evolved = await self._get_recently_evolved_strategies()
            
            validated_count = 0
            for strategy_name in evolved:
                try:
                    # Run walk-forward validation
                    result = self._walk_forward_analyzer.analyze_strategy(
                        strategy_name=strategy_name,
                        symbol="BTC-USD",
                        period="2y"
                    )
                    
                    if result.get("oos_sharpe", 0) > 0:
                        validated_count += 1
                        logger.info(f"Validated {strategy_name}: OOS Sharpe {result['oos_sharpe']:.2f}")
                    else:
                        logger.warning(f"Strategy {strategy_name} failed validation")
                
                except Exception as e:
                    logger.debug(f"Validation failed for {strategy_name}: {e}")
            
            self.state.strategies_validated += validated_count
            logger.info(f"Validated {validated_count} strategies")
            
        except Exception as e:
            logger.error(f"Strategy validation failed: {e}")
    
    async def _reallocate_capital(self):
        """Reallocate capital based on performance"""
        try:
            if not self._risk_manager or not self._execution_manager:
                return
            
            # Get strategy performance
            strategy_perf = await self._get_strategy_performance()
            
            # Calculate allocation weights (performance-weighted)
            total_sharpe = sum(max(0, p.get("sharpe", 0)) for p in strategy_perf.values())
            if total_sharpe == 0:
                return
            
            allocations = {}
            for name, perf in strategy_perf.items():
                sharpe = max(0, perf.get("sharpe", 0))
                weight = (sharpe / total_sharpe) * self.capital_pct
                allocations[name] = weight
            
            # Apply allocations (track in state; ExecutionManager doesn't have set_strategy_allocations)
            self.state.capital_deployed = sum(allocations.values())
            logger.info(f"Reallocated capital across {len(allocations)} strategies: {list(allocations.keys())}")
            
        except Exception as e:
            logger.error(f"Capital reallocation failed: {e}")
    
    async def _debate_low_confidence_signals(self):
        """Use council debate for low-confidence signals"""
        try:
            if not self._council_debate:
                return
            
            # Get pending signals with low confidence
            signals = await self._get_pending_signals()
            low_conf = [s for s in signals if s.get("confidence", 1.0) < 0.6]
            
            if not low_conf:
                return
            
            # Debate each low-confidence signal
            for signal in low_conf:
                try:
                    debate_result = self._council_debate.debate(signal)
                    if debate_result.get("consensus") == "REJECT":
                        logger.info(f"Council rejected signal: {signal.get('strategy')}")
                    else:
                        logger.info(f"Council approved signal: {signal.get('strategy')}")
                except Exception as e:
                    logger.debug(f"Debate failed: {e}")
        
        except Exception as e:
            logger.debug(f"Council debate failed: {e}")
    
    async def _get_recent_trades(self) -> List[Dict]:
        """Get recent trades from paper_trades.csv and trades.csv"""
        trades: List[Dict] = []
        import csv
        from pathlib import Path
        # Read paper trades
        for csv_path in (REPO_ROOT / "data" / "paper_trades.csv", REPO_ROOT / "data" / "trades.csv"):
            if csv_path.exists():
                try:
                    with open(csv_path, "r") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            trades.append(dict(row))
                except Exception as e:
                    logger.debug(f"Failed to read {csv_path}: {e}")
        # Also check paper_state for recent fills
        state_dir = Path("paper_state")
        if state_dir.is_dir():
            for jsonl in state_dir.glob("execution_audit.jsonl"):
                try:
                    with open(jsonl, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    entry = json.loads(line)
                                    if entry.get("action") == "ORDER_SUBMITTED":
                                        trades.append(entry)
                                except json.JSONDecodeError:
                                    pass
                except Exception as e:
                    logger.debug(f"Failed to read audit log: {e}")
        return trades
    
    async def _get_strategy_performance(self) -> Dict[str, Dict]:
        """Get performance metrics per strategy from PnLEvaluator stats"""
        perf: Dict[str, Dict] = {}
        # Read from strategy_stats directory
        from pathlib import Path
        stats_dir = REPO_ROOT / "data" / "strategy_stats"
        if stats_dir.exists():
            for stat_file in stats_dir.glob("*.json"):
                try:
                    data = json.loads(stat_file.read_text())
                    strategy_name = stat_file.stem
                    perf[strategy_name] = {
                        "sharpe": float(data.get("sharpe", data.get("avg_sharpe", 0))),
                        "win_rate": float(data.get("win_rate", 0)),
                        "total_trades": int(data.get("total_trades", 0)),
                        "equity": float(data.get("equity", data.get("total_pnl", 0))),
                        "max_drawdown": float(data.get("max_drawdown", 0)),
                    }
                except Exception as e:
                    logger.debug(f"Failed to read stats for {stat_file.stem}: {e}")
        # Fallback: read from PnLEvaluator if loaded
        if self._pnl_evaluator and not perf:
            try:
                for sname, history in self._pnl_evaluator._trade_history.items():
                    if history:
                        wins = sum(1 for t in history if t.realized_pnl() > 0)
                        total = len(history)
                        perf[sname] = {
                            "sharpe": 0.0,
                            "win_rate": wins / total if total > 0 else 0.0,
                            "total_trades": total,
                            "equity": sum(t.realized_pnl() for t in history),
                            "max_drawdown": 0.0,
                        }
            except Exception:
                pass
        return perf
    
    async def _get_recently_evolved_strategies(self) -> List[str]:
        """Get list of recently evolved strategies from evolver history"""
        evolved: List[str] = []
        # Read from evolution history file
        from pathlib import Path
        history_path = REPO_ROOT / "data" / "evolution_history.json"
        if history_path.exists():
            try:
                data = json.loads(history_path.read_text())
                # Get unique strategy names from recent entries (last 24h)
                import time
                cutoff = time.time() - 86400  # 24 hours
                for entry in data:
                    if entry.get("timestamp", 0) > cutoff and entry.get("accepted", False):
                        name = entry.get("strategy_name", "")
                        if name and name not in evolved:
                            evolved.append(name)
            except Exception as e:
                logger.debug(f"Failed to read evolution history: {e}")
        # Fallback: list all registered strategies as candidates
        if not evolved:
            try:
                from quant_nanggroe.engine.strategies.registry import StrategyRegistry
                evolved = list(StrategyRegistry.list_strategies())[:10]
            except Exception:
                pass
        return evolved
    
    async def _get_pending_signals(self) -> List[Dict]:
        """Get pending trading signals from ProductionStrategyRunner.

        FIX (2026-07-28): previously hard-coded prices={sym:0.0} and
        empty market_data, which made generate_signals() skip every symbol
        (price<=0 guard) → returned []. Now we fetch REAL ticker + OHLCV
        from a live provider (CoinGecko; Binance is geo-blocked here) so
        signals are computed on live data.
        """
        signals: List[Dict] = []
        try:
            from quant_nanggroe.engine_production_bridge import ProductionStrategyRunner
            from quant_nanggroe.data.providers.coingecko_provider import CoinGeckoProvider
            from quant_nanggroe.data.providers.yahoo import YahooFinanceProvider

            runner = ProductionStrategyRunner()
            if not runner.strategies:
                return signals

            # QNA symbol -> (Yahoo symbol, CoinGecko coin_id)
            # CoinGecko gives spot price (Binance is geo-blocked here);
            # Yahoo gives reliable OHLCV history without an API key.
            symbols = {
                "BTCUSDT": ("BTC-USD", "bitcoin"),
                "ETHUSDT": ("ETH-USD", "ethereum"),
            }
            price_provider = CoinGeckoProvider()
            ohlcv_provider = YahooFinanceProvider()

            async def _fetch():
                prices: Dict[str, float] = {}
                market_data: Dict[str, List[Dict]] = {}
                for qna_sym, (yf_sym, cg_id) in symbols.items():
                    try:
                        price = await price_provider.get_price(cg_id)
                        if price and price > 0:
                            prices[qna_sym] = float(price)
                        ohlcv = await ohlcv_provider.get_ohlcv(yf_sym, TimeFrame.H1, limit=100)
                        market_data[qna_sym] = [
                            {
                                "open": c.open,
                                "high": c.high,
                                "low": c.low,
                                "close": c.close,
                                "volume": c.volume,
                                "timestamp": c.timestamp,
                            }
                            for c in ohlcv
                        ]
                    except Exception as e:
                        logger.debug(f"Price fetch failed for {qna_sym}: {e}")
                return prices, market_data

            prices, market_data = await _fetch()
            if not prices:
                logger.debug("No live prices fetched — skipping signal gen")
                return signals

            generated = runner.generate_signals(market_data, prices)
            for sig in generated:
                signals.append({
                    "strategy": sig.strategy,
                    "symbol": sig.symbol,
                    "side": sig.side,
                    "confidence": sig.confidence,
                    "price": sig.price,
                    "reason": sig.reason,
                })
        except Exception as e:
            logger.debug(f"Failed to generate signals: {e}")
        return signals
    
    def get_status(self) -> Dict[str, Any]:
        """Get current self-loop status"""
        return {
            "is_running": self.state.is_running,
            "cycle_count": self.state.cycle_count,
            "total_trades_evaluated": self.state.total_trades_evaluated,
            "strategies_evolved": self.state.strategies_evolved,
            "strategies_validated": self.state.strategies_validated,
            "capital_deployed": self.state.capital_deployed,
            "current_equity": self.state.current_equity,
            "drawdown": self.state.drawdown,
            "sharpe_ratio": self.state.sharpe_ratio,
            "last_evaluation": self.state.last_evaluation.isoformat() if self.state.last_evaluation else None,
            "last_evolution": self.state.last_evolution.isoformat() if self.state.last_evolution else None,
            "last_validation": self.state.last_validation.isoformat() if self.state.last_validation else None,
            "error_count": self.state.error_count,
            "last_error": self.state.last_error,
        }

    def get_self_awareness(self) -> Optional[Dict[str, Any]]:
        """Get self-awareness reflection in API-friendly format"""
        if not self._self_aware:
            return None
        try:
            reflection = self._self_aware.reflect()
            return {
                "assessment": reflection.verdict,
                "confidence": 1.0 - reflection.metrics.get("drawdown", 0.0),
                "recommendations": [
                    s for s in reflection.statements
                    if "should" in s.lower() or "stale" in s.lower() or "evolve" in s.lower()
                ] or reflection.statements[:2],
                "risks": reflection.anomalies,
                "statements": reflection.statements,
                "metrics": reflection.metrics,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.debug(f"Self-awareness reflection failed: {e}")
            return None