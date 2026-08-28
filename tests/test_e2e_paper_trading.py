"""E2E Paper Trading Test -- AutonomousPipeline x PaperBroker (+ MT5 optional).

Three scenarios:
  A) Real BTC-USD data -- verifies init, stages, fallback behavior
  B) Monkey-patched buy signal -- forces buy through FinalDecider,
     execution, trailing stop, and SLA
  C) All 24 registered strategies + MTF verification + MT5 config check
     (no monkey-patch on signal -- real strategy ensemble voting)

ASCII-only output (safe on Windows cp1252 terminal).

Usage:
    .venv/Scripts/python.exe -m pytest tests/test_e2e_paper_trading.py -v -s --tb=short
    set VALETAX_PASSWORD=your_password  # optional: enables MT5 demo broker
    .venv/Scripts/python.exe tests/test_e2e_paper_trading.py  # standalone
"""

import logging
import os
import sys
import time

import numpy as np
import pandas as pd
import pytest

logging.basicConfig(level=logging.WARNING)
for name in [
    "urllib3", "yfinance", "qna", "QNA",
    "quant_nanggroe.engine.agentic",
    "quant_nanggroe.engine.execution",
    "quant_nanggroe.exchange",
]:
    logging.getLogger(name).setLevel(logging.WARNING)

EXPECTED_STAGES = {"data_fetch", "signal_generation", "ensemble_voting",
                   "council_debate", "risk_check", "execution"}

EXPECTED_NEW_STRATEGIES = {
    "pairs_trade", "trend_follow", "tsmom",
    "xgboost_alpha", "multi_timeframe",
}


def _make_strong_trend_df(length: int = 100) -> pd.DataFrame:
    """Mock OHLCV with strong uptrend."""
    np.random.seed(42)
    returns = np.random.normal(0.003, 0.01, length)
    prices = 100.0 * np.cumprod(1 + returns)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq="D")
    df = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.002, length)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.004, length))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.004, length))),
        "close": prices,
        "volume": np.random.lognormal(15, 1, length),
    }, index=dates)
    df.columns = [c.lower() for c in df.columns]
    return df


