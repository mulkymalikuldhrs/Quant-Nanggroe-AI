"""
SMT Alert System — Real-Time Divergence Monitor with Telegram Alerts
=====================================================================

Monitors all correlated pairs (GC1!/SI1!, ES1!/NQ1!, etc.) via
SMTDivergenceDetector, fetches live price data via CMEPriceProvider,
and sends Telegram alerts when |z-score| exceeds the divergence threshold.

Architecture:
    - Runs in a background daemon thread
    - Checks all pairs every N seconds (default: 300s / 5 min)
    - Deduplicates alerts: won't re-alert for the same divergence direction
      unless severity escalates or a new divergence appears after resolution
    - Sends resolution alerts when divergences normalize
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.causal.cme_provider import CMEPriceProvider
from quant_nanggroe.engine.causal.smt_divergence import SMTDivergenceDetector

logger = logging.getLogger(__name__)

SEVERITY_LEVELS = {"none": 0, "diverged": 1, "severe": 2}


def _pair_key(a: str, b: str) -> str:
    """Canonical pair key used by both detector and alert system."""
    return f"{a}<->{b}"


class SMTPairAlertState:
    """Tracks alert state for a single monitored pair to prevent spam."""

    def __init__(self, pk: str, name_a: str, name_b: str):
        self.pair_key = pk
        self.name_a = name_a
        self.name_b = name_b
        self.current_severity: str = "none"
        self.last_alert_severity: str = "none"
        self.last_alert_zscore: float = 0.0
        self.last_alert_direction: str = "NEUTRAL"
        self.last_alert_time: Optional[datetime] = None
        self.alert_count: int = 0
        self.alert_history: List[Dict[str, Any]] = []
        self.last_check_time: Optional[datetime] = None
        self.last_check_result: Optional[Dict[str, Any]] = None
        self.was_diverged: bool = False  # tracks if previous check was diverged

    def should_alert(self, result: Dict[str, Any], cooldown_seconds: int = 600) -> bool:
        severity = result.get("severity", "none")
        direction = result.get("direction", "NEUTRAL")

        if severity == "none":
            return False

        if self.last_alert_time is None:
            return True

        # Escalation
        if SEVERITY_LEVELS.get(severity, 0) > SEVERITY_LEVELS.get(self.last_alert_severity, 0):
            return True

        # Direction change
        if direction != self.last_alert_direction:
            return True

        # Cooldown expired
        if (datetime.now() - self.last_alert_time).total_seconds() >= cooldown_seconds:
            return True

        return False

    def record_alert(self, result: Dict[str, Any]) -> None:
        self.current_severity = result.get("severity", "none")
        self.last_alert_severity = self.current_severity
        self.last_alert_zscore = result.get("zscore", 0.0)
        self.last_alert_direction = result.get("direction", "NEUTRAL")
        self.last_alert_time = datetime.now()
        self.alert_count += 1
        self.alert_history.append({
            "time": self.last_alert_time.isoformat(),
            "severity": self.current_severity,
            "zscore": result.get("zscore"),
            "direction": result.get("direction"),
        })
        if len(self.alert_history) > 50:
            self.alert_history = self.alert_history[-50:]

    def resolve(self, result: Dict[str, Any]) -> None:
        """Mark divergence as resolved."""
        self.current_severity = "none"
        self.last_check_result = result
        self.was_diverged = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_key": self.pair_key,
            "name_a": self.name_a,
            "name_b": self.name_b,
            "current_severity": self.current_severity,
            "last_alert_severity": self.last_alert_severity,
            "last_zscore": self.last_alert_zscore,
            "last_direction": self.last_alert_direction,
            "last_alert_time": self.last_alert_time.isoformat() if self.last_alert_time else None,
            "alert_count": self.alert_count,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
        }


class SMTAlertSystem:
    """Real-time SMT divergence alert system with Telegram notifications."""

    MONITORED_PAIRS = [
        ("GC1!", "SI1!", "Gold / Silver"),
        ("ES1!", "NQ1!", "S&P 500 / Nasdaq"),
        ("6E1!", "6J1!", "EUR/USD / USD/JPY"),
        ("GC1!", "ZB1!", "Gold / Bonds"),
        ("ES1!", "ZB1!", "S&P 500 / Bonds"),
    ]

    def __init__(
        self,
        divergence_threshold: float = 2.0,
        severe_threshold: float = 3.0,
        check_interval: int = 300,
        lookback: int = 100,
        kline_interval: str = "1h",
        alert_cooldown: int = 600,
        enable_telegram: bool = True,
        enable_logging: bool = True,
    ):
        self.divergence_threshold = divergence_threshold
        self.severe_threshold = severe_threshold
        self.check_interval = check_interval
        self.lookback = lookback
        self.kline_interval = kline_interval
        self.alert_cooldown = alert_cooldown
        self.enable_telegram = enable_telegram
        self.enable_logging = enable_logging

        self.detector = SMTDivergenceDetector(
            divergence_threshold=divergence_threshold,
            severe_threshold=severe_threshold,
        )
        self.cme = CMEPriceProvider()

        self._pair_states: Dict[str, SMTPairAlertState] = {
            _pair_key(a, b): SMTPairAlertState(_pair_key(a, b), a, b)
            for a, b, _ in self.MONITORED_PAIRS
        }
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._cycle_count = 0
        self._last_check_time: Optional[datetime] = None
        self._total_divergences_found = 0
        self._total_alerts_sent = 0

        # Lazy import telegram
        self._send_telegram = None

    def _get_telegram(self):
        if self._send_telegram is None:
            try:
                from quant_nanggroe.notifier import send_telegram
                self._send_telegram = send_telegram
            except Exception:
                self._send_telegram = lambda msg, **kw: False
        return self._send_telegram

    # ── Single pair check ────────────────────────────────────────

    def _check_pair(self, name_a: str, name_b: str, pair_name: str) -> Dict[str, Any]:
        try:
            klines_a = self.cme.get_klines(name_a, interval=self.kline_interval, limit=self.lookback)
            klines_b = self.cme.get_klines(name_b, interval=self.kline_interval, limit=self.lookback)

            if not klines_a or not klines_b:
                return {
                    "pair_name": pair_name, "asset_a": name_a, "asset_b": name_b,
                    "diverged": False, "error": "No price data", "severity": "none", "zscore": 0.0,
                }

            return self.detector.check_divergence(
                series_a=[k["close"] for k in klines_a],
                series_b=[k["close"] for k in klines_b],
                name_a=name_a, name_b=name_b,
            )
        except Exception as e:
            logger.warning("SMT check failed for %s/%s: %s", name_a, name_b, e)
            return {
                "pair_name": pair_name, "asset_a": name_a, "asset_b": name_b,
                "diverged": False, "error": str(e), "severity": "none", "zscore": 0.0,
            }

    def check_all_pairs(self) -> List[Dict[str, Any]]:
        """Check all monitored pairs for SMT divergence. Handles alerts + resolutions."""
        with self._lock:
            self._cycle_count += 1
            results: List[Dict[str, Any]] = []

            for name_a, name_b, pair_name in self.MONITORED_PAIRS:
                result = self._check_pair(name_a, name_b, pair_name)
                pk = _pair_key(name_a, name_b)
                state = self._pair_states[pk]
                state.last_check_time = datetime.now()
                state.last_check_result = result
                results.append(result)

                if result.get("diverged"):
                    state.was_diverged = True
                    self._total_divergences_found += 1
                    if state.should_alert(result, self.alert_cooldown):
                        self._send_alert(result, state)
                        state.record_alert(result)
                    if self.enable_logging:
                        logger.warning(
                            "SMT: %s | z=%.2f | %s | hl=%.1f",
                            pair_name, result.get("zscore", 0),
                            result.get("severity"), result.get("half_life", 0),
                        )
                else:
                    # Resolution detection — resolve state FIRST, then fire-and-forget alert
                    if state.was_diverged or state.current_severity != "none":
                        logger.info("SMT resolved: %s (z=%.2f)", pair_name, result.get("zscore", 0))
                        state.resolve(result)
                        self._send_resolution_alert(state)

            self._last_check_time = datetime.now()
            diverged = sum(1 for r in results if r.get("diverged"))
            logger.info(
                "SMT cycle %d: %d/%d diverged (total=%d, alerts=%d)",
                self._cycle_count, diverged, len(results),
                self._total_divergences_found, self._total_alerts_sent,
            )
            return results

    # ── Telegram alerts ──────────────────────────────────────────

    def _format_alert_msg(self, result: Dict[str, Any]) -> str:
        severity = result.get("severity", "none")
        zscore = result.get("zscore", 0.0)
        pair_name = result.get("pair_name", "?")
        direction = result.get("direction", "NEUTRAL")
        half_life = result.get("half_life", "?")
        coint = result.get("is_cointegrated", False)
        hedge = result.get("hedge_ratio", "?")
        ns = result.get("n_samples", 0)

        emoji = "🚨" if severity == "severe" else "⚠️"
        label = "SEVERE DIVERGENCE" if severity == "severe" else "SMT DIVERGENCE"

        action = f"Convergence HL={half_life}" if coint else "Not cointegrated"
        if coint and abs(zscore) > 2.5:
            action += " | Pair trade opportunity"

        return (
            f"{emoji} <b>{label}</b>\n"
            f"• Pair: {pair_name}\n"
            f"• Z-score: <b>{zscore:+.2f}σ</b> ({severity})\n"
            f"• Direction: {direction}\n"
            f"• HL: {half_life} | Hedge: {hedge}\n"
            f"• Cointegrated: {'✅' if coint else '❌'} | Samples: {ns}\n"
            f"• Action: {action}\n"
            f"• Cycle: {self._cycle_count}"
        )

    def _send_alert(self, result: Dict[str, Any], state: SMTPairAlertState) -> bool:
        if not self.enable_telegram:
            return False
        send = self._get_telegram()
        msg = self._format_alert_msg(result)
        success = send(msg)
        if success:
            self._total_alerts_sent += 1
        return success

    def _send_resolution_alert(self, state: SMTPairAlertState) -> None:
        if not self.enable_telegram:
            return
        send = self._get_telegram()
        msg = (
            f"✅ <b>SMT RESOLVED</b>\n"
            f"• Pair: {state.name_a} / {state.name_b}\n"
            f"• Last alert: {state.last_alert_zscore:+.2f}σ\n"
            f"• Alerts sent: {state.alert_count}\n"
            f"• Spread converged — monitor for re-entry"
        )
        send(msg)

    # ── Background thread ────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, name="SMT-Alert", daemon=True)
        self._thread.start()
        logger.info("SMT alert started: interval=%ds, threshold=%.1fσ, %d pairs",
                     self.check_interval, self.divergence_threshold, len(self.MONITORED_PAIRS))

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._thread = None
        logger.info("SMT alert stopped")

    def _run_loop(self) -> None:
        while self._running:
            try:
                self.check_all_pairs()
            except Exception as e:
                logger.error("SMT cycle failed: %s", e)
            for _ in range(self.check_interval // 5):
                if not self._running:
                    return
                time.sleep(5)

    # ── Status ───────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            active = []
            for state in self._pair_states.values():
                if state.current_severity != "none":
                    d = state.to_dict()
                    r = state.last_check_result
                    if r:
                        d["zscore"] = r.get("zscore", 0)
                        d["half_life"] = r.get("half_life")
                        d["is_cointegrated"] = r.get("is_cointegrated", False)
                    active.append(d)

            return {
                "running": self._running,
                "cycle_count": self._cycle_count,
                "threshold": self.divergence_threshold,
                "severe_threshold": self.severe_threshold,
                "check_interval": self.check_interval,
                "alert_cooldown": self.alert_cooldown,
                "telegram_enabled": self.enable_telegram,
                "total_divergences_found": self._total_divergences_found,
                "total_alerts_sent": self._total_alerts_sent,
                "active_divergences": active,
                "n_active": len(active),
                "n_pairs": len(self.MONITORED_PAIRS),
                "last_check": self._last_check_time.isoformat() if self._last_check_time else None,
            }

    def get_pair_state(self, name_a: str, name_b: str) -> Optional[Dict[str, Any]]:
        pk = _pair_key(name_a, name_b)
        with self._lock:
            state = self._pair_states.get(pk)
            if state is None:
                return None
            d = state.to_dict()
            if state.last_check_result:
                d["result"] = state.last_check_result
            return d

    def get_alert_history(self) -> List[Dict[str, Any]]:
        history = []
        for state in self._pair_states.values():
            for alert in state.alert_history:
                alert["pair"] = f"{state.name_a}/{state.name_b}"
                history.append(alert)
        return sorted(history, key=lambda x: x.get("time", ""), reverse=True)[:100]


# ── Module-level singleton ───────────────────────────────────────

_smt_alert_instance: Optional[SMTAlertSystem] = None


def get_smt_alert_system(
    divergence_threshold: float = 2.0,
    check_interval: int = 300,
    enable_telegram: bool = True,
    auto_start: bool = False,
) -> SMTAlertSystem:
    global _smt_alert_instance
    if _smt_alert_instance is None:
        _smt_alert_instance = SMTAlertSystem(
            divergence_threshold=divergence_threshold,
            check_interval=check_interval,
            enable_telegram=enable_telegram,
        )
    if auto_start and not _smt_alert_instance._running:
        _smt_alert_instance.start()
    return _smt_alert_instance


__all__ = [
    "SMTAlertSystem",
    "SMTPairAlertState",
    "get_smt_alert_system",
    "_pair_key",
]
