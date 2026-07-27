"""Crypto-Specific multi-mode strategy (funding arb, liquidations, on-chain, DEX arb, MEV)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class CryptoSpecificStrategy(Strategy):
    """Crypto-specific multi-mode strategy.

    Supports: funding_rate_arb, liquidation_cascade, on_chain, dex_arb, mev_aware.
    """

    name = "crypto_specific"
    description = "Crypto-specific: funding arb, liquidations, on-chain, DEX arb, MEV"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.mode: str = str(self._parameters.get("mode", "funding_rate_arb"))
        self.lookback: int = int(self._parameters.get("lookback", 24))
        self.entry_threshold: float = float(self._parameters.get("entry_threshold", 0.0003))
        self.exit_threshold: float = float(self._parameters.get("exit_threshold", 0.0001))
        self.stop_loss_pct: float = float(self._parameters.get("stop_loss_pct", 0.05))
        self.take_profit_pct: float = float(self._parameters.get("take_profit_pct", 0.10))
        self.cascade_z_threshold: float = float(self._parameters.get("cascade_z_threshold", 2.5))
        self.whale_threshold: float = float(self._parameters.get("whale_threshold", 1_000_000))
        self.funding_rate_column: str = str(self._parameters.get("funding_rate_column", "funding_rate"))
        self.open_interest_column: str = str(self._parameters.get("open_interest_column", "open_interest"))
        self.symbol: str = str(self._parameters.get("symbol", "BTC"))

    @staticmethod
    def _compute_zscore(series: pd.Series, period: int) -> pd.Series:
        rolling_mean = series.rolling(window=period, min_periods=period).mean()
        rolling_std = series.rolling(window=period, min_periods=period).std()
        return (series - rolling_mean) / (rolling_std + 1e-10)

    def _funding_rate_signal(self, data: pd.DataFrame, price: float) -> Optional[StrategySignal]:
        if self.funding_rate_column not in data.columns:
            return None
        funding_rate = data[self.funding_rate_column]
        current_fr = float(funding_rate.iloc[-1])
        avg_fr = float(funding_rate.iloc[-self.lookback:].mean()) if len(funding_rate) >= self.lookback else current_fr
        annualized_carry = current_fr * 3 * 365

        if current_fr > self.entry_threshold:
            confidence = min(current_fr / self.entry_threshold, 1.0)
            return StrategySignal(
                strategy_name=self.name,
                symbol=self.symbol,
                direction=SignalDirection.SELL,
                confidence=round(confidence, 4),
                entry_price=round(price, 6),
                stop_loss=round(price * (1 + self.stop_loss_pct), 6),
                take_profit=round(price * (1 - self.take_profit_pct), 6),
                reasoning=f"Funding rate arb: FR={current_fr:.6f} > {self.entry_threshold:.6f}, annualized={annualized_carry:.4f}",
                indicators={"funding_rate": round(current_fr, 8), "avg_funding_rate": round(avg_fr, 8), "mode": "funding_rate_arb"},
            )
        if current_fr < -self.entry_threshold:
            confidence = min(abs(current_fr) / self.entry_threshold, 1.0)
            return StrategySignal(
                strategy_name=self.name,
                symbol=self.symbol,
                direction=SignalDirection.BUY,
                confidence=round(confidence, 4),
                entry_price=round(price, 6),
                stop_loss=round(price * (1 - self.stop_loss_pct), 6),
                take_profit=round(price * (1 + self.take_profit_pct), 6),
                reasoning=f"Funding rate arb: FR={current_fr:.6f} < -{self.entry_threshold:.6f}, annualized={annualized_carry:.4f}",
                indicators={"funding_rate": round(current_fr, 8), "avg_funding_rate": round(avg_fr, 8), "mode": "funding_rate_arb"},
            )
        return None

    def _liquidation_cascade_signal(self, data: pd.DataFrame, price: float) -> Optional[StrategySignal]:
        close = data["close"]
        volume = data["volume"]
        returns = close.pct_change().dropna()
        if len(returns) < self.lookback:
            return None
        return_z = self._compute_zscore(returns, self.lookback)
        volume_z = self._compute_zscore(volume, self.lookback)
        current_return_z = float(return_z.iloc[-1]) if not np.isnan(return_z.iloc[-1]) else 0.0
        current_volume_z = float(volume_z.iloc[-1]) if not np.isnan(volume_z.iloc[-1]) else 0.0

        if abs(current_return_z) > self.cascade_z_threshold and current_volume_z > 1.5:
            if current_return_z < -self.cascade_z_threshold:
                confidence = min(abs(current_return_z) / self.cascade_z_threshold, 1.0) * 0.8
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=self.symbol,
                    direction=SignalDirection.BUY,
                    confidence=round(confidence, 4),
                    entry_price=round(price, 6),
                    stop_loss=round(price * (1 - self.stop_loss_pct), 6),
                    take_profit=round(price * (1 + self.take_profit_pct), 6),
                    reasoning=f"Liquidation cascade BUY: return_z={current_return_z:.2f}, volume_z={current_volume_z:.2f}",
                    indicators={"return_z": round(current_return_z, 4), "volume_z": round(current_volume_z, 4), "mode": "liquidation_cascade"},
                )
            else:
                confidence = min(abs(current_return_z) / self.cascade_z_threshold, 1.0) * 0.8
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=self.symbol,
                    direction=SignalDirection.SELL,
                    confidence=round(confidence, 4),
                    entry_price=round(price, 6),
                    stop_loss=round(price * (1 + self.stop_loss_pct), 6),
                    take_profit=round(price * (1 - self.take_profit_pct), 6),
                    reasoning=f"Liquidation cascade SELL: return_z={current_return_z:.2f}, volume_z={current_volume_z:.2f}",
                    indicators={"return_z": round(current_return_z, 4), "volume_z": round(current_volume_z, 4), "mode": "liquidation_cascade"},
                )
        return None

    def _on_chain_signal(self, data: pd.DataFrame, price: float) -> Optional[StrategySignal]:
        if "exchange_inflow" not in data.columns or "exchange_outflow" not in data.columns:
            return None
        inflow = data["exchange_inflow"]
        outflow = data["exchange_outflow"]
        whale_tx = data.get("whale_tx_count", pd.Series(0, index=data.index))
        net_flow = outflow - inflow
        current_net_flow = float(net_flow.iloc[-1])
        avg_net_flow = float(net_flow.iloc[-self.lookback:].mean()) if len(net_flow) >= self.lookback else current_net_flow

        whale_z = 0.0
        if whale_tx is not None and len(whale_tx) >= self.lookback:
            wzs = self._compute_zscore(whale_tx, self.lookback)
            if not np.isnan(wzs.iloc[-1]):
                whale_z = float(wzs.iloc[-1])

        if current_net_flow > avg_net_flow * 2 and whale_z > 1.0:
            confidence = min(abs(current_net_flow) / (abs(avg_net_flow) + 1), 1.0)
            return StrategySignal(
                strategy_name=self.name,
                symbol=self.symbol,
                direction=SignalDirection.BUY,
                confidence=round(confidence, 4),
                entry_price=round(price, 6),
                stop_loss=round(price * (1 - self.stop_loss_pct), 6),
                take_profit=round(price * (1 + self.take_profit_pct), 6),
                reasoning=f"On-chain BULLISH: net_flow={current_net_flow:.0f}, whale_z={whale_z:.2f}",
                indicators={"net_flow": round(current_net_flow, 2), "whale_z": round(whale_z, 4), "mode": "on_chain"},
            )
        if current_net_flow < avg_net_flow * 0.5 and whale_z > 1.0:
            confidence = min(abs(current_net_flow) / (abs(avg_net_flow) + 1), 1.0)
            return StrategySignal(
                strategy_name=self.name,
                symbol=self.symbol,
                direction=SignalDirection.SELL,
                confidence=round(confidence, 4),
                entry_price=round(price, 6),
                stop_loss=round(price * (1 + self.stop_loss_pct), 6),
                take_profit=round(price * (1 - self.take_profit_pct), 6),
                reasoning=f"On-chain BEARISH: net_flow={current_net_flow:.0f}, whale_z={whale_z:.2f}",
                indicators={"net_flow": round(current_net_flow, 2), "whale_z": round(whale_z, 4), "mode": "on_chain"},
            )
        return None

    def _dex_arb_signal(self, data: pd.DataFrame, price: float) -> Optional[StrategySignal]:
        if "dex_price" not in data.columns or "cex_price" not in data.columns:
            return None
        dex_price = float(data["dex_price"].iloc[-1])
        cex_price = float(data["cex_price"].iloc[-1])
        if dex_price <= 0 or cex_price <= 0:
            return None
        spread = (dex_price - cex_price) / cex_price
        fee_estimate = 0.002
        net_spread = abs(spread) - fee_estimate
        if net_spread > self.entry_threshold:
            confidence = min(net_spread / self.entry_threshold, 1.0)
            if spread > 0:
                direction = SignalDirection.SELL
                dir_str = "sell DEX / buy CEX"
            else:
                direction = SignalDirection.BUY
                dir_str = "buy DEX / sell CEX"
            return StrategySignal(
                strategy_name=self.name,
                symbol=self.symbol,
                direction=direction,
                confidence=round(confidence, 4),
                entry_price=round(price, 6),
                reasoning=f"DEX arb: {dir_str}, spread={spread:.4f}",
                indicators={"dex_price": round(dex_price, 6), "cex_price": round(cex_price, 6), "mode": "dex_arb"},
            )
        return None

    def _mev_signal(self, data: pd.DataFrame, price: float) -> Optional[StrategySignal]:
        if "solana_tip" not in data.columns or "priority_fee" not in data.columns:
            return None
        tips = data["solana_tip"]
        fees = data["priority_fee"]
        current_tip = float(tips.iloc[-1])
        current_fee = float(fees.iloc[-1])
        tip_z = 0.0
        fee_z = 0.0
        if len(tips) >= self.lookback:
            tip_zs = self._compute_zscore(tips, self.lookback)
            fee_zs = self._compute_zscore(fees, self.lookback)
            if not np.isnan(tip_zs.iloc[-1]):
                tip_z = float(tip_zs.iloc[-1])
            if not np.isnan(fee_zs.iloc[-1]):
                fee_z = float(fee_zs.iloc[-1])
        if tip_z > 2.0 or fee_z > 2.0:
            return StrategySignal(
                strategy_name=self.name,
                symbol=self.symbol,
                direction=SignalDirection.HOLD,
                confidence=0.8,
                entry_price=round(price, 6),
                reasoning=f"MEV high: delay execution (tip_z={tip_z:.2f}, fee_z={fee_z:.2f})",
                indicators={"tip_z": round(tip_z, 4), "fee_z": round(fee_z, 4), "mode": "mev_aware"},
            )
        return None

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            if len(data) < self.lookback + 10:
                return self._hold("Insufficient data")
            price = float(data["close"].iloc[-1])

            if self.mode == "funding_rate_arb":
                signal = self._funding_rate_signal(data, price)
            elif self.mode == "liquidation_cascade":
                signal = self._liquidation_cascade_signal(data, price)
            elif self.mode == "on_chain":
                signal = self._on_chain_signal(data, price)
            elif self.mode == "dex_arb":
                signal = self._dex_arb_signal(data, price)
            elif self.mode == "mev_aware":
                signal = self._mev_signal(data, price)
            else:
                signal = None

            if signal is not None:
                return signal
            return self._hold(f"No signal in mode={self.mode}")
        except Exception as exc:
            logger.error("CryptoSpecific error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["CryptoSpecificStrategy"]
