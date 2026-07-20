"""Crypto-Specific Strategies.

Implements production-quality crypto trading strategies:
1. Funding rate arbitrage (spot vs perpetual)
2. Liquidation cascade detection
3. On-chain metrics strategy (whale movements, exchange flows)
4. DEX arbitrage opportunity detection
5. MEV-aware execution (for Solana)

Academic References:
    - Alexander, C. & Dakos, M. (2020). "A Critical Investigation of Cryptocurrency
      Data." Economic Modelling, 87, 117-129.
    - Harvey, C.R., Ramachandran, A., & Santoro, J. (2021). DeFi and the Future of
      Finance. Wiley.
    - Daian, P., Goldfeder, S., et al. (2020). "Flash Boys 2.0: Frontrunning in
      Decentralized Exchanges." IEEE S&P.
    - Baur, D.G. & Dimpfl, T. (2018). "Asymmetric Volatility in Cryptocurrencies."
      Economics Letters, 173, 148-151.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class CryptoSpecificStrategy(BaseStrategy):
    """Crypto-specific trading strategy.

    Supports multiple sub-strategies via the 'mode' parameter:
    - 'funding_rate_arb': Funding rate arbitrage between spot and perpetual
    - 'liquidation_cascade': Detect and trade liquidation cascades
    - 'on_chain': Trade based on on-chain metrics
    - 'dex_arb': DEX arbitrage opportunity detection
    - 'mev_aware': MEV-aware execution for Solana

    Parameters:
        mode: Sub-strategy mode (default 'funding_rate_arb').
        lookback: Rolling window for calculations (default 24).
        entry_threshold: Entry threshold (varies by mode) (default 0.0003).
        exit_threshold: Exit threshold (default 0.0001).
        stop_loss_pct: Stop loss fraction (default 0.05).
        take_profit_pct: Take profit fraction (default 0.10).
        cascade_z_threshold: Z-score threshold for cascade detection (default 2.5).
        whale_threshold: Large transaction threshold in USD (default 1000000).
        funding_rate_column: Column name for funding rate data (default "funding_rate").
        open_interest_column: Column name for open interest (default "open_interest").
        symbol: Trading symbol (default "BTC").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="CryptoSpecific", params=params)
        self.mode: str = self.params.get("mode", "funding_rate_arb")
        self.lookback: int = self.params.get("lookback", 24)
        self.entry_threshold: float = self.params.get("entry_threshold", 0.0003)
        self.exit_threshold: float = self.params.get("exit_threshold", 0.0001)
        self.stop_loss_pct: float = self.params.get("stop_loss_pct", 0.05)
        self.take_profit_pct: float = self.params.get("take_profit_pct", 0.10)
        self.cascade_z_threshold: float = self.params.get("cascade_z_threshold", 2.5)
        self.whale_threshold: float = self.params.get("whale_threshold", 1_000_000)
        self.funding_rate_column: str = self.params.get("funding_rate_column", "funding_rate")
        self.open_interest_column: str = self.params.get("open_interest_column", "open_interest")
        self.symbol: str = self.params.get("symbol", "BTC")

    def required_columns(self) -> List[str]:
        base = ["close", "volume"]
        if self.mode == "funding_rate_arb":
            return base + [self.funding_rate_column]
        elif self.mode == "on_chain":
            return base + ["exchange_inflow", "exchange_outflow", "whale_tx_count"]
        elif self.mode == "dex_arb":
            return base + ["dex_price", "cex_price"]
        elif self.mode == "mev_aware":
            return base + ["solana_tip", "priority_fee"]
        else:
            return base

    def warmup_period(self) -> int:
        return self.lookback + 10

    # ----------------------------------------------------------------
    # Funding Rate Arbitrage
    # ----------------------------------------------------------------

    def compute_funding_rate_signal(
        self, data: pd.DataFrame
    ) -> Optional[Signal]:
        """Generate funding rate arbitrage signal.

        When funding rate is significantly positive, perpetual traders pay
        longs → short perp / long spot to collect funding.
        When funding rate is significantly negative, do the opposite.

        The annualized funding rate gives the expected carry:
            annualized_carry = funding_rate * 3 * 365  (3 funding periods/day on most exchanges)

        Reference:
            Alexander & Dakos (2020), Economic Modelling, 87, 117-129.

        Args:
            data: DataFrame with funding rate and price data.

        Returns:
            Signal if funding rate opportunity exists.
        """
        if self.funding_rate_column not in data.columns:
            return None

        funding_rate = data[self.funding_rate_column]
        current_fr = float(funding_rate.iloc[-1])

        # Compute rolling average funding rate
        avg_fr = float(funding_rate.iloc[-self.lookback:].mean()) if len(funding_rate) >= self.lookback else current_fr

        # Annualized carry
        annualized_carry = current_fr * 3 * 365  # 3 periods/day

        current_price = float(data["close"].iloc[-1])

        # Positive funding: short perp, long spot
        if current_fr > self.entry_threshold:
            confidence = min(current_fr / self.entry_threshold, 1.0)
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.SELL,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(current_price * (1 + self.stop_loss_pct), 6),
                take_profit=round(current_price * (1 - self.take_profit_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Funding rate arb: FR={current_fr:.6f} > {self.entry_threshold:.6f}, "
                    f"annualized_carry={annualized_carry:.4f}, short perp / long spot"
                ),
                evidence={
                    "funding_rate": round(current_fr, 8),
                    "avg_funding_rate": round(avg_fr, 8),
                    "annualized_carry": round(annualized_carry, 6),
                    "mode": "funding_rate_arb",
                },
                factors=["crypto", "funding_rate_arbitrage"],
            )

        # Negative funding: long perp, short spot
        if current_fr < -self.entry_threshold:
            confidence = min(abs(current_fr) / self.entry_threshold, 1.0)
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(current_price * (1 - self.stop_loss_pct), 6),
                take_profit=round(current_price * (1 + self.take_profit_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Funding rate arb: FR={current_fr:.6f} < -{self.entry_threshold:.6f}, "
                    f"annualized_carry={annualized_carry:.4f}, long perp / short spot"
                ),
                evidence={
                    "funding_rate": round(current_fr, 8),
                    "avg_funding_rate": round(avg_fr, 8),
                    "annualized_carry": round(annualized_carry, 6),
                    "mode": "funding_rate_arb",
                },
                factors=["crypto", "funding_rate_arbitrage"],
            )

        return None

    # ----------------------------------------------------------------
    # Liquidation Cascade Detection
    # ----------------------------------------------------------------

    def detect_liquidation_cascade(
        self, data: pd.DataFrame
    ) -> Optional[Signal]:
        """Detect liquidation cascades from price and volume patterns.

        A liquidation cascade is characterized by:
        1. Sharp price decline (or rise) exceeding normal volatility
        2. Volume spike well above average
        3. Rapid price recovery (mean reversion after cascade)

        We detect these using z-scores of returns and volume.

        Reference:
            Baur & Dimpfl (2018), Economics Letters, 173, 148-151.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Signal if cascade detected.
        """
        close = data["close"]
        volume = data["volume"]

        returns = close.pct_change().dropna()
        if len(returns) < self.lookback:
            return None

        current_return = float(returns.iloc[-1])
        current_volume = float(volume.iloc[-1])

        # Z-scores
        return_z = self.compute_zscore(returns, self.lookback)
        volume_z = self.compute_zscore(volume, self.lookback)

        current_return_z = float(return_z.iloc[-1]) if not np.isnan(return_z.iloc[-1]) else 0.0
        current_volume_z = float(volume_z.iloc[-1]) if not np.isnan(volume_z.iloc[-1]) else 0.0

        current_price = float(close.iloc[-1])

        # Cascade: extreme return + volume spike
        if abs(current_return_z) > self.cascade_z_threshold and current_volume_z > 1.5:
            if current_return_z < -self.cascade_z_threshold:
                # Downward cascade → buy the dip (mean reversion)
                confidence = min(abs(current_return_z) / self.cascade_z_threshold, 1.0) * 0.8
                return Signal(
                    symbol=self.symbol,
                    signal_type=SignalType.BUY,
                    confidence=round(confidence, 4),
                    price=round(current_price, 6),
                    stop_loss=round(current_price * (1 - self.stop_loss_pct), 6),
                    take_profit=round(current_price * (1 + self.take_profit_pct), 6),
                    source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"Liquidation cascade BUY: return_z={current_return_z:.2f}, "
                        f"volume_z={current_volume_z:.2f}"
                    ),
                    evidence={
                        "return_z": round(current_return_z, 4),
                        "volume_z": round(current_volume_z, 4),
                        "mode": "liquidation_cascade",
                    },
                    factors=["crypto", "liquidation_cascade"],
                )
            else:
                # Upward cascade → sell the spike
                confidence = min(abs(current_return_z) / self.cascade_z_threshold, 1.0) * 0.8
                return Signal(
                    symbol=self.symbol,
                    signal_type=SignalType.SELL,
                    confidence=round(confidence, 4),
                    price=round(current_price, 6),
                    stop_loss=round(current_price * (1 + self.stop_loss_pct), 6),
                    take_profit=round(current_price * (1 - self.take_profit_pct), 6),
                    source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"Liquidation cascade SELL: return_z={current_return_z:.2f}, "
                        f"volume_z={current_volume_z:.2f}"
                    ),
                    evidence={
                        "return_z": round(current_return_z, 4),
                        "volume_z": round(current_volume_z, 4),
                        "mode": "liquidation_cascade",
                    },
                    factors=["crypto", "liquidation_cascade"],
                )

        return None

    # ----------------------------------------------------------------
    # On-Chain Metrics Strategy
    # ----------------------------------------------------------------

    def compute_on_chain_signal(
        self, data: pd.DataFrame
    ) -> Optional[Signal]:
        """Generate signal based on on-chain metrics.

        Indicators:
        - Exchange net flow: large inflows = bearish, outflows = bullish
        - Whale transaction count: increased whale activity signals major moves
        - Exchange reserve changes

        Reference:
            Harvey, Ramachandran, & Santoro (2021). DeFi and the Future of Finance. Wiley.

        Args:
            data: DataFrame with on-chain columns.

        Returns:
            Signal if on-chain condition met.
        """
        if "exchange_inflow" not in data.columns or "exchange_outflow" not in data.columns:
            return None

        inflow = data["exchange_inflow"]
        outflow = data["exchange_outflow"]
        whale_tx = data.get("whale_tx_count", pd.Series(0, index=data.index))

        # Net flow
        net_flow = outflow - inflow  # Positive = outflows > inflows (bullish)
        current_net_flow = float(net_flow.iloc[-1])

        # Rolling average net flow
        avg_net_flow = float(net_flow.iloc[-self.lookback:].mean()) if len(net_flow) >= self.lookback else current_net_flow

        # Whale activity z-score
        whale_z = 0.0
        if whale_tx is not None and len(whale_tx) >= self.lookback:
            wzs = self.compute_zscore(whale_tx, self.lookback)
            if not np.isnan(wzs.iloc[-1]):
                whale_z = float(wzs.iloc[-1])

        current_price = float(data["close"].iloc[-1])

        # Net outflow + whale accumulation = bullish
        if current_net_flow > avg_net_flow * 2 and whale_z > 1.0:
            confidence = min(abs(current_net_flow) / (abs(avg_net_flow) + 1), 1.0)
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(current_price * (1 - self.stop_loss_pct), 6),
                take_profit=round(current_price * (1 + self.take_profit_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"On-chain BULLISH: net_flow={current_net_flow:.0f}, "
                    f"whale_z={whale_z:.2f}"
                ),
                evidence={
                    "net_flow": round(current_net_flow, 2),
                    "avg_net_flow": round(avg_net_flow, 2),
                    "whale_z": round(whale_z, 4),
                    "mode": "on_chain",
                },
                factors=["crypto", "on_chain_metrics"],
            )

        # Net inflow + whale distribution = bearish
        if current_net_flow < avg_net_flow * 0.5 and whale_z > 1.0:
            confidence = min(abs(current_net_flow) / (abs(avg_net_flow) + 1), 1.0)
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.SELL,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(current_price * (1 + self.stop_loss_pct), 6),
                take_profit=round(current_price * (1 - self.take_profit_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"On-chain BEARISH: net_flow={current_net_flow:.0f}, "
                    f"whale_z={whale_z:.2f}"
                ),
                evidence={
                    "net_flow": round(current_net_flow, 2),
                    "avg_net_flow": round(avg_net_flow, 2),
                    "whale_z": round(whale_z, 4),
                    "mode": "on_chain",
                },
                factors=["crypto", "on_chain_metrics"],
            )

        return None

    # ----------------------------------------------------------------
    # DEX Arbitrage
    # ----------------------------------------------------------------

    def detect_dex_arb(
        self, data: pd.DataFrame
    ) -> Optional[Signal]:
        """Detect DEX-CEX arbitrage opportunities.

        Compares DEX and CEX prices for the same asset.
        If DEX price < CEX price: buy on DEX, sell on CEX.
        If DEX price > CEX price: sell on DEX, buy on CEX.

        Reference:
            Daian et al. (2020). "Flash Boys 2.0." IEEE S&P.

        Args:
            data: DataFrame with 'dex_price' and 'cex_price' columns.

        Returns:
            Signal if arb opportunity exists.
        """
        if "dex_price" not in data.columns or "cex_price" not in data.columns:
            return None

        dex_price = float(data["dex_price"].iloc[-1])
        cex_price = float(data["cex_price"].iloc[-1])

        if dex_price <= 0 or cex_price <= 0:
            return None

        # Price discrepancy as fraction
        spread = (dex_price - cex_price) / cex_price

        current_price = float(data["close"].iloc[-1])

        # Account for gas/fees (~0.1% on each side)
        fee_estimate = 0.002  # 0.2% total
        net_spread = abs(spread) - fee_estimate

        if net_spread > self.entry_threshold:
            confidence = min(net_spread / self.entry_threshold, 1.0)
            if spread > 0:
                # DEX overpriced: sell DEX, buy CEX
                signal_type = SignalType.SELL
                direction = "sell DEX / buy CEX"
            else:
                # DEX underpriced: buy DEX, sell CEX
                signal_type = SignalType.BUY
                direction = "buy DEX / sell CEX"

            return Signal(
                symbol=self.symbol,
                signal_type=signal_type,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"DEX arb: {direction}, spread={spread:.4f}, "
                    f"fee_adj_spread={net_spread:.4f}"
                ),
                evidence={
                    "dex_price": round(dex_price, 6),
                    "cex_price": round(cex_price, 6),
                    "spread": round(spread, 6),
                    "fee_adjusted_spread": round(net_spread, 6),
                    "mode": "dex_arb",
                },
                factors=["crypto", "dex_arbitrage"],
            )

        return None

    # ----------------------------------------------------------------
    # MEV-Aware Execution (Solana)
    # ----------------------------------------------------------------

    def compute_mev_signal(
        self, data: pd.DataFrame
    ) -> Optional[Signal]:
        """Generate MEV-aware execution signal for Solana.

        Analyzes priority fees and tips to determine optimal
        execution timing and avoid MEV extraction.

        Key metrics:
        - Current tip level (higher = more MEV competition)
        - Priority fee percentile (avoid high-fee environments)
        - Compute unit price trends

        Reference:
            Daian et al. (2020). "Flash Boys 2.0." IEEE S&P.

        Args:
            data: DataFrame with Solana-specific columns.

        Returns:
            Signal with MEV-aware execution recommendation.
        """
        if "solana_tip" not in data.columns or "priority_fee" not in data.columns:
            return None

        tips = data["solana_tip"]
        fees = data["priority_fee"]

        current_tip = float(tips.iloc[-1])
        current_fee = float(fees.iloc[-1])

        # Z-score of current MEV environment
        tip_z = 0.0
        fee_z = 0.0
        if len(tips) >= self.lookback:
            tip_zs = self.compute_zscore(tips, self.lookback)
            fee_zs = self.compute_zscore(fees, self.lookback)
            if not np.isnan(tip_zs.iloc[-1]):
                tip_z = float(tip_zs.iloc[-1])
            if not np.isnan(fee_zs.iloc[-1]):
                fee_z = float(fee_zs.iloc[-1])

        current_price = float(data["close"].iloc[-1])

        # High MEV environment: delay execution
        if tip_z > 2.0 or fee_z > 2.0:
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.8,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"MEV-aware HOLD: high MEV environment, "
                    f"tip_z={tip_z:.2f}, fee_z={fee_z:.2f}"
                ),
                evidence={
                    "tip_z": round(tip_z, 4),
                    "fee_z": round(fee_z, 4),
                    "current_tip": round(current_tip, 6),
                    "current_fee": round(current_fee, 6),
                    "mode": "mev_aware",
                },
                factors=["crypto", "mev_aware", "solana"],
            )

        # Low MEV environment: safe to execute
        if tip_z < -0.5 and fee_z < -0.5:
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=0.6,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"MEV-aware execute: low MEV environment, "
                    f"tip_z={tip_z:.2f}, fee_z={fee_z:.2f}"
                ),
                evidence={
                    "tip_z": round(tip_z, 4),
                    "fee_z": round(fee_z, 4),
                    "current_tip": round(current_tip, 6),
                    "current_fee": round(current_fee, 6),
                    "mode": "mev_aware",
                },
                factors=["crypto", "mev_aware", "solana"],
            )

        return None

    # ----------------------------------------------------------------
    # Main Signal Generator
    # ----------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate crypto-specific signal based on selected mode.

        Dispatches to the appropriate sub-strategy based on self.mode.

        Args:
            data: DataFrame with required columns for the mode.

        Returns:
            Signal if condition met, None otherwise.
        """
        if not self.validate_data(data):
            return None

        if self.mode == "funding_rate_arb":
            return self.compute_funding_rate_signal(data)
        elif self.mode == "liquidation_cascade":
            return self.detect_liquidation_cascade(data)
        elif self.mode == "on_chain":
            return self.compute_on_chain_signal(data)
        elif self.mode == "dex_arb":
            return self.detect_dex_arb(data)
        elif self.mode == "mev_aware":
            return self.compute_mev_signal(data)
        else:
            return self.compute_funding_rate_signal(data)
