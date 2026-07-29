"""
Quant Nanggroe AI — Causal Macro Engine

Institutional-grade causal macro analysis suite for systematic hedge fund strategies.
Integrates event-driven causal inference, macro surprises, institutional positioning,
cross-asset divergence detection, and thesis drift circuit breakers.

Modules:
    causal_bias       → CausalKnowledgeGraph, event→asset bias mapping
    macro_surprise    → Macro Surprise Index via FRED
    cot_tracker       → CFTC Commitment of Traders analysis
    smt_divergence    → SMT divergence via Engle-Granger cointegration
    thesis_drift_guard → 3-stage thesis invalidation circuit breaker

Single entry point:
    engine = MasterQuantNanggroeEngine()
    result = engine.evaluate_full_pipeline(event_type, ...)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.causal.causal_bias import (
    CausalBiasEngine,
    CausalKnowledgeGraph,
)
from quant_nanggroe.engine.causal.cot_tracker import (
    COTAnalyzer,
    COTTracker,
)
from quant_nanggroe.engine.causal.macro_surprise import (
    MacroSurpriseIndex,
)

# ponytail: SMTDivergenceDetector needs statsmodels which isn't always installed.
# Imported lazily inside MasterQuantNanggroeEngine._init_sub_engines.
_SMT_AVAILABLE = False
try:
    from quant_nanggroe.engine.causal.smt_divergence import (
        SMTDivergenceDetector,
    )
    _SMT_AVAILABLE = True
except ImportError:
    SMTDivergenceDetector = None  # type: ignore

from quant_nanggroe.engine.causal.thesis_drift_guard import (
    ThesisDriftGuard,
)

logger = logging.getLogger(__name__)


class MasterQuantNanggroeEngine:
    """
    Master integrated causal macro engine.

    Synthesizes event-driven causal inference, macro surprises, institutional
    COT positioning, cross-asset SMT divergence, and DCC-GARCH dynamic
    correlation into a unified pipeline for systematic hedge fund decision-making.

    Pipeline phases:
        Phase 1 (Causal & Macro):
            - Causal Knowledge Graph: event → asset bias mapping
            - Macro Surprise Index: FRED surprise deviations
        Phase 2 (Dynamic Regime & Intermarket):
            - Macro Weather classification (Risk-On/Off)
            - COT institutional positioning
            - SMT divergence detection
            - DCC-GARCH dynamic correlation (if returns data provided)
        Phase 3 (Strategy Context):
            - Directional bias filtering
            - SMC alignment validation
        Phase 4 (Portfolio Risk):
            - Thesis drift invalidation
            - Risk sizing hints
    """

    def __init__(
        self,
        surprise_threshold: float = 1.5,
        dcc_a: float = 0.05,
        dcc_b: float = 0.90,
        enable_fred: bool = True,
        enable_cot: bool = True,
    ):
        """
        Args:
            surprise_threshold: |MSI| threshold for significant surprise (default: 1.5σ).
            dcc_a: DCC innovation parameter (default: 0.05).
            dcc_b: DCC persistence parameter (default: 0.90).
            enable_fred: Whether to attempt FRED API connection (default: True).
            enable_cot: Whether to load COT data (default: True).
        """
        self.surprise_threshold = surprise_threshold

        # Sub-engines (lazy-init)
        self._causal_bias: Optional[CausalBiasEngine] = None
        self._msi: Optional[MacroSurpriseIndex] = None
        self._cot: Optional[COTTracker] = None
        self._cot_analyzer: Optional[COTAnalyzer] = None
        self._smt: Optional[SMTDivergenceDetector] = None
        self._thesis_guard: Optional[ThesisDriftGuard] = None
        self._dcc: Any = None

        self._init_sub_engines(enable_fred, enable_cot, dcc_a, dcc_b)

    def _init_sub_engines(
        self,
        enable_fred: bool,
        enable_cot: bool,
        dcc_a: float,
        dcc_b: float,
    ) -> None:
        """Lazy-initialize sub-engines."""
        # Causal bias — always available (no external deps)
        self._causal_bias = CausalBiasEngine()

        # Macro Surprise Index — optional (needs FRED API key)
        if enable_fred:
            try:
                self._msi = MacroSurpriseIndex()
                logger.info("MSI engine initialized (FRED=%s)", self._msi.connected)
            except Exception as e:
                logger.debug("MSI init skipped: %s", e)
                self._msi = MacroSurpriseIndex(
                    fred_api_key=None
                )  # disconnected mode

        # COT Tracker — optional (needs network)
        if enable_cot:
            try:
                self._cot = COTTracker()
                self._cot_analyzer = COTAnalyzer(cot_tracker=self._cot)
                logger.info("COT engine initialized")
            except Exception as e:
                logger.debug("COT init skipped: %s", e)

        # SMT Divergence — requires statsmodels (optional dep)
        if _SMT_AVAILABLE:
            try:
                self._smt = SMTDivergenceDetector()
            except Exception as e:
                logger.debug("SMTDivergenceDetector init skipped: %s", e)
                self._smt = None
        else:
            self._smt = None

        # Thesis Drift Guard — always available (rule-based)
        self._thesis_guard = ThesisDriftGuard()

        # DCC-GARCH — lazy init when returns data provided
        try:
            from quant_nanggroe.engine.risk.dcc_garch import DCCGARCH

            self._dcc = DCCGARCH(dcc_a=dcc_a, dcc_b=dcc_b)
        except Exception as e:
            logger.debug("DCC-GARCH init skipped: %s", e)

    # ── Phase 1: Causal & Macro Engine ───────────────────────────

    def calculate_macro_surprise(
        self, actual: float, consensus: float, hist_std: float
    ) -> float:
        """Standardized macro surprise score."""
        if hist_std == 0:
            return 0.0
        return (actual - consensus) / hist_std

    def evaluate_causal_bias(
        self,
        event_type: str,
        msi_score: float = 0.0,
        geopolitical_risk_delta: float = 0.0,
    ) -> Dict[str, float]:
        """
        Evaluate directional biases for each asset class based on macro event.

        Returns dict of {CME_FUTURES_SYMBOL: bias_score} where:
            bias > 0  → bullish bias
            bias < 0  → bearish bias
            bias = 0  → neutral / no impact
        """
        if self._causal_bias is not None:
            return self._causal_bias.evaluate_causal_bias(
                event_type=event_type,
                msi_score=msi_score,
                geopolitical_risk_delta=geopolitical_risk_delta,
            )
        return {}

    # ── Phase 2: Dynamic Regime & Intermarket ───────────────────

    def detect_macro_weather(
        self, dxy_change_pct: float, bond_zb_change_pct: float
    ) -> str:
        """Classify macro weather based on DXY and bond movements."""
        if dxy_change_pct > 0.3 and bond_zb_change_pct > 0.2:
            return "RISK_OFF"
        elif dxy_change_pct < -0.3 and bond_zb_change_pct < -0.1:
            return "RISK_ON"
        return "NEUTRAL_MIXED"

    def check_smt_divergence(
        self,
        prices_a: List[float],
        prices_b: List[float],
        name_a: str = "asset_a",
        name_b: str = "asset_b",
    ) -> Dict[str, Any]:
        """
        Check SMT divergence between two correlated price series.

        Returns dict with:
            diverged: True/False
            zscore: Current cointegration z-score
            half_life: Mean reversion half-life (periods)
        """
        if self._smt is not None:
            return self._smt.check_divergence(
                series_a=prices_a,
                series_b=prices_b,
                name_a=name_a,
                name_b=name_b,
            )
        return {"diverged": False}

    def evaluate_cot_positioning(
        self,
        net_positions: float,
        hist_min: float,
        hist_max: float,
    ) -> str:
        """
        Evaluate institutional COT positioning percentile.

        Returns:
            EXTREME_LONG_OVERBOUGHT (≥90th percentile)
            EXTREME_SHORT_OVERSOLD (≤10th percentile)
            BALANCED
        """
        if (hist_max - hist_min) == 0:
            return "BALANCED"
        percentile = (net_positions - hist_min) / (hist_max - hist_min)
        if percentile >= 0.90:
            return "EXTREME_LONG_OVERBOUGHT"
        elif percentile <= 0.10:
            return "EXTREME_SHORT_OVERSOLD"
        return "BALANCED"

    def run_dcc_garch(
        self, returns: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Run DCC-GARCH dynamic correlation analysis.

        Args:
            returns: DataFrame of asset returns (columns = assets).

        Returns:
            Dict with correlation matrix, volatilities, status.
        """
        if self._dcc is None:
            return {"status": "unavailable"}

        try:
            if not self._dcc.fitted:
                self._dcc.fit(returns)

            if not self._dcc.fitted:
                return {"status": "fit_failed"}

            return {
                "status": "fitted",
                "mean_corr": float(
                    np.mean(
                        self._dcc.correlation[
                            np.triu_indices_from(self._dcc.correlation, k=1)
                        ]
                    )
                )
                if self._dcc.correlation.size > 1
                else 0.0,
                "mean_vol_pct": float(np.mean(self._dcc.volatilities) * 100)
                if self._dcc.volatilities.size > 0
                else 0.0,
                "n_assets": int(len(self._dcc.asset_names)),
                "correlation_matrix": self._dcc.correlation.tolist(),
                "volatilities": self._dcc.volatilities.tolist(),
                "diagnostics": self._dcc.get_status(),
            }
        except Exception as e:
            logger.warning("DCC-GARCH run failed: %s", e)
            return {"status": "error", "error": str(e)}

    # ── Phase 3-4: Strategy Context & Thesis Drift ──────────────

    def check_thesis_drift(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check thesis drift conditions.

        Args:
            context: Dict with macro conditions, position state, etc.

        Returns:
            Dict with drift status and recommended action.
        """
        if self._thesis_guard is not None:
            return self._thesis_guard.evaluate(context)
        return {"stage": "unknown", "action": "hold"}

    # ── Full Pipeline ──────────────────────────────────────────

    def evaluate_full_pipeline(
        self,
        event_type: str = "",
        geopolitical_risk_delta: float = 0.0,
        dxy_change: float = 0.0,
        bond_change: float = 0.0,
        smc_signal: str = "HOLD",
        rrr: float = 3.0,
        winrate: float = 0.48,
        returns: Optional[pd.DataFrame] = None,
        smc_signal_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full 4-phase causal macro pipeline.

        Phase 1 — Causal & Macro: Event bias + MSI
        Phase 2 — Dynamic Regime: Weather + COT + SMT + DCC-GARCH
        Phase 3 — Strategy Context: Bias filtering + SMC alignment
        Phase 4 — Portfolio Risk: Thesis drift + Kelly sizing

        Args:
            event_type: Macro event type (e.g. GEOPOLITICAL_SUPPLY_SHOCK).
            geopolitical_risk_delta: Geopolitical risk score delta.
            dxy_change: DXY index change percentage.
            bond_change: Bond future (ZB1!) change percentage.
            smc_signal: SMC trading signal (BUY/SELL/HOLD).
            rrr: Reward-to-risk ratio for Kelly sizing.
            winrate: Historical winrate for Kelly sizing.
            returns: Optional returns DataFrame for DCC-GARCH.
            smc_signal_params: Optional SMC signal parameters dict.

        Returns:
            Dict with all phases' results and pipeline summary.
        """
        result: Dict[str, Any] = {}

        # ── Phase 1: Causal & Macro ─────────────────────────
        phase1_causal = self.evaluate_causal_bias(
            event_type=event_type,
            geopolitical_risk_delta=geopolitical_risk_delta,
        )

        # Macro Surprise Index (current FRED data)
        phase1_msi: Dict[str, Any] = {"connected": False}
        if self._msi is not None and self._msi.connected:
            try:
                phase1_msi = self._msi.get_recent_surprises(
                    threshold=self.surprise_threshold
                )
            except Exception as e:
                logger.debug("MSI fetch failed: %s", e)
                phase1_msi = {"connected": True, "error": str(e)}

        result["phase1_causal"] = {
            "asset_biases": phase1_causal,
            "event_type": event_type,
            "geopolitical_risk_delta": geopolitical_risk_delta,
        }
        result["phase1_msi"] = phase1_msi

        # ── Phase 2: Dynamic Regime & Intermarket ───────────
        weather = self.detect_macro_weather(
            dxy_change_pct=dxy_change,
            bond_zb_change_pct=bond_change,
        )
        result["phase2_weather"] = {
            "classification": weather,
            "dxy_change_pct": dxy_change,
            "bond_change_pct": bond_change,
        }

        # COT positioning
        phase2_cot: Dict[str, Any] = {"status": "UNAVAILABLE"}
        if self._cot is not None:
            try:
                from quant_nanggroe.engine.causal.cot_tracker import COTAnalyzer
                if self._cot_analyzer is not None:
                    cot_signal = self._cot_analyzer.analyze()
                    phase2_cot = {
                        "status": cot_signal.get("signal", "UNKNOWN"),
                        "analyzer_used": True,
                        "symbol": cot_signal.get("symbol", ""),
                        "grade": cot_signal.get("grade", ""),
                        "action": cot_signal.get("action", ""),
                        "percentile_noncomm": cot_signal.get("percentile_noncomm"),
                    }
            except Exception as e:
                logger.debug("COT analysis failed: %s", e)
                phase2_cot = {"status": "ERROR", "error": str(e)}

        result["phase2_cot"] = phase2_cot

        # SMT divergence
        result["phase2_smt"] = {
            "smt_divergence_detected": False,
            "message": "SMT check requires price pair data",
        }

        # DCC-GARCH dynamic correlation
        phase2_dcc: Dict[str, Any] = {"status": "not_run"}
        if returns is not None and self._dcc is not None:
            try:
                dcc_result = self.run_dcc_garch(returns)
                phase2_dcc = dcc_result
            except Exception as e:
                logger.debug("DCC-GARCH failed: %s", e)
                phase2_dcc = {"status": "error", "error": str(e)}

        result["phase2_dcc"] = phase2_dcc

        # ── Phase 3: Strategy Context ───────────────────────
        phase3_directional_bias: Dict[str, float] = {}
        for asset, bias in phase1_causal.items():
            phase3_directional_bias[asset] = bias

        result["phase3_filter"] = {
            "directional_bias": phase3_directional_bias,
            "smc_signal_input": smc_signal,
        }

        # SMC alignment check
        smc_verdict = self._validate_execution_setup(
            macro_bias=np.mean(list(phase1_causal.values())) if phase1_causal else 0.0,
            smc_signal=smc_signal,
            rrr=rrr,
            winrate=winrate,
        )
        result["phase3_smc"] = smc_verdict

        # ── Phase 4: Portfolio Risk ──────────────────────────
        thesis_context = {
            "macro_weather": weather,
            "cot_status": phase2_cot.get("status", "UNKNOWN"),
            "dcc_mean_corr": phase2_dcc.get("mean_corr", None),
            "dcc_mean_vol": phase2_dcc.get("mean_vol_pct", None),
            "asset_biases": phase1_causal,
            "event_type": event_type,
        }
        thesis_drift = self.check_thesis_drift(thesis_context)
        result["phase4_thesis_drift"] = thesis_drift

        # Risk sizing hint
        result["phase4_risk"] = {
            "calculated_risk_pct": smc_verdict.get("calculated_risk_pct", 0.0),
            "executable": smc_verdict.get("executable", False),
        }

        # ── Summary ─────────────────────────────────────────
        result["summary"] = self._build_summary(result)

        return result

    # ── Internal helpers ─────────────────────────────────────

    def _validate_execution_setup(
        self,
        macro_bias: float,
        smc_signal: str,
        rrr: float,
        winrate: float,
    ) -> Dict[str, Any]:
        """
        Validate SMC execution setup against macro context.

        Returns:
            Dict with executable flag, expectancy, macro alignment.
        """
        expectancy = (winrate * rrr) - ((1 - winrate) * 1.0)

        aligned = False
        if macro_bias > 0.3 and smc_signal == "BUY":
            aligned = True
        elif macro_bias < -0.3 and smc_signal == "SELL":
            aligned = True

        # Fractional Kelly (safety factor = 0.25)
        is_executable = aligned and (expectancy > 0.2) and (rrr >= 2.0)
        kelly_f = (
            0.25 * (((winrate * rrr) - (1 - winrate)) / rrr)
            if is_executable
            else 0.0
        )
        risk_pct = min(max(kelly_f, 0.0), 0.005)  # Max 0.5%

        return {
            "executable": is_executable,
            "system_expectancy": round(expectancy, 2),
            "macro_aligned": aligned,
            "calculated_risk_pct": round(risk_pct * 100, 2),
        }

    def _build_summary(self, result: Dict[str, Any]) -> str:
        """
        Build a human-readable summary of the pipeline result.
        """
        parts = []

        # Weather
        weather = result.get("phase2_weather", {}).get("classification", "?")
        parts.append(f"Weather={weather}")

        # COT
        cot = result.get("phase2_cot", {}).get("status", "?")
        parts.append(f"COT={cot}")

        # Biases
        biases = result.get("phase1_causal", {}).get("asset_biases", {})
        if biases:
            bias_str = ",".join(
                f"{k}={v:.2f}" for k, v in sorted(biases.items())[:3]
            )
            parts.append(f"Biases=[{bias_str}]")

        # DCC
        dcc = result.get("phase2_dcc", {})
        if dcc.get("mean_corr") is not None:
            parts.append(f"DCC_corr={dcc['mean_corr']:.3f}")

        # SMT
        smt = result.get("phase2_smt", {})
        if smt.get("smt_divergence_detected"):
            parts.append("SMT_DIVERGED")

        # Thesis
        thesis = result.get("phase4_thesis_drift", {})
        parts.append(f"Thesis={thesis.get('stage', '?')}")

        # Executable
        exec_flag = result.get("phase4_risk", {}).get("executable", False)
        parts.append(f"Executable={'Y' if exec_flag else 'N'}")

        return " | ".join(parts)


__all__ = [
    "MasterQuantNanggroeEngine",
    "CausalBiasEngine",
    "CausalKnowledgeGraph",
    "MacroSurpriseIndex",
    "COTTracker",
    "COTAnalyzer",
    "SMTDivergenceDetector",
    "ThesisDriftGuard",
]