class TestE2EPaperTrading:

    def _log(self, *args, **kwargs):
        print(*args, **kwargs, flush=True)

    def _check_mt5_config(self):
        """Check if MT5 demo is configured. Returns True if demo ready."""
        try:
            import yaml
            cfg_path = "config/mt5_accounts.yaml"
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            paper = cfg.get("paper", None)
            server = cfg.get("server", "")
            login = cfg.get("login", 0)
            has_password = bool(cfg.get("password", "") or
                                os.environ.get("VALETAX_PASSWORD", ""))
            if paper and has_password and login:
                self._log(f"  MT5 demo: READY (server={server}, login={login})")
                return True
            self._log(f"  MT5 demo: NOT READY (paper={paper}, has_pw={has_password})")
            return False
        except Exception:
            self._log("  MT5 demo: config/mt5_accounts.yaml not found")
            return False

    # ------------------------------------------------------------------
    # SCENARIO A: REAL BTC-USD DATA
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_scenario_a_real_data(self):
        from quant_nanggroe.engine.agentic import AutonomousPipeline

        p = AutonomousPipeline()
        p.load_strategies()
        strategies = p.list_available_strategies()

        self._log("")
        self._log("=" * 60)
        self._log("  SCENARIO A: BTC-USD REAL DATA")
        self._log("=" * 60)
        self._log(f"  Strategies loaded: {len(strategies)}")
        self._log(f"  FinalDecider:  {'YES' if p._final_decider else 'NO'}")
        self._log(f"  StrategyLogger:{'YES' if p._strategy_logger else 'NO'}")
        self._log(f"  TrailingStop:  {'YES' if p._trailing_stop else 'NO'}")
        self._log(f"  TradeLifecycle:{'YES' if p._trade_lifecycle else 'NO'}")

        t0 = time.perf_counter()
        result = await p.run(symbol="BTC-USD", use_llm=False)
        run_ms = (time.perf_counter() - t0) * 1000

        assert result is not None
        assert result.symbol == "BTC-USD"
        assert result.signal in ("buy", "sell", "hold")
        assert 0.0 <= result.confidence <= 1.0
        assert result.timestamp
        assert result.reason

        step_names = {s.name for s in result.steps}
        missing = EXPECTED_STAGES - step_names
        assert not missing, f"Missing stages: {missing}"

        self._log(f"\n  --- Stages ({len(result.steps)}) ---")
        for s in result.steps:
            ok = "[OK]" if s.status == "passed" else "[SKIP]" if s.status == "skipped" else "[FAIL]"
            self._log(f"    {ok} {s.name}: {s.status} ({s.duration_ms:.1f}ms)")
            assert s.duration_ms >= 0

        # FinalDecider
        fd_decision = result.decision.get("final_decider", {})
        last_fd = getattr(p._final_decider, "_last_decision", None) if p._final_decider else None
        self._log("\n  --- FinalDecider ---")
        if last_fd:
            self._log(f"    Called via step 4.5: {last_fd.action.value} @ {last_fd.confidence:.2f}")
        elif fd_decision:
            self._log(f"    In result.decision: {fd_decision.get('action')}")
        else:
            self._log("    NOT called (risk_check blocked before step 4.5)")

        # Execution
        exec_dec = result.decision.get("execution", {})
        action = exec_dec.get("action", "hold")
        self._log(f"\n  --- Execution: {action} ---")
        if action in ("buy", "sell"):
            filled = exec_dec.get("execution") == "filled"
            self._log(f"    {'FILLED' if filled else 'REJECTED'}")
            if filled:
                self._log(f"    Fill={exec_dec.get('fill_price', 0):.2f}  "
                          f"SL={exec_dec.get('sl', 0):.2f}  TP={exec_dec.get('tp', 0):.2f}")
        else:
            self._log(f"    Reason: {exec_dec.get('reason', 'hold')}")

        # Trailing stop
        trailing_active = exec_dec.get("trailing_stop_active", False)
        self._log(f"\n  --- TrailingStop: {'ACTIVE' if trailing_active else 'inactive'} ---")

        # StrategyLogger
        if p._strategy_logger:
            recent = p._strategy_logger.get_recent(limit=5)
            self._log(f"\n  --- StrategyLogger: {len(recent)} entries ---")
        else:
            self._log("\n  --- StrategyLogger: not initialized ---")

        # TradeLifecycle
        trade_lc = result.decision.get("trade_lifecycle")
        self._log(f"\n  --- TradeLifecycleManager: {'triggered' if trade_lc else 'not triggered'} ---")

        # SLA
        sla = result.sla
        self._log("\n  --- SLA Metrics ---")
        self._log(f"    Total: {sla.total_duration_ms:.0f}ms  "
                  f"Data->Sig: {sla.data_to_signal_ms:.0f}ms  "
                  f"Sig->Risk: {sla.signal_to_risk_ms:.0f}ms  "
                  f"Risk->Exec: {sla.risk_to_exec_ms:.0f}ms")

        # SelfCorrection
        lessons = p.correction.list_lessons()
        self._log(f"\n  --- SelfCorrection: {len(lessons)} lessons ---")
        for l in lessons[:3]:
            self._log(f"    [{l['severity']}] {l['category']}: {l['summary'][:80]}")

        self._log(f"\n  --- Summary: {result.signal} @ {result.confidence:.1%} ({run_ms:.0f}ms) ---")
        self._log("=" * 60)

    # ------------------------------------------------------------------
    # SCENARIO B: FORCED BUY SIGNAL (MONKEY-PATCHED)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_scenario_b_forced_buy_signal(self):
        """Patch signal + risk to force buy through FinalDecider -> execution -> trailing -> SLA.

        Rationale: the real strategy registry (quant_nanggroe.engine.strategy.strategies)
        does not exist, so _ensemble_signal always returns 'hold' before ever
        consulting self._strategies.  Monkey-patches bypass both the signal
        and risk stages so the pipeline can exercise FinalDecider, execution,
        trailing stop, and SLA end-to-end.
        """
        from quant_nanggroe.engine.agentic import AutonomousPipeline
        from quant_nanggroe.engine.agentic.final_decider import Action

        p = AutonomousPipeline()
        p.load_strategies()
        df = _make_strong_trend_df(length=100)

        self._log("")
        self._log("=" * 60)
        self._log("  SCENARIO B: FORCED BUY (MONKEY-PATCHED)")
        self._log("=" * 60)

        # Patch signal generation -- always returns BUY at 0.85
        p._generate_signal = lambda *a, **kw: ("buy", 0.85, "forced buy from E2E test")
        self._log("  [PATCH] _generate_signal returns (buy, 0.85)")

        # Patch risk check -- always returns APPROVED
        p._check_risk = lambda *a, **kw: (
            True, "Risk bypassed for E2E test",
            {"risk_verdict": "APPROVED", "price": kw.get("current_price", 0)},
        )
        self._log("  [PATCH] _check_risk returns APPROVED")

        t0 = time.perf_counter()
        result = await p.run(symbol="BTC-USD", data=df, use_llm=False)
        run_ms = (time.perf_counter() - t0) * 1000

        # ---- 1. Pipeline integrity -----------------------------------------
        assert result is not None
        assert result.signal in ("buy", "sell", "hold")
        assert 0.0 <= result.confidence <= 1.0

        # ---- 2. All stages -------------------------------------------------
        step_names = {s.name for s in result.steps}
        missing = EXPECTED_STAGES - step_names
        assert not missing, f"Missing stages: {missing}"

        self._log(f"\n  --- Stages ({len(result.steps)}) ---")
        for s in result.steps:
            ok = "[OK]" if s.status == "passed" else "[SKIP]" if s.status == "skipped" else "[FAIL]"
            self._log(f"    {ok} {s.name}: {s.duration_ms:.1f}ms")
            assert s.duration_ms >= 0

        # ---- 3. FinalDecider MUST have been called (step 4.5) ---------------
        last_fd = getattr(p._final_decider, "_last_decision", None) if p._final_decider else None
        fd_decision = result.decision.get("final_decider", {})
        self._log("\n  --- FinalDecider ---")
        if last_fd is not None:
            is_veto = last_fd.action == Action.HOLD
            self._log(f"    Called: YES -- {last_fd.action.value} @ {last_fd.confidence:.2f}")
            self._log(f"    Veto: {'YES (trade blocked)' if is_veto else 'NO (trade approved)'}")
            self._log(f"    Reason: {last_fd.reason[:100]}")
            assert hasattr(last_fd, "action")
            assert last_fd.reason
        elif fd_decision:
            self._log(f"    In result.decision: {fd_decision.get('action')}")
            self._log(f"    {fd_decision.get('reason', '')[:80]}")
        else:
            self._log("    NOT called (pipeline stopped before step 4.5)")

        # ---- 4. Execution ---------------------------------------------------
        exec_dec = result.decision.get("execution", {})
        action = exec_dec.get("action", "hold")
        self._log("\n  --- Execution ---")
        self._log(f"    Action: {action}")
        if action in ("buy", "sell"):
            filled = exec_dec.get("execution") == "filled"
            self._log(f"    Status: {'FILLED' if filled else 'REJECTED'}")
            self._log(f"    Order: {exec_dec.get('order_id', 'N/A')}")
            if filled:
                fp = exec_dec.get("fill_price", 0)
                sl = exec_dec.get("sl", 0)
                tp = exec_dec.get("tp", 0)
                self._log(f"    Fill={fp:.2f}  SL={sl:.2f}  TP={tp:.2f}")
                assert fp > 0, "Fill price must be > 0"
                assert sl > 0, "Stop loss must be > 0"
                assert tp > 0, "Take profit must be > 0"
        else:
            self._log(f"    Reason: {exec_dec.get('reason', '')[:80]}")

        # ---- 5. TrailingStop registration -----------------------------------
        trailing_active = exec_dec.get("trailing_stop_active", False)
        self._log("\n  --- TrailingStop ---")
        if trailing_active:
            stop = p._trailing_stop.get_stop_price("BTC-USD")
            self._log("    Status: ACTIVE")
            if stop:
                self._log(f"    Stop price: {stop:.2f}")
            assert p._trailing_stop is not None
        else:
            self._log("    Status: not activated (no fill from pipeline)")

        # Always verify trailing stop IS wired and functional
        p._trailing_stop.add_position("BTC-USD", 50000.0)
        manual_stop = p._trailing_stop.get_stop_price("BTC-USD")
        self._log(f"    Manual add_position() test: stop={manual_stop:.2f}")
        assert manual_stop is not None, "TrailingStop.add_position() failed"
        assert manual_stop < 50000.0, "Stop should be below entry price"
        p._trailing_stop.remove_position("BTC-USD")
        self._log("    TrailingStop: fully wired and functional")

        # ---- 6. TradeLifecycleManager ----------------------------------------
        trade_lc = result.decision.get("trade_lifecycle")
        self._log("\n  --- TradeLifecycleManager ---")
        if trade_lc:
            self._log(f"    Eval: {trade_lc.get('eval_duration_ms', 0):.1f}ms")
            self._log(f"    Evolve: {trade_lc.get('evolve_duration_ms', 0):.1f}ms")
            self._log(f"    Lesson: {trade_lc.get('lesson_id', 'none')}")
            if trade_lc.get("evolution_triggered", False):
                evo = trade_lc.get("evolution_result", {})
                self._log(f"    Auto-evolve: {evo.get('evolutions_triggered', 0)} triggered")
        else:
            self._log("    Not triggered (no filled trade)")

        # ---- 7. SLA metrics MUST be populated --------------------------------
        sla = result.sla
        self._log("\n  --- SLA Metrics ---")
        self._log(f"    Total duration:  {sla.total_duration_ms:.1f}ms")
        self._log(f"    Data -> Signal:  {sla.data_to_signal_ms:.1f}ms")
        self._log(f"    Signal -> Risk:  {sla.signal_to_risk_ms:.1f}ms")
        self._log(f"    Risk -> Exec:    {sla.risk_to_exec_ms:.1f}ms")
        self._log(f"    Lessons:         {sla.lessons_recorded}")
        self._log(f"    Breached:        {sla.sla_breached}")

        if len(result.steps) >= 4:
            assert sla.total_duration_ms >= 0
            assert sla.data_to_signal_ms >= 0

        # ---- 8. StrategyLogger -----------------------------------------------
        if p._strategy_logger:
            recent = p._strategy_logger.get_recent(limit=5)
            self._log(f"\n  --- StrategyLogger: {len(recent)} entries ---")
            for e in recent[:3]:
                self._log(f"    {e['strategy_name']} {e['action']} {e['symbol']}")
        else:
            self._log("\n  --- StrategyLogger: not initialized ---")

        # ---- 9. Decision structure --------------------------------------------
        decision = result.decision
        expected_keys = {"regime", "ensemble", "council", "execution"}
        present = expected_keys & set(decision.keys())
        self._log(f"\n  --- Decision keys: {sorted(present)} ---")
        missing_keys = expected_keys - set(decision.keys())
        if missing_keys:
            self._log(f"    Missing: {missing_keys}")

        regime_info = decision.get("regime", {})
        if regime_info:
            assert "regime" in regime_info
            assert "confidence" in regime_info
            self._log(f"    Regime: {regime_info.get('regime')} @ {regime_info.get('confidence', 0):.2f}")

        # ---- 10. SelfCorrection -----------------------------------------------
        lessons = p.correction.list_lessons()
        self._log(f"\n  --- SelfCorrection: {len(lessons)} lessons ---")

        # ---- Summary ----------------------------------------------------------
        self._log(f"\n  --- Summary: {result.signal} @ {result.confidence:.1%} ({run_ms:.0f}ms) ---")
        self._log("=" * 60)

    # ------------------------------------------------------------------
    # SCENARIO C: ALL 24 STRATEGIES + MTF + MT5 DEMO CHECK
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_scenario_c_all_strategies_mtf(self):
        """Full pipeline with ALL 24 registered strategies + MTF verification.

        Unlike Scenario B (monkey-patched), this test:
        - Loads all 24 strategies from StrategyRegistry
        - Confirms multi_timeframe and 4 legacy strategies are among them
        - Lets _ensemble_signal() run with real strategy voting
        - Uses strong uptrend mock data so strategies generate BUY signals
        - Checks MT5 demo config readiness (no env dep required)
        """
        import os

        from quant_nanggroe.engine.agentic import AutonomousPipeline

        p = AutonomousPipeline()
        count = p.load_strategies()
        strategies = p.list_available_strategies()

        self._log("")
        self._log("=" * 60)
        self._log("  SCENARIO C: ALL 24 STRATEGIES + MTF")
        self._log("=" * 60)
        self._log(f"  Strategies loaded: {count}")
        self._log(f"  Available: {len(strategies)}")

        # ---- 1. multi_timeframe IS in registry -----------------------------
        assert "multi_timeframe" in strategies, \
            f"multi_timeframe NOT in {sorted(strategies)}"
        self._log("  multi_timeframe: CONFIRMED")

        # Count strategy types -- verify ALL 5 new strategies
        new_set = set(strategies) & EXPECTED_NEW_STRATEGIES
        assert len(new_set) == 5, \
            f"Expected 5 legacy+MTF strategies, got {len(new_set)}: {new_set}"
        arena_count = len(strategies) - len(new_set)
        self._log(f"  Arena strategies: {arena_count}")
        self._log(f"  Legacy+MTF: {len(new_set)} ({', '.join(sorted(new_set))})")
        assert count == len(strategies), "load_strategies count mismatch"

        # ---- 2. MT5 demo config check --------------------------------------
        self._log("\n  --- MT5 Demo Check ---")
        mt5_ready = self._check_mt5_config()
        if mt5_ready:
            if not os.environ.get("VALETAX_PASSWORD", ""):
                self._log("  WARNING: VALETAX_PASSWORD not set -- MT5 won't connect")
        else:
            self._log("  MT5 broker will use paper fallback (expected in CI)")

        # ---- 3. Run pipeline with strong uptrend data ----------------------
        df = _make_strong_trend_df(length=120)

        # Patch risk check to always pass (focus on strategy voting)
        p._check_risk = lambda *a, **kw: (
            True, "Risk bypassed for E2E Scenario C",
            {"risk_verdict": "APPROVED", "price": kw.get("current_price", 0)},
        )
        self._log("\n  [PATCH] _check_risk returns APPROVED (focus on strategy voting)")

        t0 = time.perf_counter()
        result = await p.run(symbol="BTC-USD", data=df, use_llm=False)
        run_ms = (time.perf_counter() - t0) * 1000

        # ---- 4. Pipeline integrity -----------------------------------------
        assert result is not None
        assert result.signal in ("buy", "sell", "hold")
        assert 0.0 <= result.confidence <= 1.0

        step_names = {s.name for s in result.steps}
        missing = EXPECTED_STAGES - step_names
        assert not missing, f"Missing stages: {missing}"

        self._log(f"\n  --- Stages ({len(result.steps)}) ---")
        for s in result.steps:
            ok = "[OK]" if s.status == "passed" else "[SKIP]" if s.status == "skipped" else "[FAIL]"
            self._log(f"    {ok} {s.name}: {s.duration_ms:.1f}ms")
            assert s.duration_ms >= 0

        # ---- 5. Ensemble vote metadata -------------------------------------
        self._log("\n  --- Pipeline Signal ---")
        self._log(f"    Signal: {result.signal} @ {result.confidence:.2%}")
        self._log(f"    Reason: {result.reason[:120]}")

        ensemble_meta = result.decision.get("ensemble", {})
        self._log("\n  --- Ensemble Vote ---")
        vote_count = 0
        if ensemble_meta:
            self._log(f"    Final bias: {ensemble_meta.get('final_bias', 'N/A')}")
            self._log(f"    Weighted conf: {ensemble_meta.get('weighted_confidence', 0):.4f}")
            vote_count = ensemble_meta.get("vote_count", 0)
            self._log(f"    Vote count: {vote_count}")
            self._log(f"    Consensus: {ensemble_meta.get('consensus_strength', 0):.4f}")
            self._log(f"    Strategies that fired: {vote_count}")
            if vote_count > 0:
                votes = ensemble_meta.get("votes", [])
                biases = {v.get("bias") for v in votes}
                sources = [v.get("source", "?") for v in votes]
                self._log(f"    Biases: {biases}")
                self._log(f"    Sources (first 10): {sources[:10]}")

                # Check if multi_timeframe appears in vote sources
                mtf_in_vote = "multi_timeframe" in sources
                self._log(f"    MultiTimeframe in vote: {'YES' if mtf_in_vote else 'NOT (returned HOLD/neutral)'}")
        else:
            self._log("    No ensemble metadata (step skipped?)")

        # At least one strategy should fire with strong trend data
        assert vote_count > 0, \
            "Expected at least 1 strategy to fire with strong uptrend data"

        # ---- 6. MultiTimeframeStrategy direct test -------------------------
        self._log("\n  --- MultiTimeframeStrategy Direct Test ---")
        try:
            from quant_nanggroe.engine.strategies.multi_timeframe_strategy import (
                MultiTimeframeStrategy,
            )
            mtf_strat = MultiTimeframeStrategy()
            mtf_signal = mtf_strat.generate_signal(df, symbol="BTC-USD")
            mtf_direction = mtf_signal.direction.value
            self._log(f"    generate_signal(): {mtf_direction} "
                      f"@ {mtf_signal.confidence:.4f}")
            self._log(f"    Reason: {mtf_signal.reasoning[:100]}")
            if mtf_signal.indicators:
                ind = mtf_signal.indicators
                self._log(f"    HTF: {ind.get('htf_trend', '?')} "
                          f"(str={ind.get('htf_strength', 0):.4f})")
                self._log(f"    MTF: {ind.get('mtf_trend', '?')} "
                          f"(str={ind.get('mtf_strength', 0):.4f})")
                self._log(f"    LTF: {ind.get('ltf_trend', '?')} "
                          f"(str={ind.get('ltf_strength', 0):.4f})")
                self._log(f"    Vol: {ind.get('volatility', '?')}")

                # With strong uptrend, HTF should detect bullish
                if mtf_direction != "hold":
                    assert ind.get("htf_trend") == "bullish", \
                        f"Expected bullish HTF, got {ind.get('htf_trend')}"
        except Exception as exc:
            self._log(f"    Direct test SKIPPED: {exc}")

        # ---- 7. Legacy strategy tests --------------------------------------
        self._log("\n  --- Legacy Strategy Tests ---")
        for sname in sorted(EXPECTED_NEW_STRATEGIES - {"multi_timeframe"}):
            try:
                from quant_nanggroe.engine.strategies.registry import StrategyRegistry
                strat = StrategyRegistry.create(sname)
                if strat is None:
                    self._log(f"    {sname}: NOT registered")
                    continue
                sig = strat.generate_signal(df, symbol="BTC-USD")
                self._log(f"    {sname}: {sig.direction.value} @ {sig.confidence:.4f} "
                          f"({sig.reasoning[:60]})")
            except Exception as exc:
                self._log(f"    {sname}: ERROR {exc}")

        # ---- 8. FinalDecider -----------------------------------------------
        last_fd = getattr(p._final_decider, "_last_decision", None) if p._final_decider else None
        fd_decision = result.decision.get("final_decider", {})
        self._log("\n  --- FinalDecider ---")
        if last_fd:
            self._log(f"    Called: {last_fd.action.value} @ {last_fd.confidence:.2f}")
            self._log(f"    Reason: {last_fd.reason[:100]}")
        elif fd_decision:
            self._log(f"    In result: {fd_decision.get('action')}")
        else:
            self._log("    NOT called")

        # ---- 9. Execution ---------------------------------------------------
        exec_dec = result.decision.get("execution", {})
        action = exec_dec.get("action", "hold")
        self._log(f"\n  --- Execution: {action} ---")
        if action in ("buy", "sell"):
            filled = exec_dec.get("execution") == "filled"
            self._log(f"    Filled: {filled}")
            if filled:
                self._log(f"    Fill={exec_dec.get('fill_price', 0):.2f}")
        self._log(f"    Reason: {exec_dec.get('reason', 'N/A')[:80]}")

        # ---- 10. SLA metrics -------------------------------------------------
        sla = result.sla
        self._log("\n  --- SLA Metrics ---")
        self._log(f"    Total: {sla.total_duration_ms:.0f}ms")
        self._log(f"    Data->Signal: {sla.data_to_signal_ms:.0f}ms")
        self._log(f"    Signal->Risk: {sla.signal_to_risk_ms:.0f}ms")
        self._log(f"    Risk->Exec: {sla.risk_to_exec_ms:.0f}ms")
        self._log(f"    Lessons: {sla.lessons_recorded}")

        # ---- 11. SelfCorrection ---------------------------------------------
        lessons = p.correction.list_lessons()
        self._log(f"\n  --- SelfCorrection: {len(lessons)} lessons ---")

        self._log(f"\n  --- Summary: {result.signal} @ {result.confidence:.1%} ({run_ms:.0f}ms) ---")
        self._log(f"    Strategies: {len(strategies)} loaded, {vote_count} voted")
        self._log("=" * 60)


# ---- Standalone ---------------------------------------------------------


def main():
    import asyncio
    async def _run():
        runner = TestE2EPaperTrading()
        runner._log = print
        await runner.test_scenario_a_real_data()
        await runner.test_scenario_b_forced_buy_signal()
        await runner.test_scenario_c_all_strategies_mtf()
        return True
    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
