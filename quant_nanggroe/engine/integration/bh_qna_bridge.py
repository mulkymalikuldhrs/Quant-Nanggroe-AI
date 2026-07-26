"""
BH→QNA Cross-Module Bridge
===========================

Routes data between BH (Backtesting/Historical) and QNA (Quant Nanggroe AI)
engine modules. Provides unified API for market data retrieval, analysis
result exchange, and cross-module error handling with fallback logic.

Usage::

    bridge = BHQnaBridge()
    market_data = bridge.get_market_data_from_bh("SPY", "2024-01-01", "2024-12-31")
    analysis = bridge.run_qna_analysis(market_data)
    bridge.send_results_to_bh(analysis)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.core.edge_case_handler import (
    defensive_wrapper,
    safe_divide,
    validate_dataframe,
    validate_price_dataframe,
)
from quant_nanggroe.exceptions import EngineError

logger = logging.getLogger(__name__)


class ModuleSide(str, Enum):
    """Which side of the bridge a component belongs to."""
    BH = "backtesting_historical"
    QNA = "quant_nanggroe_ai"


class BridgeStatus(str, Enum):
    """Status of a bridge operation."""
    SUCCESS = "success"
    FALLBACK = "fallback"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BridgeResult:
    """Result of a cross-module bridge operation."""
    status: BridgeStatus
    data: Any = None
    source: ModuleSide = ModuleSide.BH
    target: ModuleSide = ModuleSide.QNA
    latency_ms: float = 0.0
    error: Optional[str] = None
    fallback_used: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "source": self.source.value,
            "target": self.target.value,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "fallback_used": self.fallback_used,
            "timestamp": self.timestamp,
            "data_type": type(self.data).__name__ if self.data is not None else None,
        }


@dataclass
class BridgeConfig:
    """Configuration for the BH↔QNA bridge."""
    request_timeout: float = 30.0
    max_retries: int = 2
    retry_delay: float = 1.0
    enable_fallback: bool = True
    log_latency: bool = True
    validate_inputs: bool = True
    validate_outputs: bool = True


class BHQnaBridge:
    """Bridge that routes data between BH and QNA engine modules.

    Responsibilities:
    - Fetch market data from BH backtest infrastructure and convert for QNA
    - Run QNA analysis and package results for BH consumption
    - Handle errors gracefully with configurable fallback logic
    - Track latency and operation metrics
    """

    def __init__(self, config: Optional[BridgeConfig] = None) -> None:
        self.config = config or BridgeConfig()
        self._metrics: Dict[str, Any] = {
            "total_calls": 0,
            "success_count": 0,
            "fallback_count": 0,
            "failure_count": 0,
            "avg_latency_ms": 0.0,
        }
        self._latencies: List[float] = []

    # ── Market Data: BH → QNA ────────────────────────────────────────

    def get_market_data_from_bh(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        fields: Optional[List[str]] = None,
    ) -> BridgeResult:
        """Fetch market data from BH backtest infrastructure for QNA analysis.

        Args:
            symbol: Ticker symbol (e.g. "SPY", "BTC-USD").
            start_date: Start date string (ISO format).
            end_date: End date string (ISO format).
            interval: Data interval (e.g. "1d", "1h", "5m").
            fields: Optional list of fields to include.

        Returns:
            BridgeResult with market data DataFrame.
        """
        start_time = time.monotonic()
        fields = fields or ["open", "high", "low", "close", "volume"]

        try:
            df = self._fetch_bh_market_data(symbol, start_date, end_date, interval)

            if self.config.validate_inputs:
                df = validate_price_dataframe(df, symbol=symbol, min_rows=2)

            df = self._align_columns(df, fields)

            latency = (time.monotonic() - start_time) * 1000
            self._record_success("get_market_data_from_bh", latency)

            return BridgeResult(
                status=BridgeStatus.SUCCESS,
                data=df,
                source=ModuleSide.BH,
                target=ModuleSide.QNA,
                latency_ms=latency,
            )

        except Exception as exc:
            latency = (time.monotonic() - start_time) * 1000
            logger.error(f"BH→QNA market data fetch failed for {symbol}: {exc}")

            self._record_failure("get_market_data_from_bh", latency)
            return BridgeResult(
                status=BridgeStatus.FAILED,
                source=ModuleSide.BH,
                target=ModuleSide.QNA,
                latency_ms=latency,
                error=str(exc),
            )

    def _fetch_bh_market_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> pd.DataFrame:
        """Fetch data from BH backtest infrastructure. Fail-closed on loader failure."""
        try:
            from quant_nanggroe.engine.backtest.loaders import CSVLoader
            loader = CSVLoader()
            return loader.load(symbol, start_date, end_date)
        except Exception as exc:
            raise RuntimeError(
                f"BH market data loader failed for {symbol}: {exc}. "
                "Cannot generate synthetic data. Failing closed."
            ) from exc

    @staticmethod
    def _align_columns(df: pd.DataFrame, fields: List[str]) -> pd.DataFrame:
        """Ensure DataFrame has the requested columns."""
        available = [f for f in fields if f in df.columns]
        if not available:
            logger.warning(f"None of requested fields {fields} found in DataFrame")
            return df
        return df[available]

    # ── QNA Analysis: QNA Internal ───────────────────────────────────

    def run_qna_analysis(
        self,
        market_data: pd.DataFrame,
        analysis_type: str = "full",
        params: Optional[Dict[str, Any]] = None,
    ) -> BridgeResult:
        """Run QNA analysis on market data.

        Args:
            market_data: OHLCV DataFrame from BH.
            analysis_type: Type of analysis ("full", "risk", "kelly", "signal").
            params: Optional analysis parameters.

        Returns:
            BridgeResult with analysis results dict.
        """
        start_time = time.monotonic()
        params = params or {}

        try:
            if self.config.validate_inputs:
                validate_dataframe(market_data, min_rows=2, name="qna_input")

            results = self._execute_qna_analysis(market_data, analysis_type, params)

            latency = (time.monotonic() - start_time) * 1000
            self._record_success("run_qna_analysis", latency)

            return BridgeResult(
                status=BridgeStatus.SUCCESS,
                data=results,
                source=ModuleSide.QNA,
                target=ModuleSide.QNA,
                latency_ms=latency,
            )

        except Exception as exc:
            latency = (time.monotonic() - start_time) * 1000
            logger.error(f"QNA analysis failed ({analysis_type}): {exc}")

            if self.config.enable_fallback:
                fallback = self._fallback_analysis(market_data, analysis_type)
                if fallback is not None:
                    self._record_fallback("run_qna_analysis", latency)
                    return BridgeResult(
                        status=BridgeStatus.FALLBACK,
                        data=fallback,
                        source=ModuleSide.QNA,
                        target=ModuleSide.QNA,
                        latency_ms=latency,
                        fallback_used=True,
                    )

            self._record_failure("run_qna_analysis", latency)
            return BridgeResult(
                status=BridgeStatus.FAILED,
                source=ModuleSide.QNA,
                target=ModuleSide.QNA,
                latency_ms=latency,
                error=str(exc),
            )

    @defensive_wrapper(fallback_value=None, log_errors=True)
    def _execute_qna_analysis(
        self,
        data: pd.DataFrame,
        analysis_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the actual QNA analysis logic."""
        close = data["close"] if "close" in data.columns else data.iloc[:, -1]
        returns = close.pct_change().dropna()

        results: Dict[str, Any] = {
            "symbol": params.get("symbol", "UNKNOWN"),
            "analysis_type": analysis_type,
            "timestamp": datetime.now().isoformat(),
            "data_points": len(data),
        }

        if analysis_type in ("full", "risk"):
            results["risk"] = self._compute_risk_metrics(returns)

        if analysis_type in ("full", "kelly"):
            results["kelly"] = self._compute_kelly_params(returns)

        if analysis_type in ("full", "signal"):
            results["signal"] = self._compute_signal(data, returns)

        results["returns_summary"] = {
            "mean": float(returns.mean()),
            "std": float(returns.std()),
            "min": float(returns.min()),
            "max": float(returns.max()),
        }

        return results

    @staticmethod
    def _compute_risk_metrics(returns: pd.Series) -> Dict[str, float]:
        """Compute risk metrics from returns."""
        if len(returns) < 2:
            return {"var_95": 0.0, "cvar_95": 0.0, "volatility": 0.0}

        sorted_ret = np.sort(returns.values)
        n = len(sorted_ret)
        var_95 = float(np.percentile(sorted_ret, 5))
        cvar_95 = float(np.mean(sorted_ret[:max(1, int(0.05 * n))]))
        vol = float(returns.std() * np.sqrt(252))

        return {
            "var_95": var_95,
            "cvar_95": cvar_95,
            "volatility": vol,
        }

    @staticmethod
    def _compute_kelly_params(returns: pd.Series) -> Dict[str, float]:
        """Compute Kelly parameters from returns."""
        if len(returns) < 10:
            return {"win_rate": 0.5, "avg_win": 0.0, "avg_loss": 1.0, "kelly_f": 0.0}

        wins = returns[returns > 0]
        losses = returns[returns < 0]

        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.5
        avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
        avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 1.0

        b = avg_win / max(avg_loss, 1e-10)
        q = 1 - win_rate
        kelly_f = safe_divide(b * win_rate - q, b, default=0.0)
        kelly_f = max(0.0, min(1.0, kelly_f))

        return {
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "kelly_f": kelly_f,
        }

    @staticmethod
    def _compute_signal(
        data: pd.DataFrame, returns: pd.Series
    ) -> Dict[str, Any]:
        """Compute a basic trading signal."""
        if len(data) < 20:
            return {"direction": "HOLD", "confidence": 0.0}

        close = data["close"] if "close" in data.columns else data.iloc[:, -1]
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma_20
        current = float(close.iloc[-1])

        if current > sma_20 and sma_20 > sma_50:
            direction = "BUY"
            confidence = min(1.0, (current - sma_50) / max(sma_50, 1e-10))
        elif current < sma_20 and sma_20 < sma_50:
            direction = "SELL"
            confidence = min(1.0, (sma_50 - current) / max(sma_50, 1e-10))
        else:
            direction = "HOLD"
            confidence = 0.0

        return {
            "direction": direction,
            "confidence": max(0.0, min(1.0, confidence)),
            "current_price": current,
            "sma_20": float(sma_20),
            "sma_50": float(sma_50),
        }

    def _fallback_analysis(
        self, data: pd.DataFrame, analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """Provide minimal fallback analysis when primary fails."""
        try:
            close = data["close"] if "close" in data.columns else data.iloc[:, -1]
            current = float(close.iloc[-1])
            return {
                "analysis_type": analysis_type,
                "fallback": True,
                "current_price": current,
                "signal": {"direction": "HOLD", "confidence": 0.0},
                "risk": {"var_95": 0.0, "cvar_95": 0.0, "volatility": 0.0},
                "kelly": {"kelly_f": 0.0},
            }
        except Exception:
            return None

    # ── Results: QNA → BH ────────────────────────────────────────────

    def send_results_to_bh(
        self,
        analysis_result: BridgeResult,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BridgeResult:
        """Send QNA analysis results back to BH for consumption.

        Packages the QNA results in a format suitable for backtest
        strategy consumption.

        Args:
            analysis_result: BridgeResult from QNA analysis.
            metadata: Optional metadata to attach.

        Returns:
            BridgeResult with packaged results for BH.
        """
        start_time = time.monotonic()
        metadata = metadata or {}

        try:
            if analysis_result.status == BridgeStatus.FAILED:
                raise EngineError(f"Cannot forward failed analysis: {analysis_result.error}")

            bh_payload = self._package_for_bh(analysis_result.data, metadata)

            latency = (time.monotonic() - start_time) * 1000
            self._record_success("send_results_to_bh", latency)

            return BridgeResult(
                status=BridgeStatus.SUCCESS,
                data=bh_payload,
                source=ModuleSide.QNA,
                target=ModuleSide.BH,
                latency_ms=latency,
            )

        except Exception as exc:
            latency = (time.monotonic() - start_time) * 1000
            logger.error(f"Failed to send results to BH: {exc}")
            self._record_failure("send_results_to_bh", latency)

            return BridgeResult(
                status=BridgeStatus.FAILED,
                source=ModuleSide.QNA,
                target=ModuleSide.BH,
                latency_ms=latency,
                error=str(exc),
            )

    @staticmethod
    def _package_for_bh(
        analysis_data: Any, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Package QNA analysis results for BH consumption."""
        if not isinstance(analysis_data, dict):
            return {
                "bh_format": True,
                "raw_data": analysis_data,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat(),
            }

        bh_payload = {
            "bh_format": True,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
        }

        if "signal" in analysis_data:
            sig = analysis_data["signal"]
            direction = sig.get("direction", "HOLD")
            confidence = sig.get("confidence", 0.0)

            bh_payload["signal_strength"] = confidence
            if direction == "BUY":
                bh_payload["target_weight"] = min(confidence, 0.1)
            elif direction == "SELL":
                bh_payload["target_weight"] = -min(confidence, 0.1)
            else:
                bh_payload["target_weight"] = 0.0

        if "kelly" in analysis_data:
            bh_payload["kelly_fraction"] = analysis_data["kelly"].get("kelly_f", 0.0)

        if "risk" in analysis_data:
            bh_payload["risk_metrics"] = analysis_data["risk"]

        bh_payload["analysis_summary"] = {
            k: v for k, v in analysis_data.items()
            if k not in ("signal", "kelly", "risk", "returns_summary")
        }

        return bh_payload

    # ── Full Pipeline ─────────────────────────────────────────────────

    def run_full_pipeline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        analysis_type: str = "full",
        params: Optional[Dict[str, Any]] = None,
    ) -> BridgeResult:
        """Run the full BH→QNA→BH pipeline.

        1. Fetch market data from BH
        2. Run QNA analysis
        3. Package results for BH

        Args:
            symbol: Ticker symbol.
            start_date: Start date (ISO format).
            end_date: End date (ISO format).
            interval: Data interval.
            analysis_type: QNA analysis type.
            params: Optional parameters.

        Returns:
            BridgeResult with full pipeline output.
        """
        start_time = time.monotonic()

        # Step 1: BH → QNA data fetch
        data_result = self.get_market_data_from_bh(symbol, start_date, end_date, interval)
        if data_result.status == BridgeStatus.FAILED:
            return BridgeResult(
                status=BridgeStatus.FAILED,
                source=ModuleSide.BH,
                target=ModuleSide.BH,
                latency_ms=(time.monotonic() - start_time) * 1000,
                error=f"Data fetch failed: {data_result.error}",
            )

        # Step 2: QNA analysis
        params = params or {"symbol": symbol}
        analysis_result = self.run_qna_analysis(
            data_result.data, analysis_type=analysis_type, params=params
        )
        if analysis_result.status == BridgeStatus.FAILED:
            return BridgeResult(
                status=BridgeStatus.FAILED,
                source=ModuleSide.QNA,
                target=ModuleSide.BH,
                latency_ms=(time.monotonic() - start_time) * 1000,
                error=f"Analysis failed: {analysis_result.error}",
            )

        # Step 3: QNA → BH packaging
        bh_result = self.send_results_to_bh(analysis_result)
        total_latency = (time.monotonic() - start_time) * 1000

        bh_result.latency_ms = total_latency
        bh_result.data["pipeline"] = {
            "data_fetch_ms": round(data_result.latency_ms, 2),
            "analysis_ms": round(analysis_result.latency_ms, 2),
            "packaging_ms": round(bh_result.latency_ms, 2),
            "total_ms": round(total_latency, 2),
            "data_fallback": data_result.fallback_used,
            "analysis_fallback": analysis_result.fallback_used,
        }

        return bh_result

    # ── Metrics ───────────────────────────────────────────────────────

    def _record_success(self, operation: str, latency_ms: float) -> None:
        self._metrics["total_calls"] += 1
        self._metrics["success_count"] += 1
        self._latencies.append(latency_ms)
        self._update_avg_latency()

    def _record_fallback(self, operation: str, latency_ms: float) -> None:
        self._metrics["total_calls"] += 1
        self._metrics["fallback_count"] += 1
        self._latencies.append(latency_ms)
        self._update_avg_latency()

    def _record_failure(self, operation: str, latency_ms: float) -> None:
        self._metrics["total_calls"] += 1
        self._metrics["failure_count"] += 1
        self._latencies.append(latency_ms)
        self._update_avg_latency()

    def _update_avg_latency(self) -> None:
        if self._latencies:
            self._metrics["avg_latency_ms"] = sum(self._latencies) / len(self._latencies)

    def get_metrics(self) -> Dict[str, Any]:
        """Return bridge operation metrics."""
        return dict(self._metrics)
