# Quant Nanggroe AI - Expansion Plan v6.3.0

## 🎯 VISION: Complete Autonomous Hedge Fund with Self-Evolution

**Current State**: 95/100 - Autonomous infrastructure in place, TODO stubs need real data wiring  
**Target State**: 100/100 - Fully autonomous with real trade data, self-evolution from PnL, production monitoring

---

## 📋 PHASE 1: WIRE TODO STUBS TO REAL DATA (Priority: CRITICAL)

### 1.1 Trade Database Integration
**File**: `quant_nanggroe/engine/autonomous_self_loop.py`

**Current**: `_get_recent_trades()` returns empty list  
**Required**: Wire to real MT5 trade history

**Implementation**:
```python
async def _get_recent_trades(self) -> List[Dict]:
    """Get recent trades from MT5 + Paper broker"""
    trades = []
    
    # MT5 trades
    try:
        from quant_nanggroe.engine.execution.brokers.mt5_broker import MT5Broker
        mt5 = MT5Broker()
        if mt5.is_connected():
            history = mt5.get_deals_history(days=7)
            trades.extend(history)
    except Exception as e:
        logger.debug(f"MT5 trades unavailable: {e}")
    
    # Paper trades
    try:
        from quant_nanggroe.engine.execution.brokers.paper_broker import PaperBroker
        paper = PaperBroker()
        paper_trades = paper.get_trade_history(days=7)
        trades.extend(paper_trades)
    except Exception as e:
        logger.debug(f"Paper trades unavailable: {e}")
    
    return trades
```

**Files to Modify**:
- `quant_nanggroe/engine/execution/brokers/mt5_broker.py` - Add `get_deals_history()`
- `quant_nanggroe/engine/execution/brokers/paper_broker.py` - Add `get_trade_history()`
- `quant_nanggroe/engine/autonomous_self_loop.py` - Wire `_get_recent_trades()`

**Estimated Effort**: 2 hours

---

### 1.2 Performance Tracking Wire-Up
**File**: `quant_nanggroe/engine/autonomous_self_loop.py`

**Current**: `_get_strategy_performance()` returns empty dict  
**Required**: Calculate real per-strategy PnL from trades

**Implementation**:
```python
async def _get_strategy_performance(self) -> Dict[str, Dict]:
    """Calculate per-strategy performance from trade history"""
    trades = await self._get_recent_trades()
    
    # Group trades by strategy
    strategy_trades = {}
    for trade in trades:
        strategy = trade.get("strategy", "unknown")
        if strategy not in strategy_trades:
            strategy_trades[strategy] = []
        strategy_trades[strategy].append(trade)
    
    # Calculate metrics per strategy
    performance = {}
    for strategy, trades in strategy_trades.items():
        pnl = sum(t.get("profit", 0) for t in trades)
        win_rate = len([t for t in trades if t.get("profit", 0) > 0]) / len(trades)
        
        # Calculate Sharpe (simplified)
        returns = [t.get("profit", 0) / t.get("size", 1) for t in trades]
        sharpe = (sum(returns) / len(returns)) / (sum(r**2 for r in returns) / len(returns))**0.5 if returns else 0
        
        performance[strategy] = {
            "pnl": pnl,
            "win_rate": win_rate,
            "sharpe": sharpe,
            "trade_count": len(trades),
            "equity": 10000 + pnl,  # Starting equity + PnL
        }
    
    return performance
```

**Files to Modify**:
- `quant_nanggroe/engine/autonomous_self_loop.py` - Wire `_get_strategy_performance()`

**Estimated Effort**: 1 hour

---

### 1.3 Signal Pipeline Integration
**File**: `quant_nanggroe/engine/autonomous_self_loop.py`

**Current**: `_get_pending_signals()` returns empty list  
**Required**: Connect to strategy signal generation

**Implementation**:
```python
async def _get_pending_signals(self) -> List[Dict]:
    """Get pending signals from ProductionStrategyRunner"""
    try:
        from quant_nanggroe.engine_production_bridge import ProductionStrategyRunner
        runner = ProductionStrategyRunner()
        
        # Get signals from all strategies
        signals = []
        for strategy_name in runner.list_strategies():
            try:
                strategy = runner.create_strategy(strategy_name)
                signal = strategy.generate_signal(market_data={})  # Latest market data
                
                if signal and signal.confidence > 0:
                    signals.append({
                        "strategy": strategy_name,
                        "signal": signal.direction,
                        "confidence": signal.confidence,
                        "timestamp": signal.timestamp.isoformat(),
                    })
            except Exception as e:
                logger.debug(f"Signal generation failed for {strategy_name}: {e}")
        
        return signals
    except Exception as e:
        logger.error(f"Signal pipeline unavailable: {e}")
        return []
```

