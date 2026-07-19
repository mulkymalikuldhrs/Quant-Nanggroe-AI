"""QuickVeto Bridge — Proposal-based Pre-filter untuk QNA Risk Pipeline.

Adaptasi dari E:\\trading\\risk_guard.py (AI Market Maker) untuk QNA ecosystem.

Perbedaan dengan RiskCheckGate (9 checkpoint):
- QuickVeto adalah PRE-filter cepat — cek dulu sebelum masuk ke 9 checkpoint
- API-nya proposal-based (dict), cocok untuk LLM agent pipeline
- Melengkapi RiskGateBridge dengan pre-filter market volatility + position sizing

Alur:
  1. LLM Agent → proposal dict
  2. QuickVetoBridge.evaluate(proposal) — 5 quick checks + kill switch
  3. Jika VETOED → return langsung, trade dibatalkan
  4. Jika APPROVED → lanjut ke RiskGateBridge (9 checkpoint)

Constitutional limits dari quant_nanggroe.engine.risk.constants — SINGLE SOURCE OF TRUTH.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.risk.constants import (
    MAX_DAILY_LOSS as _MAX_DAILY_LOSS_FRAC,
    MAX_DRAWDOWN_PCT as _MAX_DRAWDOWN_FRAC,
    MAX_LEVERAGE as _MAX_LEVERAGE,
    MAX_RISK_PER_TRADE as _MAX_RISK_PER_TRADE_FRAC,
    MAX_POSITION_SIZE_PCT as _MAX_POSITION_SIZE_FRAC,
)
from quant_nanggroe.engine.risk.manager import RiskManager

logger = logging.getLogger(__name__)

# ── Default paths ────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "quick_veto"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Enums ────────────────────────────────────────────────────────────────────


class QuickVerdict(str, Enum):
    """Verdict dari QuickVeto pre-filter."""
    APPROVED = "APPROVED"
    VETOED = "VETOED"
    KILL_SWITCH = "KILL_SWITCH"


# ── Data models ──────────────────────────────────────────────────────────────


@dataclass
class QuickVetoResult:
    """Hasil evaluasi QuickVeto.

    Attributes:
        verdict: APPROVED / VETOED / KILL_SWITCH
        risk_score: 0.0 (safe) — 1.0 (veto)
        reasons: Alasan veto
        symbol: Trading symbol
        action: buy / sell / hold
        adjusted_volume: Volume yang disarankan jika dimodifikasi
        timestamp: Waktu evaluasi
    """
    verdict: QuickVerdict
    risk_score: float
    reasons: List[str] = field(default_factory=list)
    symbol: str = ""
    action: str = ""
    adjusted_volume: Optional[float] = None
    threshold: float = 0.8
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "reasons": self.reasons,
            "symbol": self.symbol,
            "action": self.action,
            "adjusted_volume": self.adjusted_volume,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "source": "quick_veto_bridge",
        }


# ── Bridge ───────────────────────────────────────────────────────────────────


class QuickVetoBridge:
    """Proposal-based pre-filter bridge untuk QNA risk pipeline.

    API ini adaptasi dari E:\\trading\\risk_guard.py yang digunakan oleh
    hedge_fund_mtf.py untuk quick veto sebelum eksekusi MT5.

    Perbedaan utama:
      - Mengambil constitutional limits dari QNA engine/risk/constants.py
      - Menggunakan QNA RiskManager untuk kill switch + P&L tracking
      - Integrasi dengan RiskGateBridge untuk 9 checkpoint selanjutnya

    Usage:
        bridge = QuickVetoBridge(risk_manager=my_risk_manager)
        result = bridge.evaluate({
            "symbol": "BTCUSDT",
            "action": "buy",
            "volume": 0.1,
            "price": 65000.0,
            "sl": 64000.0,
            "account_balance": 10000.0,
            "daily_pnl": -50.0,
            "open_positions": 2,
            "market_volatility": 0.02,  # ATR / price
        })
        if result.verdict == QuickVerdict.VETOED:
            return {"action": "HOLD"}  # Blocked by pre-filter
    """

    def __init__(
        self,
        risk_manager: Optional[RiskManager] = None,
        policy_overrides: Optional[Dict[str, Any]] = None,
        log_veto: bool = True,
    ):
        self._risk_manager = risk_manager
        self._log_veto = log_veto
        self._policy = {
            # Defaults dari constitutional constants + overrides
            "risk_score_threshold": 0.8,
            "max_position_size_pct": _MAX_POSITION_SIZE_FRAC,
            "max_daily_loss_pct": _MAX_DAILY_LOSS_FRAC,
            "max_leverage": _MAX_LEVERAGE,
            "max_drawdown_pct": _MAX_DRAWDOWN_FRAC,
            "max_open_positions": 20,
            "volatility_emergency_threshold": 0.05,  # 5% intraday vol
            "sl_max_pct": 0.05,  # 5% max stop loss distance
            "concentration_limit": _MAX_POSITION_SIZE_FRAC * 3,
        }
        if policy_overrides:
            self._policy.update(policy_overrides)

        logger.info(
            "QuickVetoBridge initialized | threshold=%.2f max_pos=%.1f%% "
            "max_loss=%.1f%% max_leverage=%.1fx vol_emerg=%.2f",
            self._policy["risk_score_threshold"],
            self._policy["max_position_size_pct"] * 100,
            self._policy["max_daily_loss_pct"] * 100,
            self._policy["max_leverage"],
            self._policy["volatility_emergency_threshold"],
        )

    # ── Public API ───────────────────────────────────────────────────────────

    def evaluate(self, proposal: Dict[str, Any]) -> QuickVetoResult:
        """Main entry: evaluate proposal dan return verdict.

        Proposal keys:
            symbol (str): Trading symbol
            action (str): 'buy' | 'sell' | 'hold'
            volume (float): Lot / quantity
            price (float): Entry price
            sl (float, optional): Stop loss price
            tp (float, optional): Take profit price
            account_balance (float): Current balance
            daily_pnl (float): Today's P&L
            open_positions (int): Current open positions
            market_volatility (float): ATR / price
            leverage (float, optional): Requested leverage
        """
        symbol = str(proposal.get("symbol", "UNKNOWN"))
        action = str(proposal.get("action", "hold")).lower()
        volume = float(proposal.get("volume", 0.01))
        price = float(proposal.get("price", 0.0))
        balance = float(proposal.get("account_balance", 1000.0))
        daily_pnl = float(proposal.get("daily_pnl", 0.0))
        open_pos = int(proposal.get("open_positions", 0))
        volatility = float(proposal.get("market_volatility", 0.0))

        logger.info(
            "QuickVeto: %s %s | vol=%.4f price=%.2f balance=%.2f "
            "pnl=%.2f pos=%d vola=%.4f",
            action.upper(), symbol, volume, price, balance,
            daily_pnl, open_pos, volatility,
        )

        # 1. Kill switch — via RiskManager
        if self._risk_manager and self._risk_manager.kill_switch.is_active:
            logger.critical("QuickVeto KILL_SWITCH: %s %s", action.upper(), symbol)
            return self._result(
                QuickVerdict.KILL_SWITCH, 1.0, ["kill_switch_active"],
                symbol, action,
            )

        # Kill switch via env var (fallback jika RiskManager tidak tersedia)
        if _env_truthy("HEDGE_KILL_SWITCH") or _env_truthy("HEDGE_RISK_GUARD_KILL"):
            return self._result(
                QuickVerdict.KILL_SWITCH, 1.0, ["kill_switch_env_active"],
                symbol, action,
            )

        # 2. Run 5 quick checks
        risk_score = 0.0
        reasons: List[str] = []

        # Check A: Position size vs balance
        notional = volume * price if price > 0 else 0
        pos_ratio = notional / balance if balance > 0 else 1.0
        max_pos = self._policy["max_position_size_pct"]
        if pos_ratio > max_pos * 1.5:
            risk_score = max(risk_score, 0.95)
            reasons.append(f"position_too_large ratio={pos_ratio:.2%} > {max_pos:.2%}")
        elif pos_ratio > max_pos:
            risk_score = max(risk_score, 0.75)
            reasons.append(f"position_large ratio={pos_ratio:.2%} ~ {max_pos:.2%}")

        # Check B: Daily loss limit
        if daily_pnl < 0:
            loss_ratio = abs(daily_pnl) / balance if balance > 0 else 0
            max_loss = self._policy["max_daily_loss_pct"]
            if loss_ratio > max_loss * 1.2:
                risk_score = max(risk_score, 1.0)
                reasons.append(f"daily_loss_limit_hit loss={loss_ratio:.2%} > {max_loss:.2%}")
            elif loss_ratio > max_loss:
                risk_score = max(risk_score, 0.85)
                reasons.append(f"daily_loss_high loss={loss_ratio:.2%} ~ {max_loss:.2%}")

        # Check C: Concentration (open positions)
        max_positions = self._policy["max_open_positions"]
        if open_pos >= max_positions:
            risk_score = max(risk_score, 0.9)
            reasons.append(f"max_positions_reached {open_pos} >= {max_positions}")
        elif open_pos >= max_positions * 0.8:
            risk_score = max(risk_score, 0.6)
            reasons.append(f"near_max_positions {open_pos}/{max_positions}")

        # Check D: Market volatility emergency
        vol_threshold = self._policy["volatility_emergency_threshold"]
        if volatility > vol_threshold:
            risk_score = max(risk_score, min(1.0, volatility * 5))
            reasons.append(f"high_volatility vol={volatility:.4f} > {vol_threshold}")

        # Check E: Stop loss distance
        sl = float(proposal.get("sl", 0))
        if price > 0 and sl > 0:
            sl_pct = abs(price - sl) / price
            sl_max = self._policy["sl_max_pct"]
            if sl_pct > sl_max:
                risk_score = max(risk_score, min(0.9, sl_pct * 10))
                reasons.append(f"wide_stop_loss sl={sl_pct:.2%} > {sl_max:.2%}")

        # Default: no checks triggered, moderate risk
        if not reasons:
            risk_score = 0.35
            reasons.append("quick_checks_passed_default_caution")
        else:
            risk_score = min(1.0, max(0.0, risk_score))

        # Threshold decision
        threshold = self._policy["risk_score_threshold"]
        verdict = QuickVerdict.VETOED if risk_score > threshold else QuickVerdict.APPROVED

        result = QuickVetoResult(
            verdict=verdict,
            risk_score=risk_score,
            reasons=reasons[:6],
            symbol=symbol,
            action=action,
            threshold=threshold,
        )

        if self._log_veto:
            self._log_decision(result, proposal)

        if verdict == QuickVerdict.VETOED:
            logger.warning(
                "QuickVeto %s %s → VETOED (score=%.3f > %.2f) | reasons: %s",
                action.upper(), symbol, risk_score, threshold,
                "; ".join(reasons[:3]),
            )
        else:
            logger.info(
                "QuickVeto %s %s → APPROVED (score=%.3f ≤ %.2f)",
                action.upper(), symbol, risk_score, threshold,
            )

        return result

    # ── Internal ─────────────────────────────────────────────────────────────

    def _result(
        self,
        verdict: QuickVerdict,
        risk_score: float,
        reasons: List[str],
        symbol: str,
        action: str,
    ) -> QuickVetoResult:
        return QuickVetoResult(
            verdict=verdict,
            risk_score=risk_score,
            reasons=reasons,
            symbol=symbol,
            action=action,
        )

    def _log_decision(self, decision: QuickVetoResult, proposal: Dict[str, Any]) -> None:
        """Log QuickVeto decision ke file JSONL (sama format seperti risk_guard.py)."""
        log_entry = {
            "decision": decision.to_dict(),
            "proposal_summary": {
                "symbol": proposal.get("symbol"),
                "action": proposal.get("action"),
                "volume": proposal.get("volume"),
                "price": proposal.get("price"),
            },
        }
        log_file = LOG_DIR / f"decisions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except OSError as e:
            logger.warning("Failed to log QuickVeto decision: %s", e)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _env_truthy(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def create_quick_veto(
    risk_manager: Optional[RiskManager] = None,
    policy_overrides: Optional[Dict[str, Any]] = None,
) -> QuickVetoBridge:
    """Factory: create QuickVetoBridge dengan default settings."""
    return QuickVetoBridge(
        risk_manager=risk_manager,
        policy_overrides=policy_overrides,
    )


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    bridge = create_quick_veto()

    test_proposal = {
        "symbol": "BTCUSDT",
        "action": "buy",
        "volume": 0.02,
        "price": 65000.0,
        "sl": 64500.0,
        "account_balance": 10000.0,
        "daily_pnl": -50.0,
        "open_positions": 1,
        "market_volatility": 0.001,
    }

    result = bridge.evaluate(test_proposal)
    print(json.dumps(result.to_dict(), indent=2))
