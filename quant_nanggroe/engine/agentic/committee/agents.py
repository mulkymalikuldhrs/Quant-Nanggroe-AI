"""Committee Agents — Bull, Bear, Macro, Risk, Execution."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger("QNA.Committee.Agents")


@dataclass
class AgentVote:
    agent_name: str
    bias: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0-1.0
    evidence: list[str] = field(default_factory=list)
    reasoning: str = ""


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def analyze(self, symbol: str, df: Any, **kwargs) -> AgentVote:
        ...


class BullAnalyst(BaseAgent):
    """Looks for reasons TO BUY. Aggressive, momentum-focused."""
    name = "bull_analyst"

    def analyze(self, symbol: str, df: Any, **kwargs) -> AgentVote:
        if df is None or len(df) < 20:
            return AgentVote(self.name, "neutral", 0.0, ["insufficient data"])

        evidence = []
        score = 0.0
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        # RSI oversold
        rsi = self._rsi(close, 14)
        if rsi < 30:
            evidence.append(f"RSI oversold at {rsi:.1f}")
            score += 0.3
        elif rsi < 40:
            evidence.append(f"RSI approaching oversold at {rsi:.1f}")
            score += 0.15

        # MACD cross up
        macd_line, signal_line = self._macd(close)
        if macd_line > signal_line and macd_line[-2] <= signal_line[-2]:
            evidence.append("MACD bullish crossover")
            score += 0.25

        # Price above EMA 20
        ema20 = self._ema(close, 20)
        if close[-1] > ema20[-1]:
            evidence.append(f"Price above EMA20 ({close[-1]:.5f} > {ema20[-1]:.5f})")
            score += 0.15

        # Volume spike
        vol = df["volume"].values if "volume" in df.columns else None
        if vol is not None and len(vol) > 20:
            avg_vol = np.mean(vol[-20:])
            if vol[-1] > avg_vol * 1.5:
                evidence.append(f"Volume spike: {vol[-1]/avg_vol:.1f}x average")
                score += 0.15

        # Higher low pattern
        if len(low) >= 5:
            recent_lows = low[-5:]
            if all(recent_lows[i] <= recent_lows[i+1] for i in range(len(recent_lows)-1)):
                evidence.append("Higher low pattern (5 bars)")
                score += 0.15

        confidence = min(1.0, score)
        bias = "bullish" if confidence >= 0.3 else "neutral"
        return AgentVote(self.name, bias, confidence, evidence,
                         f"Found {len(evidence)} bullish signals")

    @staticmethod
    def _rsi(close, period=14):
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _macd(close, fast=12, slow=26, signal=9):
        def ema(data, span):
            alpha = 2 / (span + 1)
            result = np.zeros_like(data, dtype=float)
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            return result
        ema_fast = ema(close, fast)
        ema_slow = ema(close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = ema(macd_line, signal)
        return macd_line, signal_line

    @staticmethod
    def _ema(data, period):
        alpha = 2 / (period + 1)
        result = np.zeros_like(data, dtype=float)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        return result


class BearAnalyst(BaseAgent):
    """Looks for reasons TO SELL. Skeptical, resistance-focused."""
    name = "bear_analyst"

    def analyze(self, symbol: str, df: Any, **kwargs) -> AgentVote:
        if df is None or len(df) < 20:
            return AgentVote(self.name, "neutral", 0.0, ["insufficient data"])

        evidence = []
        score = 0.0
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        # RSI overbought
        rsi = BullAnalyst._rsi(close, 14)
        if rsi > 70:
            evidence.append(f"RSI overbought at {rsi:.1f}")
            score += 0.3
        elif rsi > 60:
            evidence.append(f"RSI approaching overbought at {rsi:.1f}")
            score += 0.15

        # MACD cross down
        macd_line, signal_line = BullAnalyst._macd(close)
        if macd_line < signal_line and macd_line[-2] >= signal_line[-2]:
            evidence.append("MACD bearish crossover")
            score += 0.25

        # Price below EMA 20
        ema20 = BullAnalyst._ema(close, 20)
        if close[-1] < ema20[-1]:
            evidence.append(f"Price below EMA20 ({close[-1]:.5f} < {ema20[-1]:.5f})")
            score += 0.15

        # Volume distribution
        vol = df["volume"].values if "volume" in df.columns else None
        if vol is not None and len(vol) > 20:
            avg_vol = np.mean(vol[-20:])
            if vol[-1] > avg_vol * 1.5 and close[-1] < close[-2]:
                evidence.append(f"Selling volume spike: {vol[-1]/avg_vol:.1f}x")
                score += 0.15

        # Lower high pattern
        if len(high) >= 5:
            recent_highs = high[-5:]
            if all(recent_highs[i] >= recent_highs[i+1] for i in range(len(recent_highs)-1)):
                evidence.append("Lower high pattern (5 bars)")
                score += 0.15

        confidence = min(1.0, score)
        bias = "bearish" if confidence >= 0.3 else "neutral"
        return AgentVote(self.name, bias, confidence, evidence,
                         f"Found {len(evidence)} bearish signals")


class MacroAnalyst(BaseAgent):
    """Big picture: regime, correlations, session timing."""
    name = "macro_analyst"

    def analyze(self, symbol: str, df: Any, **kwargs) -> AgentVote:
        evidence = []
        score = 0.0

        regime = kwargs.get("regime", "unknown")
        timeframe = kwargs.get("timeframe", "M15")

        # Regime alignment
        if regime in ("trending", "momentum"):
            # Trending markets favor momentum strategies
            close = df["close"].values if df is not None and len(df) > 0 else []
            if len(close) > 20:
                sma20 = np.mean(close[-20:])
                if close[-1] > sma20:
                    evidence.append(f"Trending regime + price above SMA20 → bullish alignment")
                    score += 0.2
                else:
                    evidence.append(f"Trending regime + price below SMA20 → bearish alignment")
                    score += 0.2
        elif regime in ("ranging", "mean_reversion"):
            evidence.append(f"Range-bound regime → mean reversion bias")
            score += 0.1

        # Session timing (forex)
        if "XAU" not in symbol and "BTC" not in symbol:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            hour = now.hour
            if 7 <= hour <= 16:  # London + NY overlap
                evidence.append(f"Active session (UTC {hour}:00) → higher liquidity")
                score += 0.1
            elif hour >= 22 or hour <= 5:
                evidence.append(f"Asian session (UTC {hour}:00) → lower liquidity")
                score -= 0.1

        # Volatility regime
        if df is not None and len(df) > 14:
            close = df["close"].values
            returns = np.diff(np.log(close[-15:]))
            vol_14 = np.std(returns) * np.sqrt(252)
            if vol_14 > 0.20:
                evidence.append(f"High annualized vol: {vol_14:.1%} → wider stops needed")
                score += 0.05
            elif vol_14 < 0.05:
                evidence.append(f"Low annualized vol: {vol_14:.1%} → tight range")
                score -= 0.05

        confidence = min(1.0, max(0.0, abs(score)))
        bias = "bullish" if score > 0.1 else ("bearish" if score < -0.1 else "neutral")
        return AgentVote(self.name, bias, confidence, evidence,
                         f"Macro score: {score:+.2f}")


class RiskOfficer(BaseAgent):
    """ABSOLUTE VETO POWER. Checks portfolio risk, drawdown, correlation."""
    name = "risk_officer"

    def analyze(self, symbol: str, df: Any, **kwargs) -> AgentVote:
        evidence = []
        approved = True

        portfolio_state = kwargs.get("portfolio_state", {})
        current_equity = portfolio_state.get("equity", 0)
        daily_pnl = portfolio_state.get("daily_pnl", 0)
        open_positions = portfolio_state.get("open_positions", 0)
        max_drawdown = portfolio_state.get("max_drawdown", 0)

        # Daily loss limit (1%)
        if current_equity > 0 and daily_pnl < 0:
            daily_loss_pct = abs(daily_pnl) / current_equity
            if daily_loss_pct >= 0.01:
                evidence.append(f"Daily loss limit hit: {daily_loss_pct:.2%} >= 1%")
                approved = False

        # Max drawdown (3%)
        if max_drawdown >= 0.03:
            evidence.append(f"Max drawdown breached: {max_drawdown:.2%} >= 3%")
            approved = False

        # Max open positions (5)
        if open_positions >= 5:
            evidence.append(f"Max positions reached: {open_positions} >= 5")
            approved = False

        # Position sizing sanity
        lot_size = kwargs.get("lot_size", 0.01)
        if lot_size > 1.0:
            evidence.append(f"Lot size too large: {lot_size} > 1.0")
            approved = False

        confidence = 1.0 if approved else 0.0
        bias = "neutral" if approved else "bearish"
        return AgentVote(self.name, bias, confidence, evidence,
                         "APPROVED" if approved else "VETOED")


class ExecutionAgent(BaseAgent):
    """Precision entry/exit logic. Runs after approval."""
    name = "execution_agent"

    def analyze(self, symbol: str, df: Any, **kwargs) -> AgentVote:
        # Execution agent doesn't vote — it computes entry/exit
        entry = kwargs.get("entry_price", 0.0)
        atr = kwargs.get("atr", 0.0)
        side = kwargs.get("side", "buy")
        timeframe = kwargs.get("timeframe", "M15")

        from quant_nanggroe.engine.risk.trading_profile import detect_profile, compute_sl_tp
        profile = detect_profile(timeframe)
        sltp = compute_sl_tp(side=side, entry_price=entry, atr_value=atr, timeframe=timeframe)

        return AgentVote(
            self.name, "neutral", 1.0,
            [f"SL={sltp['sl']:.5f}", f"TP={sltp['tp']:.5f}",
             f"profile={profile.name}", f"R:R={profile.rr_target}"],
            f"Execution ready: {side} @ {entry:.5f}")