**Files to Modify**:
- `quant_nanggroe/engine/autonomous_self_loop.py` - Wire `_get_pending_signals()`

**Estimated Effort**: 1 hour

---

### 1.4 Strategy Registry Wire-Up
**File**: `quant_nanggroe/engine/autonomous_self_loop.py`

**Current**: `_get_recently_evolved_strategies()` returns empty list  
**Required**: Track evolved strategies in registry

**Implementation**:
```python
async def _get_recently_evolved_strategies(self) -> List[str]:
    """Get strategies evolved in last 24 hours"""
    try:
        from quant_nanggroe.engine.strategies.registry import StrategyRegistry
        registry = StrategyRegistry()
        
        # Check for strategies with "evolved" tag or recent registration
        evolved = []
        for name in registry.list_strategies():
            meta = registry.get_metadata(name)
            if meta and meta.get("evolved"):
                evolved_at = meta.get("evolved_at")
                if evolved_at:
                    from datetime import datetime, timedelta
                    if datetime.fromisoformat(evolved_at) > datetime.utcnow() - timedelta(hours=24):
                        evolved.append(name)
        
        return evolved
    except Exception as e:
        logger.error(f"Strategy registry unavailable: {e}")
        return []
```

**Files to Modify**:
- `quant_nanggroe/engine/strategies/registry.py` - Add `get_metadata()` method
- `quant_nanggroe/engine/strategies/strategy_evolver.py` - Tag evolved strategies
- `quant_nanggroe/engine/autonomous_self_loop.py` - Wire `_get_recently_evolved_strategies()`

**Estimated Effort**: 1.5 hours

---

## 📋 PHASE 2: FILE ORGANIZATION & CLEANUP (Priority: HIGH)

### 2.1 Strategy File Audit
**Goal**: Ensure all 78 strategies are properly organized

**Tasks**:
1. List all files in `quant_nanggroe/engine/strategies/`
2. Verify each has `@StrategyRegistry.register` decorator
3. Remove orphaned files (no decorator)
4. Ensure `__init__.py` imports all strategies
5. Check for duplicate strategy names

**Command**:
```bash
cd quant_nanggroe/engine/strategies
Get-ChildItem -Filter *.py | Where-Object { $_.Name -ne "__init__.py" } | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -notmatch "@StrategyRegistry\.register") {
        Write-Output "ORPHAN: $($_.Name)"
    }
}
```

**Estimated Effort**: 1 hour

---

### 2.2 Remove Dead Code
**Goal**: Eliminate unused modules and imports

**Targets**:
1. `quant_nanggroe/engine/strategy/strategies/` - Legacy shim (keep only `__init__.py`)
2. `archive/` - Move old files here
3. `__pycache__/` - Clean up
4. Unused imports in all Python files

**Command**:
```bash
# Find files with no imports used
ruff check quant_nanggroe/ --select F401 --fix
```

**Estimated Effort**: 2 hours

---

### 2.3 Documentation Reorganization
**Goal**: Move stale docs to `docs/archive/`

**Files to Archive**:
- Any docs referencing removed modules
- Outdated architecture diagrams
- Old API documentation
- Superseded plans

**Files to Update**:
- `README.md` - Add autonomous section
- `ARCHITECTURE.md` - Add self-loop diagram
- `AGENTS.md` - Add autonomous orchestrator instructions
- `CHANGELOG.md` - Document v6.2.0 + v6.3.0 features

**Estimated Effort**: 3 hours

---

## 📋 PHASE 3: STRATEGY EVOLUTION FROM REAL PNL (Priority: CRITICAL)

### 3.1 PnL-Based Strategy Mutation
**File**: `quant_nanggroe/engine/strategies/strategy_evolver.py`

**Current**: Mutates strategies randomly  
**Required**: Mutate based on actual PnL performance

**Implementation**:
```python
def evolve_from_pnl(self, strategy_name: str, pnl_data: Dict):
    """Evolve strategy based on real PnL data"""
    # Analyze PnL patterns
    losing_trades = [t for t in pnl_data["trades"] if t["profit"] < 0]
    
    # Identify failure patterns
    if len(losing_trades) > pnl_data["trade_count"] * 0.4:
        # High loss rate - mutate risk parameters
        self._mutate_risk_params(strategy_name)
    
    if pnl_data["sharpe"] < 0.5:
        # Low Sharpe - mutate entry/exit logic
        self._mutate_entry_exit(strategy_name)
    
    # Validate via walk-forward
    result = self._walk_forward_validate(strategy_name)
    
    if result["oos_sharpe"] > pnl_data["sharpe"]:
        # Improved - register new version
        self._register_evolved_strategy(strategy_name, result)
```

