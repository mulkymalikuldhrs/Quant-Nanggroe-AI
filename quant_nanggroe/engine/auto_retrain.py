"""Auto-Retrain Orchestrator — closed-loop parameter freshness.

Closes the loop that was previously MANUAL (scripts/run_param_tuning.py):
fetch fresh broker bars → Bayesian-tune admitted strategies around their
current params → validate on out-of-sample folds → persist ONLY on
measurable improvement → flag decaying strategies.

Safety contract (fail-closed):
- New params are persisted ONLY when holdout score beats the incumbent
  baseline by IMPROVEMENT_MARGIN and is positive. Otherwise old params stay.
- Writes are atomic (tmp + os.replace).
- Strategies without numeric params or failing generation are SKIPPED,
  never crash the trading loop.
- Runs in a background thread; QNA_RETRAIN_INTERVAL_HOURS=0 disables.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("QNA.AutoRetrain")

TUNING_PATH = Path("data/tuning_results.json")
REPORT_PATH = Path("data/retrain_report.json")

# Persist only when strictly better than incumbent by this margin
IMPROVEMENT_MARGIN = 0.05
# Folds used for out-of-sample validation of one param set
VALIDATION_FOLDS = 4


class AutoRetrainer:
    """Scheduled Bayesian retraining with holdout validation gates."""

    def __init__(
        self,
        fetcher: Callable[[str, str], Any],
        symbols: List[str],
        n_trials: int = 12,
        interval_hours: float | None = None,
    ) -> None:
        """
        Args:
            fetcher: async-free callable (symbol, timeframe) -> OHLCV DataFrame.
                     Injected so tests can fake it and live wiring can reuse
                     the pipeline's real MT5 path.
            symbols: symbols to keep fresh.
            n_trials: Bayesian trials per strategy per cycle.
            interval_hours: background cadence. None reads env
                            QNA_RETRAIN_INTERVAL_HOURS (default 12; 0 = off).
        """
        self._fetcher = fetcher
        self._symbols = list(symbols)
        self._n_trials = max(4, int(n_trials))
        if interval_hours is None:
            try:
                interval_hours = float(os.environ.get("QNA_RETRAIN_INTERVAL_HOURS", "12"))
            except ValueError:
                interval_hours = 12.0
        self.interval_hours = float(interval_hours)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.last_summary: Dict[str, Any] = {}

    # ── Parameter space discovery ─────────────────────────────────────

    @staticmethod
    def _numeric_param_space(strat: Any) -> Dict[str, tuple[float, float]]:
        """Tunable space = current numeric params ±50% (bounded below)."""
        space: Dict[str, tuple[float, float]] = {}
        params = getattr(getattr(strat, "_parameters", None), "params", {}) or {}
        for key, val in params.items():
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                continue
            v = float(val)
            lo, hi = v * 0.5, v * 1.5
            if v > 0:
                lo = max(lo, 1e-4)
            if hi - lo < 1e-6:
                continue
            space[key] = (lo, hi)
        return space

    # ── Evaluation ────────────────────────────────────────────────────

    def _evaluate(self, strategy_name: str, params: Dict[str, float], df: Any) -> float:
        """Fold-validated directional score (mini-Sharpe across folds).

        Signal generated on the first half of each fold, scored on the
        second half — no lookahead. Uniform across every strategy output
        shape (single signal or per-bar series).
        """
        import pandas as pd

        from quant_nanggroe.engine.strategies.registry import StrategyRegistry

        strat = StrategyRegistry.create(strategy_name)
        if strat is None:
            return float("-inf")
        try:
            for k, v in params.items():
                strat._parameters.set(k, v)
        except Exception:
            return float("-inf")

        n = len(df)
        fold_len = n // VALIDATION_FOLDS
        if fold_len < 20:
            return float("-inf")

        pnls: List[float] = []
        for i in range(VALIDATION_FOLDS):
            seg = df.iloc[i * fold_len:(i + 1) * fold_len]
            half = len(seg) // 2
            if half < 10:
                continue
            try:
                result = strat.generate_signal(seg.iloc[:half])
                sig, conf, _reason = _extract_signal(result)
            except Exception:
                return float("-inf")  # broken under these params → hard reject
            entry = float(seg["close"].iloc[half - 1])
            exit_ = float(seg["close"].iloc[-1])
            if entry <= 0:
                continue
            fwd = exit_ / entry - 1.0
            if sig == "buy":
                pnls.append(fwd)
            elif sig == "sell":
                pnls.append(-fwd)
            else:
                pnls.append(0.0)

        if not pnls:
            return float("-inf")
        mean = sum(pnls) / len(pnls)
        var = sum((p - mean) ** 2 for p in pnls) / len(pnls)
        std = var ** 0.5
        if std < 1e-9:
            # all-hold or degenerate → neutral-negative so it can't win
            return -0.001 if mean == 0 else mean * 100.0
        return mean / std * (len(pnls) ** 0.5)  # annualization-ish scaling

    # ── Persistence ───────────────────────────────────────────────────

    @staticmethod
    def _load_tuning() -> Dict[str, Any]:
        try:
            return json.loads(TUNING_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _save_tuning(data: Dict[str, Any]) -> None:
        TUNING_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = TUNING_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, TUNING_PATH)

    @staticmethod
    def _write_report(report: Dict[str, Any]) -> None:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = REPORT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, REPORT_PATH)

    # ── Core cycle ────────────────────────────────────────────────────

    def run_once(self) -> Dict[str, Any]:
        """One full retrain pass over all symbols × admitted strategies."""
        started = time.monotonic()
        summary: Dict[str, Any] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "symbols": {}, "updated": 0, "skipped": 0, "errors": 0,
        }

        try:
            from quant_nanggroe.engine.strategy_allocation import (
                allocation_map, _lookup_asset, best_params_for,
            )
            from quant_nanggroe.engine.strategies.registry import StrategyRegistry
            from quant_nanggroe.engine.backtest.hyperopt import BayesianOptimizer
        except ImportError as exc:
            summary["errors"] += 1
            summary["fatal"] = str(exc)
            return summary

        allocation = allocation_map()
        if not allocation:
            summary["note"] = "no CPCV allocation evidence — nothing to retrain"
            return summary

        for symbol in self._symbols:
            asset = _lookup_asset(symbol)
            strategies = allocation.get(asset, []) if asset else []
            sym_result: Dict[str, Any] = {}
            df = None
            for name in strategies:
                try:
                    if df is None:
                        df = self._safe_fetch(symbol)
                    if df is None or len(df) < VALIDATION_FOLDS * 20:
                        sym_result[name] = {"status": "no_data"}
                        summary["skipped"] += 1
                        continue

                    probe = StrategyRegistry.create(name)
                    if probe is None:
                        sym_result[name] = {"status": "not_registered"}
                        summary["skipped"] += 1
                        continue
                    space = self._numeric_param_space(probe)
                    if not space:
                        sym_result[name] = {"status": "no_tunable_params"}
                        summary["skipped"] += 1
                        continue

                    current = best_params_for(name, symbol) or {}
                    baseline_score = self._evaluate(name, current, df)

                    opt = BayesianOptimizer(
                        param_space=space, n_trials=self._n_trials,
                    )
                    result = opt.optimize(lambda p: self._evaluate(name, p, df))
                    candidate = result.get("best_params") or {}
                    cand_score = float(result.get("best_score", float("-inf")))

                    improved = (
                        cand_score > 0
                        and cand_score > baseline_score + IMPROVEMENT_MARGIN
                    )
                    if improved:
                        tuning = self._load_tuning()
                        tuning.setdefault(name, {}).setdefault(asset, {})
                        tuning[name][asset] = {
                            "best_params": candidate,
                            "improved": True,
                            "score": round(cand_score, 6),
                            "baseline_score": round(baseline_score, 6),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "source": "auto_retrain",
                        }
                        self._save_tuning(tuning)
                        summary["updated"] += 1
                        sym_result[name] = {
                            "status": "updated",
                            "score": round(cand_score, 6),
                            "baseline": round(baseline_score, 6),
                        }
                    else:
                        sym_result[name] = {
                            "status": "kept_current",
                            "score": round(cand_score, 6),
                            "baseline": round(baseline_score, 6),
                        }
                except Exception as exc:
                    logger.warning("retrain %s/%s failed: %s", symbol, name, exc)
                    sym_result[name] = {"status": "error", "error": str(exc)}
                    summary["errors"] += 1
            summary["symbols"][symbol] = sym_result

        summary["duration_s"] = round(time.monotonic() - started, 1)
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        self.last_summary = summary
        self._append_report(summary)
        return summary

    def _safe_fetch(self, symbol: str) -> Any:
        try:
            return self._fetcher(symbol, "H1")
        except Exception as exc:
            logger.warning("retrain fetch failed %s: %s", symbol, exc)
            return None

    def _append_report(self, summary: Dict[str, Any]) -> None:
        """Append-only decay ledger: keeps last 50 runs per strategy."""
        try:
            history: Dict[str, List[Dict[str, Any]]] = {}
            if REPORT_PATH.exists():
                prev = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
                # NOTE: file holds {"history": ..., "stale_strategies": ...};
                # reloading it wholesale previously corrupted the structure
                # (top-level keys got treated as strategy entries).
                history = prev.get("history", {}) or {}
            for symbol, res in summary.get("symbols", {}).items():
                for name, info in res.items():
                    if isinstance(info, dict) and "baseline" in info:
                        key = f"{name}:{symbol}"
                        hist = history.setdefault(key, [])
                        if not isinstance(hist, list):
                            hist = []
                        hist.append({
                            "at": summary["finished_at"],
                            "baseline": info.get("baseline"),
                            "candidate": info.get("score"),
                            "status": info.get("status"),
                        })
                        history[key] = hist[-50:]
            stale = [
                k for k, h in history.items()
                if isinstance(h, list) and len(h) >= 3 and all(
                    (entry.get("baseline") is not None and entry["baseline"] < 0)
                    for entry in h[-3:]
                )
            ]
            self._write_report({"history": history, "stale_strategies": stale})
        except Exception as exc:
            logger.debug("retrain report write failed: %s", exc)

    # ── Background loop ───────────────────────────────────────────────

    def start(self) -> bool:
        """Start the background retrain thread. Returns False if disabled."""
        if self.interval_hours <= 0:
            logger.info("auto-retrain disabled (interval<=0)")
            return False

        def _loop():
            # First pass after a grace period so the trading loop boots first.
            if self._stop_event.wait(300):
                return
            while not self._stop_event.is_set():
                try:
                    s = self.run_once()
                    logger.info(
                        "auto-retrain done: updated=%d skipped=%d errors=%d (%.0fs)",
                        s.get("updated", 0), s.get("skipped", 0),
                        s.get("errors", 0), s.get("duration_s", 0),
                    )
                except Exception as exc:
                    logger.error("auto-retrain cycle crashed: %s", exc)
                self._stop_event.wait(self.interval_hours * 3600)

        self._thread = threading.Thread(target=_loop, daemon=True, name="qna-auto-retrain")
        self._thread.start()
        logger.info("auto-retrain scheduled every %.1fh", self.interval_hours)
        return True

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None


def _extract_signal(result: Any) -> tuple[str, float, str]:
    """Mirror of AutonomousPipeline._extract_signal (import-free copy to
    avoid pulling the whole agentic module into the retrain thread)."""
    if result is None:
        return "hold", 0.0, "No signal"
    if hasattr(result, "signal_type"):
        sig = result.signal_type.value
        conf = getattr(result, "confidence", 0.5)
        return sig, min(float(conf), 1.0), getattr(result, "reasoning", "") or sig
    import pandas as pd
    if isinstance(result, pd.Series) and len(result) > 0:
        last = result.iloc[-1]
        sig = "buy" if last > 0 else "sell" if last < 0 else "hold"
        return sig, min(abs(float(last)), 1.0), f"{last:.4f}"
    return "hold", 0.0, f"Unknown: {type(result).__name__}"


_default_retrainer: AutoRetrainer | None = None


def get_auto_retrainer(fetcher=None, symbols=None) -> AutoRetrainer:
    """Process-wide singleton. Live wiring passes pipeline._fetch_data."""
    global _default_retrainer
    if _default_retrainer is None:
        if fetcher is None:
            raise RuntimeError(
                "get_auto_retrainer requires a fetcher on first call "
                "(wire to AutonomousPipeline._fetch_data in qna.py daemon)")
        _default_retrainer = AutoRetrainer(fetcher=fetcher, symbols=symbols or ["EURUSD"])
    return _default_retrainer


def reset_singleton() -> None:
    global _default_retrainer
    _default_retrainer = None
