"""
MasterQuantNanggroeEngine — Causal Macro, Intermarket, SMT, COT & SMC Execution Engine.

Embedded from Riset_QNA.md — Master Blueprint & Master Document Riset Kuantitatif Komprehensif.
Synthesizes the 4 phases into one integrated quantitative engine:

  FASE 1 — Causal & Macro Engine (CKG + MSI)
  FASE 2 — Dynamic Regime & Intermarket (Lead-Lag + SMT + Macro Weather + COT)
  FASE 3 — Strategy Context & Dhaher SMC Filter
  FASE 4 — Portfolio Risk & Guardrails (Kelly + Thesis Invalidation)

Usage:
    from quant_nanggroe.engine.causal import MasterQuantNanggroeEngine
    engine = MasterQuantNanggroeEngine()
    biases = engine.evaluate_causal_bias("GEOPOLITICAL_SUPPLY_SHOCK", 
                                         geopolitical_risk_delta=40.0)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class MasterQuantNanggroeEngine:
    """
    Quant-Nanggroe-AI: Master Integrated Quantitative Engine.
    
    Synthesizes Causal Macro, Intermarket Futures Lead-Lag, COT Tracking, 
    and SMC/ICT Execution into a unified signal pipeline.
    """

    def __init__(self, surprise_threshold: float = 1.5):
        self.surprise_threshold = surprise_threshold

    # ──────────────────────────────────────────────────────────────
    # FASE 1: CAUSAL & MACRO ENGINE
    # ──────────────────────────────────────────────────────────────

    def calculate_macro_surprise(
        self, actual: float, consensus: float, hist_std: float
    ) -> float:
        """
        Macro Surprise Index (MSI): standardized deviation from consensus.

        MSI_i = (Actual_i - Consensus_i) / sigma_historical(i)

        |MSI| > 1.5 => significant surprise that triggers bias revision.

        Args:
            actual: Released economic data point.
            consensus: Market consensus / median forecast.
            hist_std: Historical standard deviation of the series.

        Returns:
            Standardized surprise score (z-score).
        """
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
        Causal Knowledge Graph (CKG) inference: map macro event → asset bias.

        Converts unstructured news/event narratives into a mathematical tuple:
            ⟨Cause Event, Effect Variable, Direction, Impact Magnitude⟩

        Args:
            event_type: Type of macro event.
            msi_score: Macro Surprise Index (if applicable).
            geopolitical_risk_delta: Geopolitical risk change in % (0-100).

        Returns:
            Dict of asset → directional bias (-1.0 to +1.0).
        """
        bias: Dict[str, float] = {
            "GC1!": 0.0, "ES1!": 0.0, "DXY": 0.0,
            "ZB1!": 0.0, "6E1!": 0.0, "SI1!": 0.0,
        }

        if event_type == "GEOPOLITICAL_SUPPLY_SHOCK":
            impact = np.clip(geopolitical_risk_delta / 100.0, 0.0, 1.0)
            bias["GC1!"] = +0.9 * impact   # Gold safe-haven demand
            bias["ES1!"] = -0.8 * impact   # Equities risk-off
            bias["DXY"] = +0.6 * impact    # USD cash inflow
            bias["ZB1!"] = +0.7 * impact   # Bond safe-haven

        elif event_type == "INFLATION_SURPRISE":
            if abs(msi_score) >= self.surprise_threshold:
                direction = np.sign(msi_score)
                bias["DXY"] = +0.9 * direction
                bias["ES1!"] = -0.7 * direction
                bias["GC1!"] = -0.5 * direction
                bias["6E1!"] = -0.8 * direction

        elif event_type == "CENTRAL_BANK_DOVISH":
            bias["ES1!"] = +0.7
            bias["DXY"] = -0.6
            bias["ZB1!"] = +0.5
            bias["6E1!"] = +0.4

        elif event_type == "CENTRAL_BANK_HAWKISH":
            bias["ES1!"] = -0.7
            bias["DXY"] = +0.6
            bias["ZB1!"] = -0.5
            bias["6E1!"] = -0.4

        elif event_type == "RISK_ON_SENTIMENT":
            bias["ES1!"] = +0.8
            bias["GC1!"] = -0.3
            bias["DXY"] = -0.4

        elif event_type == "RISK_OFF_SENTIMENT":
            bias["ES1!"] = -0.8
            bias["GC1!"] = +0.5
            bias["DXY"] = +0.4
            bias["ZB1!"] = +0.5

        return bias

    # ──────────────────────────────────────────────────────────────
    # FASE 2: DYNAMIC INTERMARKET & MACRO WEATHER
    # ──────────────────────────────────────────────────────────────

    def detect_macro_weather(
        self, dxy_change_pct: float, bond_zb_change_pct: float
    ) -> str:
        """
        Macro Weather Matrix: classify market regime from cross-asset moves.

        Reference mapping:
            ☀️ Risk-On:   DXY↓, Bonds↓   => Equities↑, Crypto↑, AUD/NZD↑
            🌧 Risk-Off:  DXY↑, Bonds↑   => Gold↑, USD↑, Bonds↑ (safe-haven)

        Args:
            dxy_change_pct: DXY % change (positive = USD strengthening).
            bond_zb_change_pct: ZB1! (30Y T-Bond) % change.

        Returns:
            Weather classification string.
        """
        if dxy_change_pct > 0.3 and bond_zb_change_pct > 0.2:
            return "RISK_OFF"
        elif dxy_change_pct < -0.3 and bond_zb_change_pct < -0.1:
            return "RISK_ON"
        return "NEUTRAL_MIXED"

    def check_smt_divergence(
        self,
        futures_a_highs: list[float],
        futures_b_highs: list[float],
    ) -> bool:
        """
        SMT Divergence: check for divergence between correlated pairs.

        Correlated pairs:
            - GC1! (Gold) ↔ SI1! (Silver)   — should move together
            - ES1! (S&P)  ↔ NQ1! (Nasdaq)   — should move together
            - 6E1! (EUR)  ↔ 6B1! (GBP)      — should move together

        If A makes Higher High (HH) but B fails (Lower High = LH),
        that's an SMT Divergence — potential fake move / liquidity grab.

        Args:
            futures_a_highs: Recent highs for pair A (e.g. GC1! Gold).
            futures_b_highs: Recent highs for pair B (e.g. SI1! Silver).

        Returns:
            True if SMT divergence is detected.
        """
        if len(futures_a_highs) < 2 or len(futures_b_highs) < 2:
            return False
        a_hh = futures_a_highs[-1] > futures_a_highs[-2]
        b_hh = futures_b_highs[-1] > futures_b_highs[-2]
        return a_hh != b_hh

    # ──────────────────────────────────────────────────────────────
    # FASE 2: COT INSTITUTIONAL POSITIONING
    # ──────────────────────────────────────────────────────────────

    def evaluate_cot_positioning(
        self,
        net_positions: float,
        hist_min: float,
        hist_max: float,
    ) -> str:
        """
        Evaluate COT positioning using historical percentile.

        Non-Commercial (Managed Money / Hedge Funds):
            Percentile > 90%  => EXTREME_LONG_OVERBOUGHT — crowded trade, potential reversal
            Percentile < 10%  => EXTREME_SHORT_OVERSOLD — capitulation, potential bottom
            Otherwise         => BALANCED — no extreme signal

        Commercials (Hedgers / Smart Money):
            True smart money accumulates at bottoms, distributes at tops.

        Non-Reportable (Retail):
            Contrarian indicator — retail is usually wrong at extremes.

        Args:
            net_positions: Current net position count.
            hist_min: Historical minimum net position (5-year lookback).
            hist_max: Historical maximum net position (5-year lookback).

        Returns:
            Positioning signal string.
        """
        if hist_max == hist_min:
            return "BALANCED"
        percentile = (net_positions - hist_min) / (hist_max - hist_min)
        if percentile >= 0.90:
            return "EXTREME_LONG_OVERBOUGHT"
        elif percentile <= 0.10:
            return "EXTREME_SHORT_OVERSOLD"
        return "BALANCED"

    # ──────────────────────────────────────────────────────────────
    # FASE 3-4: DHAHER SMC EXECUTION FILTER + KELLY RISK
    # ──────────────────────────────────────────────────────────────

    def validate_execution_setup(
        self,
        macro_bias: float,
        smc_signal: str,
        rrr: float,
        winrate: float,
        smt_divergence: bool = False,
    ) -> Dict[str, Any]:
        """
        Dhaher System Formula v1.0 — Execution filter & Kelly sizing.

        System Expectancy:
            E = (P_win × RRR) - (P_loss × 1.0)

        Gate conditions:
            1. Macro bias must align with SMC signal (directional filter)
            2. Expectancy > 0.2
            3. RRR >= 3.0
            4. No SMT divergence against the trade direction
            5. SMT divergence in the same direction = extra confirmation

        Risk sizing via Fractional Kelly (safety factor λ = 0.25):
            f* = λ × ((p × b - q) / b)
            Capped at 0.5% max risk per trade (institutional guardrail).

        Args:
            macro_bias: Directional bias from Causal Engine (-1.0 to +1.0).
            smc_signal: SMC signal direction ("BUY" or "SELL").
            rrr: Reward-to-Risk Ratio (e.g. 3.5).
            winrate: Historical win rate (0.0 to 1.0).
            smt_divergence: True if SMT divergence detected between correlated pairs.

        Returns:
            Dict with executable flag, expectancy, alignment, risk %, and reasoning.
        """
        expectancy = (winrate * rrr) - ((1 - winrate) * 1.0)

        # Check macro → SMC alignment
        aligned = False
        if macro_bias > 0.3 and smc_signal == "BUY":
            aligned = True
        elif macro_bias < -0.3 and smc_signal == "SELL":
            aligned = True

        # SMT divergence logic:
        #   - Same direction divergence = extra confirmation (smart money positioning)
        #   - Opposite direction divergence = potential fake move → BLOCK
        smt_confirms = False
        smt_blocks = False
        if smt_divergence:
            if smc_signal == "BUY":
                smt_blocks = True   # divergence in correlated pair warns against buy
            elif smc_signal == "SELL":
                smt_confirms = True  # divergence confirms sell (weakness in correlated asset)

        executable = aligned and (expectancy > 0.2) and (rrr >= 3.0) and not smt_blocks

        # Fractional Kelly with strict 0.5% cap (λ = 0.25 safety factor)
        kelly_f = 0.0
        risk_pct = 0.0
        if executable:
            b = rrr
            p = winrate
            q = 1 - p
            kelly_raw = (p * b - q) / b if b > 0 else 0.0
            kelly_f = 0.0025 * kelly_raw  # quarter-Kelly (0.25% safety factor) → overridden by quarter-Kelly cap below  # safety factor λ = 0.25
            risk_pct = min(max(kelly_f, 0.0), 0.005)  # strict 0.5% max

        return {
            "executable": executable,
            "macro_aligned": aligned,
            "smt_divergence": smt_divergence,
            "smt_confirms_trade": smt_confirms,
            "smt_blocks_trade": smt_blocks,
            "system_expectancy": round(expectancy, 4),
            "rrr": rrr,
            "raw_kelly_fraction": round(kelly_f, 4),
            "calculated_risk_pct": round(risk_pct * 100, 4),
            "max_possible_risk_pct": 0.5,
            "reason": (
                f"{'✅ EXECUTABLE' if executable else '❌ BLOCKED'}: "
                f"bias={macro_bias:+.2f} smc={smc_signal} "
                f"expectancy={expectancy:.2f} rrr={rrr:.1f} "
                f"risk={risk_pct*100:.2f}% "
                f"{'smt_div=CONFIRM' if smt_confirms else ''}"
                f"{'smt_div=BLOCK' if smt_blocks else ''}"
            ),
        }

    def evaluate_full_pipeline(
        self,
        event_type: str,
        geopolitical_risk_delta: float = 0.0,
        dxy_change: float = 0.0,
        bond_change: float = 0.0,
        msi_score: float = 0.0,
        gold_highs: list[float] | None = None,
        silver_highs: list[float] | None = None,
        cot_net_positions: float | None = None,
        cot_hist_min: float | None = None,
        cot_hist_max: float | None = None,
        smc_signal: str = "HOLD",
        rrr: float = 3.0,
        winrate: float = 0.48,
        # ── DCC-GARCH integration ─────────────────────────────
        returns: Any | None = None,           # (n_days x n_assets) returns array
        dcc_garch_instance: Any | None = None, # pre-fitted DCCGARCH instance
        # ── MSI / FRED integration ────────────────────────────
        msi_api_key: str | None = None,       # FRED API key for MSI auto-eval
        msi_instance: Any | None = None,       # pre-configured MacroSurpriseIndex
        # ── SMT cointegration integration ─────────────────────
        smt_price_data: Any | None = None,    # price DataFrame for cointegration SMT
        smt_detector_instance: Any | None = None,  # pre-fitted CointegrationSMTDetector
    ) -> dict[str, Any]:
        """
        Run the full 4-phase evaluation pipeline end-to-end.

        Extended with DCC-GARCH correlation/volatility estimates and
        Macro Surprise Index (MSI) from FRED data.

        If a pre-configured MSI instance or FRED API key is provided,
        the pipeline auto-fetches economic data and computes MSI scores
        for all tracked indicators, mapped to QNA event types.

        This is the main entry point for agentic/trading systems.

        Returns a complete decision dict with causal context, macro weather,
        intermarket analysis, COT context, DCC correlation, MSI scores,
        and execution decision.
        """
        result: dict[str, Any] = {
            "phase1_causal": {},
            "phase1_msi": {},
            "phase2_weather": {},
            "phase2_cot": {},
            "phase2_smt": {},
            "phase2_dcc": {},
            "phase3_decision": {},
            "summary": "",
        }

        # Phase 0: DCC-GARCH dynamic correlation
        dcc_corr = None
        dcc_vols = None
        dcc_cov = None
        dcc_diag: dict[str, Any] = {}
        if dcc_garch_instance is not None and hasattr(dcc_garch_instance, "fitted"):
            if dcc_garch_instance.fitted:
                dcc_corr = dcc_garch_instance.correlation
                dcc_vols = dcc_garch_instance.volatilities
                dcc_cov = dcc_garch_instance.covariance
                dcc_diag = dcc_garch_instance.get_status()
        elif returns is not None:
            # Lazily fit DCC-GARCH from raw returns
            try:
                from quant_nanggroe.engine.risk.dcc_garch import DCCGARCH
                dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
                dcc.fit(returns)
                if dcc.fitted:
                    dcc_corr = dcc.correlation
                    dcc_vols = dcc.volatilities
                    dcc_cov = dcc.covariance
                    dcc_diag = dcc.get_status()
            except Exception as e:
                logger.debug("DCC-GARCH lazy fit failed: %s", e)
        result["phase2_dcc"] = {
            "fitted": dcc_corr is not None,
            "mean_corr": float(np.mean(dcc_corr)) if dcc_corr is not None else None,
            "mean_vol_pct": float(dcc_diag.get("mean_vol_pct", 0)) if dcc_diag else None,
            "n_assets": len(dcc_vols) if dcc_vols is not None else 0,
            "asset_names": dcc_diag.get("asset_names") if dcc_diag else None,
        }

        # Phase 1: Causal bias
        biases = self.evaluate_causal_bias(
            event_type=event_type,
            msi_score=msi_score,
            geopolitical_risk_delta=geopolitical_risk_delta,
        )
        result["phase1_causal"] = {"event": event_type, "asset_biases": biases}

        # Phase 1: Macro Surprise Index (auto-fetch from FRED if configured)
        msi_results: dict[str, Any] = {}
        if msi_instance is not None:
            try:
                if hasattr(msi_instance, "evaluate_all"):
                    msi_instance.evaluate_all()
                    msi_results = msi_instance.get_summary()
                    logger.info(
                        "MSI: %d indicators, %d significant surprises",
                        msi_results.get("n_indicators", 0),
                        msi_results.get("n_significant", 0),
                    )
            except Exception as e:
                logger.debug("MSI instance eval failed: %s", e)
        elif msi_api_key:
            try:
                from quant_nanggroe.engine.macro import MacroSurpriseIndex
                msi = MacroSurpriseIndex(api_key=msi_api_key)
                if msi.is_connected:
                    msi.evaluate_all()
                    msi_results = msi.get_summary()
                    logger.info(
                        "MSI auto-fetched: %d indicators, %d significant",
                        msi_results.get("n_indicators", 0),
                        msi_results.get("n_significant", 0),
                    )
            except Exception as e:
                logger.debug("MSI auto-fetch failed: %s", e)
        result["phase1_msi"] = {
            "connected": bool(msi_results),
            "n_significant": msi_results.get("n_significant", 0),
            "events": msi_results.get("events", {}),
            "threshold": self.surprise_threshold,
        }

        # Phase 2: Macro weather
        weather = self.detect_macro_weather(
            dxy_change_pct=dxy_change, bond_zb_change_pct=bond_change
        )
        result["phase2_weather"] = {"classification": weather}

        # Phase 2: SMT divergence — cointegration-based (Bennett 2022) + heuristic fallback
        smt_flag = False
        smt_diag: dict[str, Any] = {"method": "none", "n_divergent": 0}

        # Try cointegration-based detector first (requires price history)
        # Reuse a cached detector, or create one from smt_price_data, or accept pre-fitted
        if smt_detector_instance is not None:
            # Pre-fitted detector provided — use it directly
            self._smt_detector = smt_detector_instance

        if smt_price_data is not None:
            # Lazy-init detector from raw price data
            try:
                from quant_nanggroe.engine.intermarket import CointegrationSMTDetector

                if not hasattr(self, "_smt_detector") or self._smt_detector is None:
                    self._smt_detector = CointegrationSMTDetector(z_score_threshold=2.0)
                if not self._smt_detector.fitted:
                    self._smt_detector.fit(smt_price_data)
            except ImportError:
                pass
            except Exception as e:
                logger.debug("SMT lazy-fit failed: %s", e)

        # Detect divergences from cached/configured detector
        if hasattr(self, "_smt_detector") and self._smt_detector is not None:
            if self._smt_detector.fitted:
                detections = self._smt_detector.detect()
                smt_flag = any(r.divergence_detected for r in detections.values())
                smt_diag = {
                    "method": "cointegration",
                    "n_pairs": self._smt_detector.n_cointegrated,
                    "n_divergent": sum(1 for r in detections.values() if r.divergence_detected),
                    "blocked_symbols": self._smt_detector.get_blocked_symbols(),
                }

        # Fallback to heuristic if cointegration not available
        if smt_diag.get("method", "") not in ("cointegration",) or not smt_diag.get("n_pairs", 0):
            if gold_highs and silver_highs:
                smt_flag = self.check_smt_divergence(gold_highs, silver_highs)
                smt_diag["method"] = "heuristic"

        result["phase2_smt"] = {
            "smt_divergence_detected": smt_flag,
            **smt_diag,
        }

        # Phase 2: COT institutional positioning
        cot_status = "BALANCED"
        cot_diag: dict[str, Any] = {}
        if cot_net_positions is not None and cot_hist_min is not None and cot_hist_max is not None:
            cot_status = self.evaluate_cot_positioning(
                net_positions=cot_net_positions,
                hist_min=cot_hist_min,
                hist_max=cot_hist_max,
            )
        # Try COTAnalyzer if available (auto-fetches live COT data)
        try:
            from quant_nanggroe.engine.cot import COTAnalyzer
            if not hasattr(self, "_cot_analyzer") or self._cot_analyzer is None:
                self._cot_analyzer = COTAnalyzer(years_history=3)
            if not self._cot_analyzer.is_loaded:
                self._cot_analyzer.fetch_history()
            if self._cot_analyzer.is_loaded:
                # Determine which symbol to evaluate based on weather context
                cot_sym = "GC1!"
                if weather == "RISK_ON":
                    cot_sym = "ES1!"
                elif event_type == "INFLATION_SURPRISE":
                    cot_sym = "6E1!"
                eval_result = self._cot_analyzer.evaluate(cot_sym)
                if eval_result.get("signal") != "NOT_FOUND":
                    cot_status = eval_result.get("signal", "BALANCED")
                    cot_diag = {
                        "analyzer_used": True,
                        "symbol": cot_sym,
                        "market": eval_result.get("market"),
                        "percentile_noncomm": eval_result.get("percentile_noncomm"),
                        "percentile_comm": eval_result.get("percentile_comm"),
                        "grade": eval_result.get("grade"),
                        "action": eval_result.get("action"),
                        "net_noncomm": eval_result.get("net_noncomm"),
                        "latest_date": eval_result.get("latest_date"),
                        "n_weeks_history": eval_result.get("n_weeks_history"),
                    }
        except ImportError:
            pass
        except Exception as e:
            logger.debug("COTAnalyzer lazy load failed: %s", e)

        result["phase2_cot"] = {
            "status": cot_status,
            **cot_diag,
        }

        # Phase 3-4: Execution decision
        # Use GC1! bias as the primary macro bias for Gold/XAU trading
        macro_bias = biases.get("GC1!", 0.0)
        if weather == "RISK_ON":
            macro_bias = biases.get("ES1!", 0.0)  # equities bias in risk-on
        elif weather == "RISK_OFF":
            macro_bias = biases.get("GC1!", 0.0)  # gold bias in risk-off

        decision = self.validate_execution_setup(
            macro_bias=macro_bias,
            smc_signal=smc_signal,
            rrr=rrr,
            winrate=winrate,
            smt_divergence=smt_flag,
        )
        result["phase3_decision"] = decision

        # Build summary with DCC context
        dcc_note = ""
        if dcc_corr is not None:
            dcc_note = f"DCC corr={result['phase2_dcc']['mean_corr']:.3f} "
        summary = (
            f"QNA Master Engine: [{event_type}] → Weather={weather} "
            f"COT={cot_status} "
            f"{'🚩SMT' if smt_flag else '✓'} "
            f"{dcc_note}"
            f"{'✅ TRADE' if decision['executable'] else '❌ BLOCKED'}: "
            f"{smc_signal} | "
            f"risk={decision['calculated_risk_pct']:.2f}% | "
            f"E={decision['system_expectancy']:.2f}"
        )
        result["summary"] = summary

        return result