**Files to Modify**:
- `quant_nanggroe/engine/strategies/strategy_evolver.py` - Add `evolve_from_pnl()`
- `quant_nanggroe/engine/autonomous_self_loop.py` - Call `evolve_from_pnl()` in evolution step

**Estimated Effort**: 3 hours

---

### 3.2 Closed Trade Analysis
**File**: `quant_nanggroe/engine/analytics/pnl_analyzer.py` (NEW)

**Purpose**: Analyze closed trades to identify strategy weaknesses

**Implementation**:
```python
class PnLAnalyzer:
    """Analyze closed trades for strategy improvement"""
    
    def analyze_strategy(self, strategy_name: str, trades: List[Dict]) -> Dict:
        """Analyze strategy performance"""
        return {
            "win_rate": self._calc_win_rate(trades),
            "avg_win": self._calc_avg_win(trades),
            "avg_loss": self._calc_avg_loss(trades),
            "profit_factor": self._calc_profit_factor(trades),
            "max_drawdown": self._calc_max_drawdown(trades),
            "sharpe_ratio": self._calc_sharpe(trades),
            "holding_period": self._calc_avg_holding_period(trades),
            "time_of_day_performance": self._analyze_time_of_day(trades),
            "market_regime_performance": self._analyze_regime(trades),
        }
    
    def identify_weaknesses(self, analysis: Dict) -> List[str]:
        """Identify strategy weaknesses"""
        weaknesses = []
        
        if analysis["win_rate"] < 0.4:
            weaknesses.append("Low win rate - consider tightening entry criteria")
        
        if analysis["profit_factor"] < 1.5:
            weaknesses.append("Low profit factor - improve risk/reward ratio")
        
        if analysis["max_drawdown"] > 0.2:
            weaknesses.append("High drawdown - reduce position sizing")
        
        return weaknesses
```

**Files to Create**:
- `quant_nanggroe/engine/analytics/pnl_analyzer.py`

**Estimated Effort**: 2 hours

---

### 3.3 Auto-Reinvestment Logic
**File**: `quant_nanggroe/engine/execution/capital_allocator.py` (NEW)

**Purpose**: Automatically reinvest profits based on performance

**Implementation**:
```python
class CapitalAllocator:
    """Allocate capital based on strategy performance"""
    
    def allocate(self, performance: Dict[str, Dict]) -> Dict[str, float]:
        """Performance-weighted allocation"""
        total_sharpe = sum(max(0, p["sharpe"]) for p in performance.values())
        
        if total_sharpe == 0:
            # Equal allocation if no performance data
            n = len(performance)
            return {name: 1.0 / n for name in performance}
        
        # Performance-weighted
        allocations = {}
        for name, perf in performance.items():
            sharpe = max(0, perf["sharpe"])
            weight = (sharpe / total_sharpe) * 0.8  # 80% deployed, 20% reserve
            allocations[name] = weight
        
        return allocations
```

**Files to Create**:
- `quant_nanggroe/engine/execution/capital_allocator.py`

**Estimated Effort**: 1.5 hours

---

## 📋 PHASE 4: PRODUCTION MONITORING & ALERTING (Priority: HIGH)

### 4.1 Autonomous System Health Checks
**File**: `quant_nanggroe/daemons/autonomous_health.py` (NEW)

**Purpose**: Monitor autonomous system health

**Implementation**:
```python
class AutonomousHealthMonitor:
    """Monitor autonomous self-loop health"""
    
    def check_health(self) -> Dict:
        """Check system health"""
        return {
            "self_loop_running": self._check_self_loop(),
            "last_evaluation_age": self._check_evaluation_age(),
            "last_evolution_age": self._check_evolution_age(),
            "last_validation_age": self._check_validation_age(),
            "error_rate": self._check_error_rate(),
            "capital_deployed": self._check_capital(),
            "drawdown": self._check_drawdown(),
        }
    
    def alert_if_unhealthy(self, health: Dict):
        """Send alerts if system is unhealthy"""
        if not health["self_loop_running"]:
            self._send_alert("CRITICAL: Self-loop not running")
        
        if health["last_evaluation_age"] > 3600:  # 1 hour
            self._send_alert("WARNING: Evaluation stale (>1h)")
        
        if health["drawdown"] > 0.15:  # 15%
            self._send_alert("CRITICAL: Drawdown >15%")
```

