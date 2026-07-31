"""VIX Gate — blocks/reduces trading based on VIX fear level.

Fail-closed: if VIX data is unavailable, treat as VIX > 35 (block).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VixGateResult:
    """Result from a VIX gate check."""
    __slots__ = ("vix_value", "block_trading", "reduce_size", "reason")

    def __init__(
        self,
        vix_value: float = 0.0,
        block_trading: bool = False,
        reduce_size: bool = False,
        reason: str = "",
    ) -> None:
        self.vix_value = vix_value
        self.block_trading = block_trading
        self.reduce_size = reduce_size
        self.reason = reason


class VixGate:
    """Checks current VIX level and gates trading accordingly.

    VIX < 25:  normal trading
    VIX 25–35: reduce max position size by 50%
    VIX > 35:  no new positions (block)

    Fail-closed: unavailable VIX data → VIX > 35 (block).
    """

    VIX_NORMAL: float = 25.0
    VIX_HIGH: float = 35.0

    def __init__(self) -> None:
        self._last_raw: Optional[float] = None

    def _fetch_vix(self) -> Optional[float]:
        """Fetch current VIX level.

        Tries MT5 symbol VIX (or VIX-USD / VIXX) first, then falls
        back to an environment override (QNA_VIX_OVERRIDE) for testing.
        Returns None on any failure (fail-closed).
        """
        vix = None
        try:
            from quant_nanggroe.hedge_fund.utils.config import MT5_AVAILABLE, mt5

            if MT5_AVAILABLE:
                for sym in ("VIX", "VIX-USD", "VIXX", "VIX-IND"):
                    try:
                        tick = mt5.symbol_info_tick(sym)
                        if tick is not None and tick.bid > 0:
                            vix = float(tick.bid)
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        if vix is not None:
            self._last_raw = vix
            return vix

        override = self._env_override()
        if override is not None:
            self._last_raw = override
            return override

        return None

    @staticmethod
    def _env_override() -> Optional[float]:
        raw = __import__("os").environ.get("QNA_VIX_OVERRIDE")
        if raw:
            try:
                return float(raw)
            except (ValueError, TypeError):
                pass
        return None

    def evaluate(self) -> VixGateResult:
        """Check current VIX and return the gate result."""
        vix = self._fetch_vix()

        if vix is None:
            logger.critical("VIX data unavailable — FAIL CLOSED, blocking all trades")
            return VixGateResult(
                vix_value=-1.0,
                block_trading=True,
                reduce_size=False,
                reason="VIX data unavailable (fail-closed)",
            )

        if vix > self.VIX_HIGH:
            logger.warning("VIX=%.1f > %s — blocking all new positions", vix, self.VIX_HIGH)
            return VixGateResult(
                vix_value=vix,
                block_trading=True,
                reduce_size=False,
                reason=f"VIX={vix:.1f} exceeds high threshold ({self.VIX_HIGH})",
            )

        if vix >= self.VIX_NORMAL:
            logger.info("VIX=%.1f in [%s, %s] — reducing position size by 50%%", vix, self.VIX_NORMAL, self.VIX_HIGH)
            return VixGateResult(
                vix_value=vix,
                block_trading=False,
                reduce_size=True,
                reason=f"VIX={vix:.1f} in elevated zone — size halved",
            )

        logger.info("VIX=%.1f < %s — normal trading", vix, self.VIX_NORMAL)
        return VixGateResult(
            vix_value=vix,
            block_trading=False,
            reduce_size=False,
            reason="normal",
        )
