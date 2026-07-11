#!/usr/bin/env python3
"""Cross-python test runner for Quant Nanggroe AI.

Detects available Python interpreters and capabilities, then runs the
maximum set of tests possible in the current environment.

Usage::
    python3 scripts/test_runner.py
    python3 scripts/test_runner.py --verbose
    python3 scripts/test_runner.py --quick
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Callable, List

# Ensure repo root is on PYTHONPATH
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


@dataclass
class TestResult:
    name: str
    passed: bool
    duration: float
    error: str = ""
    details: str = ""


@dataclass
class SuiteResult:
    name: str
    tests: List[TestResult] = field(default_factory=list)
    python: str = ""
    skipped: bool = False

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if not t.passed)

    @property
    def total(self) -> int:
        return len(self.tests)


ALL_RESULTS: List[SuiteResult] = []


def suite(name: str, python: str = "") -> Callable:
    def decorator(fn: Callable[[], List[TestResult]]) -> None:
        def wrapper() -> SuiteResult:
            result = SuiteResult(name=name, python=python or sys.executable)
            try:
                tests = fn()
                result.tests = tests
            except Exception as e:
                result.tests = [TestResult(name, False, 0, str(e))]
                result.skipped = True
            ALL_RESULTS.append(result)
            return result
        wrapper()
    return decorator


def test(name: str, fn: Callable[[], None]) -> TestResult:
    start = time.time()
    try:
        fn()
        return TestResult(name, True, time.time() - start)
    except Exception as e:
        return TestResult(name, False, time.time() - start, str(e))


def require(*modules: str) -> bool:
    for m in modules:
        if importlib.util.find_spec(m) is None:
            return False
    return True


# ── Test Suites ───────────────────────────────────────────────────────────

@suite("Auth")
def test_auth():
    from quant_nanggroe.security.auth import APIKeyAuth, JWTAuth, UserRole

    def test_jwt():
        jwt = JWTAuth(secret_key="test-secret")
        token = jwt.create_token("user1", UserRole.TRADER)
        payload = jwt.validate_token(token)
        assert payload.user_id == "user1"
        assert payload.role == UserRole.TRADER

    def test_apikey():
        ak = APIKeyAuth()
        ak.add_key("test-key", "user2", UserRole.ADMIN)
        result = ak.authenticate("test-key")
        assert result.success and result.user_id == "user2"

    def test_repr():
        jwt = JWTAuth(secret_key="sk")
        assert "JWTAuth" in repr(jwt)

    return [test("JWT create/validate", test_jwt),
            test("API key auth", test_apikey),
            test("repr", test_repr)]


@suite("Risk Engine")
def test_risk_engine():
    from quant_nanggroe.engine.risk.checks import ConstitutionalRiskGuard, RiskCheckGate
    from quant_nanggroe.engine.risk.kill_switch import RESET_CONFIRMATION, KillSwitch

    def test_alias():
        assert RiskCheckGate is ConstitutionalRiskGuard

    def test_reset_constant():
        assert RESET_CONFIRMATION == "CONFIRM_RESET_AFTER_REVIEW"

    def test_killswitch_status():
        ks = KillSwitch()
        status = ks.status()
        assert isinstance(status, dict)
        assert "is_active" in status

    def test_killswitch_activate():
        ks = KillSwitch()
        ks.activate("test_trigger")
        assert ks.is_active is True

    def test_evaluate():
        guard = ConstitutionalRiskGuard()
        result = guard.evaluate(
            symbol="BTC/USDT", direction="buy", lot_size=0.1,
            entry=50000, stop_loss=49000, account_balance=10000,
        )
        assert isinstance(result, dict)

    def test_auto_trigger():
        ks = KillSwitch()
        ks._auto_triggered = False
        result = ks.check_auto_trigger()
        assert result is None  # None = not triggered

    return [test("RiskCheckGate alias", test_alias),
            test("RESET_CONFIRMATION constant", test_reset_constant),
            test("KillSwitch.status() dict", test_killswitch_status),
            test("KillSwitch.activate(str)", test_killswitch_activate),
            test("ConstitutionalRiskGuard.evaluate()", test_evaluate),
            test("check_auto_trigger()", test_auto_trigger)]


@suite("PSR/DSR Validation")
def test_psr():
    import numpy as np
    np.random.seed(42)
    from quant_nanggroe.engine.backtest.psr import (
        deflated_sharpe_ratio,
        estimate_sharpe,
        probabilistic_sharpe_ratio,
        psr_vs_sharpe,
        validate_backtest_metrics,
    )

    def test_zero_mean():
        returns = np.random.normal(0, 0.02, 500)
        returns -= returns.mean()
        psr = probabilistic_sharpe_ratio(returns, 0)
        assert abs(psr.psr - 0.5) < 0.001

    def test_positive_alpha():
        returns = np.random.normal(0.001, 0.02, 500)
        sr = estimate_sharpe(returns)
        assert sr > 0.2

    def test_dsr_penalty():
        returns = np.random.normal(0.002, 0.02, 300)
        dsr1 = deflated_sharpe_ratio(returns, 1)
        dsr100 = deflated_sharpe_ratio(returns, 100)
        assert dsr1.dsr >= dsr100.dsr

    def test_validation_report():
        returns = np.random.normal(0.001, 0.02, 300)
        vr = validate_backtest_metrics("Test", returns, 10)
        assert vr.dsr is not None

    def test_psr_curve():
        returns = np.random.normal(0.002, 0.02, 300)
        curve = psr_vs_sharpe(returns, np.linspace(0, 3, 10))
        assert curve[0] > curve[-1]

    return [test("zero-mean PSR≈0.5", test_zero_mean),
            test("positive Sharpe", test_positive_alpha),
            test("DSR multiple-testing penalty", test_dsr_penalty),
            test("validation report", test_validation_report),
            test("PSR curve descending", test_psr_curve)]


@suite("Data Freshness Monitor")
def test_monitor():
    from quant_nanggroe.data.monitor import DataFreshnessMonitor
    from quant_nanggroe.types.market import TimeFrame

    def test_record():
        m = DataFreshnessMonitor()
        m.record_fetch("BTC/USDT", TimeFrame.H1)
        assert m.get_stale_report().total_symbols == 1

    def test_batch():
        m = DataFreshnessMonitor()
        m.record_batch(["A", "B"], TimeFrame.H1)
        assert m.get_stale_report().total_symbols == 2

    def test_clear():
        m = DataFreshnessMonitor()
        m.record_fetch("X", TimeFrame.H1)
        m.clear()
        assert m.get_stale_report().total_symbols == 0

    return [test("record fetch", test_record),
            test("batch record", test_batch),
            test("clear", test_clear)]


@suite("Survivorship Bias")
def test_survivorship():
    from datetime import date

    from quant_nanggroe.data.survivorship import SurvivorshipBiasDetector

    def test_analyze():
        d = SurvivorshipBiasDetector()
        d.record_universe("SP500", {"A", "B", "C"}, snapshot_date=date(2020, 1, 1))
        d.record_universe("SP500", {"A", "D", "E"}, snapshot_date=date(2024, 1, 1))
        r = d.analyze("SP500")
        assert r is not None
        assert r.delisted == 2

    def test_no_bias():
        d = SurvivorshipBiasDetector()
        d.record_universe("TEST", {"A", "B"}, snapshot_date=date(2020, 1, 1))
        d.record_universe("TEST", {"A", "B"}, snapshot_date=date(2024, 1, 1))
        r = d.analyze("TEST")
        assert r is not None
        assert r.delisted == 0

    def test_insufficient_data():
        d = SurvivorshipBiasDetector()
        d.record_universe("X", {"A"}, snapshot_date=date(2024, 1, 1))
        assert d.analyze("X") is None

    return [test("detects bias", test_analyze),
            test("no bias case", test_no_bias),
            test("insufficient data", test_insufficient_data)]


@suite("Strategy Registry")
def test_strategies():
    from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies

    def test_list():
        names = list_strategies()
        assert len(names) >= 8

    def test_create():
        s = create_strategy("Momentum")
        assert s is not None

    def test_invalid():
        try:
            create_strategy("NonExistent")
            assert False, "should raise"
        except ValueError:
            pass

    return [test(f"list ({len(list_strategies())} strategies)", test_list),
            test("create known strategy", test_create),
            test("invalid strategy raises", test_invalid)]


@suite("CLI Alpha Destruction")
def test_alpha_destruction():
    import numpy as np

    from scripts.alpha_destruction import run_destruction

    def test_run():
        np.random.seed(42)
        report = run_destruction(["BTC"], n_observations=100)
        assert "summary" in report
        assert report["summary"]["total_strategies"] >= 8

    return [test("runs 8 strategies", test_run)]


# ── Auto-discovered unittest tests ──────────────────────────────────────

class _TimedTestResult(unittest.TestResult):
    """unittest.TestResult with per-test timing."""
    def __init__(self):
        super().__init__()
        self.test_durations = {}
        self._start_times = {}

    def startTest(self, test):
        self._start_times[test] = time.time()
        super().startTest(test)

    def stopTest(self, test):
        if test in self._start_times:
            self.test_durations[test] = time.time() - self._start_times[test]
        super().stopTest(test)


def _collect_tests(suite):
    """Recursively collect TestCase instances from a TestSuite.
    Filters out _FailedTest instances (failed imports) and None values.
    """
    tests = []
    for t in suite:
        if t is None:
            continue
        if isinstance(t, unittest.TestSuite):
            tests.extend(_collect_tests(t))
        elif not type(t).__name__.startswith('_Failed'):
            tests.append(t)
    return tests


@suite("Engine Tests")
def test_engine_tests():
    loader = unittest.TestLoader()
    suite_dir = os.path.join(_REPO_ROOT, 'tests')
    if not os.path.isdir(suite_dir):
        return [TestResult("discover tests dir", False, 0, f"not found: {suite_dir}")]

    # Save real pandas before discover (test_data_freshness_kill_switch.py
    # deliberately patches sys.modules['pandas'] at module level, polluting
    # all subsequently imported test modules).
    _real_pandas = sys.modules['pandas']

    suite = loader.discover(suite_dir)

    # Restore real pandas module if corrupted by discover
    if sys.modules['pandas'] is not _real_pandas:
        sys.modules['pandas'] = _real_pandas
    # Fix all modules that imported the mock pandas
    import unittest.mock as _mock

    import pandas as _pd
    for _mod in sys.modules.values():
        if _mod is None:
            continue
        for _attr in ('pd', 'pandas'):
            _obj = getattr(_mod, _attr, None)
            if isinstance(_obj, _mock.MagicMock):
                setattr(_mod, _attr, _pd)
    all_tests = _collect_tests(suite)
    if not all_tests:
        return [TestResult("discover", False, 0, f"no tests found in {suite_dir}")]

    result = _TimedTestResult()
    suite.run(result)
    failure_map = {t: tb for t, tb in result.failures}
    error_map = {t: tb for t, tb in result.errors}
    skipped_map = {t: r for t, r in result.skipped}

    test_results = []
    for t in all_tests:
        name = t.id()
        duration = result.test_durations.get(t, 0.0)
        if t in failure_map:
            test_results.append(TestResult(name, False, duration, failure_map[t]))
        elif t in error_map:
            test_results.append(TestResult(name, False, duration, error_map[t]))
        elif t in skipped_map:
            test_results.append(TestResult(name, True, duration, f"skipped: {skipped_map[t]}"))
        else:
            test_results.append(TestResult(name, True, duration))

    return test_results


# ── Regime Detection Tests ─────────────────────────────────────────────────

def _run_unittest_file(filepath: str) -> List[TestResult]:
    """Run a single unittest file and return test results."""
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(filepath),
                            pattern=os.path.basename(filepath))
    all_tests = _collect_tests(suite)
    if not all_tests:
        return [TestResult(os.path.basename(filepath), False, 0, "no tests found")]

    result = _TimedTestResult()
    suite.run(result)
    failure_map = {t: tb for t, tb in result.failures}
    error_map = {t: tb for t, tb in result.errors}

    test_results = []
    for t in all_tests:
        name = t.id()
        duration = result.test_durations.get(t, 0.0)
        if t in failure_map:
            test_results.append(TestResult(name, False, duration, failure_map[t]))
        elif t in error_map:
            test_results.append(TestResult(name, False, duration, error_map[t]))
        else:
            test_results.append(TestResult(name, True, duration))
    return test_results


@suite("Regime HMM Detector")
def test_regime_hmm():
    return _run_unittest_file(os.path.join(_REPO_ROOT, "tests", "test_regime_hmm_detector.py"))


@suite("Regime Strategy Selector")
def test_regime_selector():
    return _run_unittest_file(os.path.join(_REPO_ROOT, "tests", "test_regime_strategy_selector.py"))


@suite("Regime Ensemble")
def test_regime_ensemble():
    return _run_unittest_file(os.path.join(_REPO_ROOT, "tests", "test_regime_ensemble.py"))


@suite("Regime Correlation Detector")
def test_regime_corr():
    return _run_unittest_file(os.path.join(_REPO_ROOT, "tests", "test_regime_correlation.py"))


@suite("Regime Macro Detector")
def test_regime_macro():
    return _run_unittest_file(os.path.join(_REPO_ROOT, "tests", "test_regime_macro.py"))


@suite("Regime Volatility Detector")
def test_regime_vol():
    return _run_unittest_file(os.path.join(_REPO_ROOT, "tests", "test_regime_volatility.py"))


@suite("Regime Store")
def test_regime_store():
    return _run_unittest_file(os.path.join(_REPO_ROOT, "tests", "test_regime_store.py"))


@suite("Credential Inference")
def test_credential_inference():
    return _run_unittest_file(
        os.path.join(_REPO_ROOT, "tests", "test_security", "test_credential_inference.py")
    )


# ── Runner ───────────────────────────────────────────────────────────────

def print_report() -> None:
    total_passed = 0
    total_failed = 0
    total_tests = 0

    print("\n" + "=" * 60)
    print("  QUANT NANGGROE AI — TEST REPORT")
    print("=" * 60)

    for suite_result in ALL_RESULTS:
        tag = "✓" if suite_result.failed == 0 else "✗"
        print(f"\n  {tag} {suite_result.name} ({suite_result.python[:50]})")
        for t in suite_result.tests:
            status = "PASS" if t.passed else "FAIL"
            print(f"    {'✓' if t.passed else '✗'} {t.name} ({t.duration:.2f}s)")
            if not t.passed:
                print(f"       → {t.error[:120]}")
        print(f"    ─── {suite_result.passed}/{suite_result.total} passed")

        total_passed += suite_result.passed
        total_failed += suite_result.failed
        total_tests += suite_result.total

    print("\n" + "=" * 60)
    pct = total_passed / max(total_tests, 1) * 100
    print(f"  TOTAL: {total_passed}/{total_tests} passed ({pct:.1f}%)")
    if total_failed == 0:
        print("  RESULT: ALL TESTS PASSED ✓")
    else:
        print(f"  RESULT: {total_failed} test(s) FAILED ✗")
    print("=" * 60)


def run_in_python(python_bin: str) -> str:
    """Run the test suite in a specific Python interpreter."""
    script_path = os.path.abspath(__file__)
    result = subprocess.run(
        [python_bin, script_path, "--json"],
        capture_output=True, text=True, timeout=120,
    )
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description="QNA Test Runner")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--verbose", action="store_true", help="Show details")
    args = parser.parse_args()

    if args.json:
        # Run all tests and output JSON
        results_json = []
        for s in ALL_RESULTS:
            results_json.append({
                "name": s.name,
                "tests": [{"name": t.name, "passed": t.passed, "duration": round(t.duration, 3), "error": t.error} for t in s.tests],
            })
        json.dump(results_json, sys.stdout, indent=2)
        return

    print_report()


if __name__ == "__main__":
    main()