**Files to Create**:
- `quant_nanggroe/daemons/autonomous_health.py`

**Estimated Effort**: 2 hours

---

### 4.2 Metrics Export (Prometheus)
**File**: `quant_nanggroe/api/middleware.py`

**Purpose**: Export autonomous metrics to Prometheus

**Implementation**:
```python
from prometheus_client import Counter, Gauge, Histogram

# Autonomous metrics
AUTONOMOUS_CYCLES = Counter("autonomous_cycles_total", "Total self-loop cycles")
AUTONOMOUS_TRADES_EVALUATED = Counter("autonomous_trades_evaluated_total", "Total trades evaluated")
AUTONOMOUS_STRATEGIES_EVOLVED = Counter("autonomous_strategies_evolved_total", "Total strategies evolved")
AUTONOMOUS_CAPITAL_DEPLOYED = Gauge("autonomous_capital_deployed", "Capital deployed (fraction)")
AUTONOMOUS_EQUITY = Gauge("autonomous_equity", "Current equity")
AUTONOMOUS_DRAWDOWN = Gauge("autonomous_drawdown", "Current drawdown")
AUTONOMOUS_SHARPE = Gauge("autonomous_sharpe_ratio", "Current Sharpe ratio")
```

**Files to Modify**:
- `quant_nanggroe/api/middleware.py` - Add autonomous metrics
- `quant_nanggroe/engine/autonomous_self_loop.py` - Update metrics

**Estimated Effort**: 1.5 hours

---

### 4.3 Telegram Alerts
**File**: `quant_nanggroe/agents/tools/telegram_alerter.py`

**Purpose**: Send autonomous system alerts via Telegram

**Implementation**:
```python
class AutonomousAlerter:
    """Send alerts for autonomous system events"""
    
    def alert_cycle_complete(self, cycle_count: int):
        """Alert when cycle completes"""
        if cycle_count % 10 == 0:  # Every 10 cycles
            self._send_telegram(f"✅ Autonomous cycle #{cycle_count} completed")
    
    def alert_strategy_evolved(self, strategy_name: str, old_sharpe: float, new_sharpe: float):
        """Alert when strategy evolves"""
        self._send_telegram(
            f"🧬 Strategy evolved: {strategy_name}\n"
            f"Old Sharpe: {old_sharpe:.2f} → New Sharpe: {new_sharpe:.2f}"
        )
    
    def alert_drawdown_warning(self, drawdown: float):
        """Alert on high drawdown"""
        if drawdown > 0.10:
            self._send_telegram(f"⚠️ Drawdown warning: {drawdown*100:.1f}%")
```

**Files to Modify**:
- `quant_nanggroe/agents/tools/telegram_alerter.py` - Add autonomous alerts
- `quant_nanggroe/engine/autonomous_self_loop.py` - Call alerter

**Estimated Effort**: 1 hour

---

## 📋 PHASE 5: TESTING & VALIDATION (Priority: CRITICAL)

### 5.1 Unit Tests for Autonomous Orchestrator
**File**: `tests/test_autonomous_self_loop.py` (NEW)

**Tests**:
- Test self-loop start/stop
- Test performance evaluation
- Test strategy evolution
- Test walk-forward validation
- Test capital reallocation
- Test council debate
- Test error recovery

**Estimated Effort**: 3 hours

---

### 5.2 Integration Tests
**File**: `tests/test_autonomous_integration.py` (NEW)

**Tests**:
- Test full self-loop cycle
- Test trade database integration
- Test signal pipeline integration
- Test strategy registry integration
- Test API endpoints

**Estimated Effort**: 4 hours

---

### 5.3 End-to-End Test
**File**: `tests/test_autonomous_e2e.py` (NEW)

**Tests**:
- Start autonomous loop
- Wait for 3 cycles
- Verify metrics updated
- Verify strategies evolved
- Verify capital reallocated
- Stop autonomous loop

**Estimated Effort**: 2 hours

---

## 📋 PHASE 6: DOCUMENTATION UPDATES (Priority: MEDIUM)

### 6.1 Update README.md
**Section to Add**: "Autonomous Hedge Fund Features"

**Content**:
- Self-awareness explanation
- Self-loop flow diagram
- Council debate description
- Strategy evolution process
- Dashboard screenshots

**Estimated Effort**: 1 hour

