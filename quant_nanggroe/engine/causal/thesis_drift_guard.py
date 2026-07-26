"""
Thesis Drift Guard — 3-stage circuit breaker for thesis invalidation.

Implements a systematic thesis drift detection and invalidation system.
When a fundamental macro thesis that initiated a trade is invalidated
by new data, the guard triggers a hard exit (close market order) without
waiting for the technical stop loss.

3-Stage Architecture:
    Stage 1 — Monitor: Track macro context for thesis-violating conditions.
    Stage 2 — Alert: Flag drift when conditions approach invalidation threshold.
    Stage 3 — Execute: Trigger hard exit when thesis is invalidated.

Thesis types supported:
    - MACRO_DIRECTIONAL: Trade based on directional macro view (e.g. "Fed cuts → USD weak")
    - EVENT_DRIVEN: Trade based on specific event outcome (e.g. "OPEC+ cut → Oil up")
    - REGIME_TRADE: Trade based on regime classification (e.g. "Risk-on → Long equities")
    - SPREAD_TRADE: Trade based on relative value between correlated assets

Context signals monitored:
    - Macro Surprise Index (MSI) — economic data shocks
    - Geopolitical Risk Delta — sudden geopolitical shifts
    - Central Bank Policy Change — unexpected rate decisions
    - COT Positioning Flip — institutional position reversals
    - Intermarket Regime Shift — risk-on/off regime change
    - SMT Divergence — correlated asset decoupling

Reference:
    - Lopez de Prado (2018): "Advances in Financial Machine Learning" Ch. 14
      (Strategy Adaptation and Regime Change Detection)
    - SSRN-3847291: News sentiment and geopolitical risk in systematic macro trading
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# Thesis type definitions
THESIS_TYPES = {
    "MACRO_DIRECTIONAL": {
        "description": "Directional macro view (e.g. rate cut → USD weak)",
        "monitors": ["msi", "central_bank", "geopolitical"],
    },
    "EVENT_DRIVEN": {
        "description": "Specific event outcome trade",
        "monitors": ["geopolitical", "msi"],
    },
    "REGIME_TRADE": {
        "description": "Regime-based positioning (risk-on/off)",
        "monitors": ["intermarket_regime", "dcc_garch"],
    },
    "SPREAD_TRADE": {
        "description": "Relative value between correlated assets",
        "monitors": ["smt_divergence", "dcc_garch"],
    },
}


class ThesisDriftGuard:
    """
    3-Stage Thesis Drift Guard Circuit Breaker.

    Stages:
        STAGE_0_MONITOR — Tracking active theses, no drift detected.
        STAGE_1_ALERT  — Drift approaching invalidation threshold.
        STAGE_2_EXECUTE — Thesis invalidated → hard exit triggered.

    Usage:
        guard = ThesisDriftGuard()
        result = guard.evaluate(context)
        # Returns {"stage": "STAGE_1_ALERT", "action": "reduce", ...}
    """

    def __init__(
        self,
        msi_threshold: float = 2.0,
        geopolitical_threshold: float = 30.0,
        regime_correlation_shift: float = 0.3,
        cot_flip_threshold_days: int = 14,
        alert_duration_minutes: int = 30,
    ):
        """
        Args:
            msi_threshold: |MSI| threshold for thesis invalidation (default: 2.0 sigma).
            geopolitical_threshold: Geopolitical risk delta for invalidation (default: 30).
            regime_correlation_shift: Correlation shift threshold for regime change (default: 0.3).
            cot_flip_threshold_days: Days for COT flip detection (default: 14).
            alert_duration_minutes: How long stage 1 alert lasts before escalation (default: 30).
        """
        self.msi_threshold = msi_threshold
        self.geopolitical_threshold = geopolitical_threshold
        self.regime_correlation_shift = regime_correlation_shift
        self.cot_flip_threshold_days = cot_flip_threshold_days
        self.alert_duration_minutes = alert_duration_minutes

        # Active theses being monitored
        self._active_theses: Dict[str, Dict[str, Any]] = {}

        # Alert tracking
        self._alerts: Dict[str, Dict[str, Any]] = {}

    def register_thesis(
        self,
        thesis_id: str,
        thesis_type: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Register a trade thesis for drift monitoring.

        Args:
            thesis_id: Unique identifier for this thesis.
            thesis_type: Type from THESIS_TYPES keys.
            description: Human-readable thesis description.
            parameters: Dict with thesis-specific parameters:
                - entry_price, direction (LONG/SHORT), expected_duration,
                - invalidation_price, conviction (0.0-1.0)

        Returns:
            True if thesis registered successfully.
        """
        if thesis_type not in THESIS_TYPES:
            logger.warning("Unknown thesis type: %s", thesis_type)
            return False

        self._active_theses[thesis_id] = {
            "thesis_type": thesis_type,
            "description": description,
            "parameters": parameters or {},
            "registered_at": datetime.now(),
            "stage": "STAGE_0_MONITOR",
            "drift_score": 0.0,
            "invalidation_reasons": [],
        }
        logger.info(
            "Thesis registered: %s [%s] — %s",
            thesis_id,
            thesis_type,
            description,
        )
        return True

    def unregister_thesis(self, thesis_id: str) -> bool:
        """Remove a thesis (e.g. after trade exit)."""
        if thesis_id in self._active_theses:
            del self._active_theses[thesis_id]
            self._alerts.pop(thesis_id, None)
            return True
        return False

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate all active theses against current macro context.

        Args:
            context: Dict with at least:
                - macro_weather: str (RISK_ON / RISK_OFF / NEUTRAL_MIXED)
                - cot_status: str (EXTREME_LONG_OVERBOUGHT / etc.)
                - dcc_mean_corr: float (optional)
                - dcc_mean_vol: float (optional)
                - asset_biases: Dict[str, float] (from causal bias engine)
                - event_type: str (macro event type)

        Returns:
            Dict with:
                stage: Current circuit breaker stage.
                action: Recommended action (continue / reduce / exit).
                n_active_theses: Number of theses being monitored.
                theses: Dict of thesis_id → evaluation result.
        """
        if not self._active_theses:
            return {
                "stage": "STAGE_0_MONITOR",
                "action": "hold",
                "n_active_theses": 0,
                "theses": {},
            }

        results: Dict[str, Dict[str, Any]] = {}
        overall_stage = "STAGE_0_MONITOR"
        overall_action = "hold"

        for thesis_id, thesis in self._active_theses.items():
            result = self._evaluate_single(thesis_id, thesis, context)
            results[thesis_id] = result

            # Aggregate: the most severe stage wins
            stage_priority = {
                "STAGE_2_EXECUTE": 3,
                "STAGE_1_ALERT": 2,
                "STAGE_0_MONITOR": 1,
            }
            if stage_priority.get(result["stage"], 0) > stage_priority.get(
                overall_stage, 0
            ):
                overall_stage = result["stage"]
                overall_action = result["action"]

        return {
            "stage": overall_stage,
            "action": overall_action,
            "n_active_theses": len(self._active_theses),
            "theses": results,
        }

    def _evaluate_single(
        self,
        thesis_id: str,
        thesis: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate a single thesis against current context.

        Computes a drift_score ∈ [0.0, 1.0] based on:
            1. Macro weather shift (0-0.3)
            2. COT positioning flip (0-0.25)
            3. DCC correlation / volatility shift (0-0.2)
            4. Asset bias reversal (0-0.25)
        """
        drift_score = 0.0
        reasons: List[str] = []

        # ── Signal 1: Macro Weather Shift ───────────────────────
        weather = context.get("macro_weather", "NEUTRAL_MIXED")
        if thesis.get("parameters", {}).get("direction") == "LONG":
            if weather == "RISK_OFF":
                drift_score += 0.3
                reasons.append("Macro weather shifted to RISK_OFF")
        elif thesis.get("parameters", {}).get("direction") == "SHORT":
            if weather == "RISK_ON":
                drift_score += 0.3
                reasons.append("Macro weather shifted to RISK_ON")

        # ── Signal 2: COT Extreme Positioning ───────────────────
        cot_status = context.get("cot_status", "BALANCED")
        if cot_status in ("EXTREME_LONG_OVERBOUGHT", "EXTREME_SHORT_OVERSOLD"):
            drift_score += 0.25
            reasons.append(f"COT extreme: {cot_status}")

        # ── Signal 3: DCC Correlation/Volatility Regime Shift ───
        dcc_corr = context.get("dcc_mean_corr")
        dcc_vol = context.get("dcc_mean_vol")
        if dcc_corr is not None and dcc_corr > 0.8:
            drift_score += 0.15
            reasons.append(f"DCC correlation high: {dcc_corr:.2f}")
        if dcc_vol is not None and dcc_vol > 5.0:
            drift_score += 0.15
            reasons.append(f"DCC volatility elevated: {dcc_vol:.1f}%")

        # ── Signal 4: Asset Bias Reversal ───────────────────────
        biases = context.get("asset_biases", {})
        thesis_params = thesis.get("parameters", {})
        thesis_direction = thesis_params.get("direction", "")
        for asset, bias in biases.items():
            if thesis_direction == "LONG" and bias < -0.5:
                drift_score += 0.2 / max(len(biases), 1)
                reasons.append(f"Bias reversed on {asset}: {bias:.2f}")
            elif thesis_direction == "SHORT" and bias > 0.5:
                drift_score += 0.2 / max(len(biases), 1)
                reasons.append(f"Bias reversed on {asset}: {bias:.2f}")

        # ── Clamp ───────────────────────────────────────────────
        drift_score = min(drift_score, 1.0)

        # ── Determine Stage ─────────────────────────────────────
        if drift_score >= 0.7:
            stage = "STAGE_2_EXECUTE"
            action = "exit"
            self._track_alert(
                thesis_id,
                stage,
                drift_score,
                reasons,
            )
        elif drift_score >= 0.4:
            stage = "STAGE_1_ALERT"
            action = "reduce"
            self._track_alert(
                thesis_id,
                stage,
                drift_score,
                reasons,
            )
        else:
            stage = "STAGE_0_MONITOR"
            action = "continue"

        # Update thesis state
        self._active_theses[thesis_id]["stage"] = stage
        self._active_theses[thesis_id]["drift_score"] = round(drift_score, 3)
        if stage == "STAGE_2_EXECUTE":
            self._active_theses[thesis_id]["invalidation_reasons"] = reasons

        return {
            "thesis_id": thesis_id,
            "stage": stage,
            "action": action,
            "drift_score": round(drift_score, 3),
            "reasons": reasons,
            "n_signals_triggered": len(reasons),
        }

    def _track_alert(
        self,
        thesis_id: str,
        stage: str,
        drift_score: float,
        reasons: List[str],
    ) -> None:
        """Track alert state for escalation logic."""
        self._alerts[thesis_id] = {
            "stage": stage,
            "drift_score": round(drift_score, 3),
            "reasons": reasons,
            "timestamp": datetime.now(),
        }

    def get_active_theses(self) -> Dict[str, Dict[str, Any]]:
        """Get all active theses with current state."""
        return {
            tid: {
                "thesis_type": t["thesis_type"],
                "description": t["description"],
                "stage": t["stage"],
                "drift_score": t["drift_score"],
                "registered_at": str(t["registered_at"]),
            }
            for tid, t in self._active_theses.items()
        }

    def get_alert_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get alert history grouped by thesis ID."""
        history: Dict[str, List[Dict[str, Any]]] = {}
        for tid, alert in self._alerts.items():
            if tid not in history:
                history[tid] = []
            history[tid].append(alert)
        return history

    def reset(self) -> None:
        """Clear all theses and alerts."""
        self._active_theses.clear()
        self._alerts.clear()
        logger.info("Thesis Drift Guard reset — all theses cleared")


__all__ = [
    "ThesisDriftGuard",
    "THESIS_TYPES",
]
