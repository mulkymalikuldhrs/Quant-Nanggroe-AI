"""
Macro Context Provider
======================
Integrates all causal macro engines into the pipeline as upstream signal context.
Provides macro weather filtering, causal bias alignment, COT positioning checks,
SMT divergence detection, and thesis drift guard for every pipeline run.

v6.1.0: Fixed orphaned imports, duplicate instances, and filter short-circuit.
All filters stack cumulatively instead of short-circuiting on first trigger.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from quant_nanggroe.engine.causal import MasterQuantNanggroeEngine
from quant_nanggroe.engine.causal.cme_provider import CMEPriceProvider
from quant_nanggroe.engine.causal.models import CausalContext
from quant_nanggroe.engine.risk.dcc_state import DCCState

logger = logging.getLogger("QNA-MacroContext")


class MacroContextProvider:
    """
    Integrates all macro engines into the pipeline as upstream context.

    All data flows through MasterQuantNanggroeEngine — no duplicate
    sub-engine instances. The 5-stage filter applies cumulatively.
    """

    SYMBOL_TO_FUTURES = {
        "XAUUSD": "GC1!", "XAGUSD": "SI1!", "GOLD": "GC1!", "SILVER": "SI1!",
        "US500": "ES1!", "SPX": "ES1!", "SP500": "ES1!",
        "NAS100": "NQ1!", "US100": "NQ1!",
        "US30": "YM1!", "DJI": "YM1!", "DOW": "YM1!",
        "EURUSD": "6E1!", "GBPUSD": "6B1!", "USDJPY": "6J1!",
        "AUDUSD": "6A1!", "USDCAD": "6C1!", "USDCHF": "6S1!",
        "DXY": "DXY",
        "US10Y": "ZN1!", "US30Y": "ZB1!",
        "BTCUSDT": "BTC1!", "BTCUSD": "BTC1!", "BTC": "BTC1!",
        "ETHUSDT": "ETH1!", "ETHUSD": "ETH1!", "ETH": "ETH1!",
        "USOIL": "CL1!", "UKOIL": "CL1!", "WTI": "CL1!",
        "NG": "NG1!", "NATGAS": "NG1!",
    }

    def __init__(self, enable_fred: bool = False, enable_cot: bool = False):
        # Single master engine — all sub-engines live here
        self.master = MasterQuantNanggroeEngine(
            enable_fred=enable_fred, enable_cot=enable_cot,
        )
        self.cme = CMEPriceProvider()
        self.dcc = DCCState()

    def _resolve_futures(self, symbol: str) -> str:
        return self.SYMBOL_TO_FUTURES.get(symbol.upper(), symbol.upper())

    def get_signal_context(self, symbol: str, causal_ctx: Optional[CausalContext] = None) -> Dict[str, Any]:
        futures = self._resolve_futures(symbol)
        context: Dict[str, Any] = {
            "macro_bias": 0.0,
            "macro_weather": "UNKNOWN",
            "cot_signal": "neutral",
            "cot_percentile": None,
            "dcc_mean_corr": None,
            "dcc_mean_vol": None,
            "dcc_n_assets": 0,
            "smt_diverged": False,
            "smt_zscore": None,
            "thesis_ok": True,
            "futures_symbol": futures,
            "msi_n_significant": 0,
        }

        dcc_status = self.dcc.get_status()
        context["dcc_mean_corr"] = dcc_status.get("mean_corr")
        context["dcc_mean_vol"] = dcc_status.get("mean_vol_pct")
        context["dcc_n_assets"] = dcc_status.get("n_assets", 0)

        # Use CausalContext if provided, otherwise fall back to env vars
        if causal_ctx is not None:
            context["macro_bias"] = causal_ctx.bias_for(futures)
            context["macro_weather"] = causal_ctx.macro_regime.upper()
        else:
            raw_bias = os.environ.get(f"QNA_CAUSAL_BIAS_{futures}", "")
            if raw_bias:
                try:
                    context["macro_bias"] = float(raw_bias)
                except (ValueError, TypeError):
                    pass

        weather = os.environ.get("QNA_MACRO_WEATHER", "")
        if weather:
            context["macro_weather"] = weather

        cot_signal = os.environ.get("QNA_COT_SIGNAL", "")
        if cot_signal:
            context["cot_signal"] = cot_signal.lower()
        cot_pct = os.environ.get("QNA_COT_PERCENTILE", "")
        if cot_pct:
            try:
                context["cot_percentile"] = float(cot_pct)
            except (ValueError, TypeError):
                pass

        smt_flag = os.environ.get("QNA_SMT_DIVERGENCE", "false").lower()
        context["smt_diverged"] = smt_flag == "true"

        msi_n = os.environ.get("QNA_MSI_N_SIGNIFICANT", "")
        if msi_n:
            try:
                context["msi_n_significant"] = int(msi_n)
            except (ValueError, TypeError):
                pass

        return context

    def apply_macro_filter(
        self,
        symbol: str,
        signal_side: str,
        confidence: float,
        causal_ctx: Optional[CausalContext] = None,
    ) -> Tuple[str, float, str]:
        """
        Apply macro filters cumulatively — all stages stack.

        Args:
            symbol: Trading symbol.
            signal_side: Raw signal side ('buy' / 'sell' / 'hold').
            confidence: Raw signal confidence.
            causal_ctx: Optional CausalContext. When provided, used as the
                        macro bias source instead of QNA_* env vars.

        Returns (filtered_side, filtered_confidence, reason_chain).
        """
        context = self.get_signal_context(symbol, causal_ctx=causal_ctx)
        reasons: List[str] = []
        current_side = signal_side
        current_conf = confidence

        # Stage 1: Macro weather
        weather = context["macro_weather"]
        if weather == "RISK_OFF" and current_side == "buy":
            current_conf *= 0.7
            reasons.append(f"Weather({weather}) x0.7")
        elif weather == "RISK_ON" and current_side == "sell":
            current_conf *= 0.7
            reasons.append(f"Weather({weather}) x0.7")

        # Stage 2: Causal bias alignment
        bias = context["macro_bias"]
        if bias != 0.0:
            direction = 1 if current_side == "buy" else -1
            alignment = direction * bias
            if alignment < -0.5:
                current_side = "hold"
                current_conf = 0.0
                reasons.append(f"Bias({bias:+.2f}) BLOCKED")
            elif alignment < -0.2:
                current_conf *= max(0.3, 1.0 - abs(alignment))
                reasons.append(f"Bias({bias:+.2f}) x{max(0.3, 1.0 - abs(alignment)):.2f}")
            elif alignment > 0.3:
                current_conf = min(current_conf * 1.3, 1.0)
                reasons.append(f"Bias({bias:+.2f}) BOOST")
            else:
                reasons.append(f"Bias({bias:+.2f}) OK")

        # Stage 3: COT extreme filter
        cot = context["cot_signal"]
        if "crowded_long" in str(cot) and current_side == "buy":
            current_conf *= 0.5
            reasons.append(f"COT({cot}) x0.5")
        elif "crowded_short" in str(cot) and current_side == "sell":
            current_conf *= 0.5
            reasons.append(f"COT({cot}) x0.5")

        # Stage 4: SMT divergence
        if context.get("smt_diverged") and current_side != "hold":
            current_side = "hold"
            current_conf = 0.0
            reasons.append("SMT_DIVERGED BLOCKED")

        # Stage 5: Thesis drift
        if current_side != "hold":
            thesis_check = self.master.check_thesis_drift({
                "macro_weather": weather,
                "cot_status": os.environ.get("QNA_COT_SIGNAL", "BALANCED"),
                "dcc_mean_corr": context["dcc_mean_corr"],
                "dcc_mean_vol": context["dcc_mean_vol"],
                "asset_biases": {context["futures_symbol"]: context["macro_bias"]},
                "event_type": os.environ.get("QNA_MACRO_EVENT", "UNKNOWN"),
            })
            if thesis_check.get("stage") == "STAGE_2_EXECUTE":
                current_side = "hold"
                current_conf = 0.0
                reasons.append(f"Thesis({thesis_check.get('action')}) BLOCKED")

        reason_chain = " | ".join(reasons) if reasons else "Passed"
        return (current_side, round(current_conf, 4), reason_chain)


__all__ = ["MacroContextProvider"]