---

### 6.2 Update ARCHITECTURE.md
**Section to Add**: "Autonomous Self-Loop Architecture"

**Content**:
- Orchestrator diagram
- Component interactions
- Data flow
- API endpoints

**Estimated Effort**: 1 hour

---

### 6.3 Update AGENTS.md
**Section to Add**: "Autonomous Orchestrator Instructions"

**Content**:
- How to start/stop autonomous loop
- How to monitor status
- How to trigger manual operations
- Troubleshooting guide

**Estimated Effort**: 1 hour

---

### 6.4 Update CHANGELOG.md
**Entries to Add**:
- v6.2.0: Autonomous self-loop orchestrator
- v6.2.0: Self-awareness module
- v6.2.0: Council debate integration
- v6.2.0: Dashboard autonomous page
- v6.3.0: Real trade database wiring
- v6.3.0: PnL-based strategy evolution
- v6.3.0: Production monitoring

**Estimated Effort**: 0.5 hours

---

## 📊 TIMELINE & PRIORITIES

### **Week 1: Critical Wiring (Phase 1)**
- Day 1: Trade database integration (2h)
- Day 2: Performance tracking (1h) + Signal pipeline (1h)
- Day 3: Strategy registry wire-up (1.5h)
- **Total**: 5.5 hours

### **Week 2: File Organization (Phase 2)**
- Day 1: Strategy file audit (1h) + Dead code removal (2h)
- Day 2: Documentation reorganization (3h)
- **Total**: 6 hours

### **Week 3: Strategy Evolution (Phase 3)**
- Day 1: PnL-based mutation (3h)
- Day 2: Closed trade analysis (2h)
- Day 3: Auto-reinvestment (1.5h)
- **Total**: 6.5 hours

### **Week 4: Monitoring (Phase 4)**
- Day 1: Health checks (2h)
- Day 2: Prometheus metrics (1.5h)
- Day 3: Telegram alerts (1h)
- **Total**: 4.5 hours

### **Week 5: Testing (Phase 5)**
- Day 1: Unit tests (3h)
- Day 2: Integration tests (4h)
- Day 3: E2E tests (2h)
- **Total**: 9 hours

### **Week 6: Documentation (Phase 6)**
- Day 1: README (1h) + ARCHITECTURE (1h)
- Day 2: AGENTS (1h) + CHANGELOG (0.5h)
- **Total**: 3.5 hours

---

## 🎯 SUCCESS CRITERIA

### **Phase 1 Success**:
- [ ] `_get_recent_trades()` returns real MT5/Paper trades
- [ ] `_get_strategy_performance()` calculates real PnL
- [ ] `_get_pending_signals()` returns real signals
- [ ] `_get_recently_evolved_strategies()` tracks evolved strategies

### **Phase 2 Success**:
- [ ] All 78 strategies verified and organized
- [ ] No orphaned files
- [ ] Dead code removed
- [ ] Documentation reorganized

### **Phase 3 Success**:
- [ ] Strategies evolve based on real PnL
- [ ] Closed trade analysis identifies weaknesses
- [ ] Auto-reinvestment allocates capital correctly

### **Phase 4 Success**:
- [ ] Health checks detect issues
- [ ] Prometheus metrics exported
- [ ] Telegram alerts sent for critical events

### **Phase 5 Success**:
- [ ] Unit tests pass (90%+ coverage)
- [ ] Integration tests pass
- [ ] E2E test passes (3 cycles)

### **Phase 6 Success**:
- [ ] README updated
- [ ] ARCHITECTURE updated
- [ ] AGENTS updated
- [ ] CHANGELOG updated

---

## 🚀 FINAL GOAL: 100/100 AUTONOMOUS

**After completing all phases**:
- ✅ Real trade data flowing
- ✅ Real performance tracking
- ✅ Real signal generation
- ✅ Real strategy evolution
- ✅ Real capital allocation
- ✅ Real monitoring & alerting
- ✅ Real testing & validation
- ✅ Real documentation

**Result**: **100/100 - FULLY AUTONOMOUS HEDGE FUND** 🚀

---

## 📝 NEXT STEPS

1. **Start Phase 1** - Wire TODO stubs to real data (5.5 hours)
2. **Validate Phase 1** - Run tests, verify data flow
3. **Proceed to Phase 2** - File organization (6 hours)
4. **Continue through all phases** - 35 hours total
5. **Final validation** - E2E test, production deployment

**Estimated Total Effort**: 35 hours (1 week full-time)

**Status**: Ready to execute
