"""Core signal providers — built-in strategies that run locally or call external ecosystems.

Each provider now accepts an optional ctx: CausalContext parameter for macro
bias adjustment. When ctx is provided, apply_causal_bias() uses ctx.bias_for()
instead of the deprecated QNA_CAUSAL_BIAS_* env var protocol.

If the causal bias strongly contradicts a provider's signal, confidence is
reduced. If it aligns, confidence is boosted.
"""

import os
import subprocess
import sys
import warnings
from datetime import datetime
from typing import Optional

from quant_nanggroe.engine.causal.models import CausalContext
from quant_nanggroe.hedge_fund.utils.config import SRC, log
from quant_nanggroe.hedge_fund.utils.data import get_historical_mt5

# ──────────────────────────────────────────────────────────────────────
#  Causal bias lookup — symbol → CME futures → env var
# ──────────────────────────────────────────────────────────────────────

# Mapping: trading symbol → primary CME futures symbol for causal bias
SYMBOL_TO_FUTURES = {
    # Forex
    "EURUSD": "6E1!",
    "GBPUSD": "6B1!",
    "USDJPY": "6J1!",
    "AUDUSD": "6A1!",
    "USDCAD": "6C1!",
    "USDCHF": "6S1!",
    "NZDUSD": "6N1!",
    # Metals
    "XAUUSD": "GC1!",
    "XAGUSD": "SI1!",
    # Indices
    "US30": "YM1!",
    "US500": "ES1!",
    "NAS100": "NQ1!",
    "US100": "NQ1!",
    "SPX": "ES1!",
    "DJI": "YM1!",
    # Crypto (CME futures)
    "BTCUSD": "BTC1!",
    "ETHUSD": "ETH1!",
    # Bonds
    "US10Y": "ZN1!",
    "US30Y": "ZB1!",
}


def causal_bias_score(symbol: str) -> float:
    """Read the causal macro bias for a trading symbol from QNA_CAUSAL_BIAS_* env vars.

    .. deprecated::
       Use CausalContext.bias_for(symbol) instead.

    Returns a float in [-1.0, 1.0]:
        > 0.3  → bullish macro context for this symbol
        < -0.3 → bearish macro context for this symbol
        0.0    → no macro context available
    """
    warnings.warn(
        "causal_bias_score() is deprecated. Use CausalContext.bias_for() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    futures = SYMBOL_TO_FUTURES.get(symbol.upper(), symbol.upper())
    raw = os.environ.get(f"QNA_CAUSAL_BIAS_{futures}", "")
    if not raw:
        raw = os.environ.get(f"QNA_CAUSAL_BIAS_{symbol.upper()}", "")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def apply_causal_bias(signal: dict, symbol: str, ctx: Optional[CausalContext] = None) -> dict:
    """Apply causal macro bias to a provider's signal result.

    Adjusts confidence based on macro context:
      - Macro bullish (+bias) + signal buy   → confidence boosted
      - Macro bearish (-bias) + signal sell  → confidence boosted
      - Macro bullish (+bias) + signal sell  → confidence reduced (may flip to neutral)
      - Macro bearish (-bias) + signal buy   → confidence reduced (may flip to neutral)
      - Bias neutral / no context            → no change

    Args:
        signal: Provider result dict with 'bias' and 'confidence' keys.
        symbol: Trading symbol for bias lookup.
        ctx: Optional CausalContext. If provided, uses ctx.bias_for()
             instead of QNA_CAUSAL_BIAS_* env vars.

    Returns:
        Updated signal dict with adjusted confidence/neutral.
    """
    bias = signal.get("bias", "neutral")
    confidence = signal.get("confidence", 0.0)
    if bias == "neutral" or confidence <= 0:
        return signal

    cb = ctx.bias_for(symbol) if ctx is not None else causal_bias_score(symbol)
    if cb == 0.0:
        return signal  # no macro context — pass through

    direction = 1 if bias == "buy" else -1
    alignment = direction * cb  # >0 = aligned, <0 = contradictory

    if alignment > 0.3:
        # Macro context aligns — boost confidence
        signal["confidence"] = min(confidence * (1.0 + abs(cb) * 0.3), 1.0)
        signal["_causal_bias"] = cb
        signal["_causal_effect"] = "boost"
        log.info("  %s: causal bias %.2f BOOSTS %s (conf %.2f → %.2f)",
                 symbol, cb, bias, confidence, signal["confidence"])
    elif alignment < -0.3:
        # Macro context contradicts — reduce confidence or flip to neutral
        penalty = abs(alignment)
        if penalty > 0.6:
            # Strong contradiction — override to neutral
            signal["bias"] = "neutral"
            signal["confidence"] = 0.0
            signal["_causal_bias"] = cb
            signal["_causal_effect"] = "blocked"
            log.info("  %s: causal bias %.2f BLOCKS %s — overridden to neutral", symbol, cb, bias)
        else:
            # Mild contradiction — reduce confidence
            signal["confidence"] = max(confidence * (1.0 - penalty * 0.5), 0.0)
            signal["_causal_bias"] = cb
            signal["_causal_effect"] = "reduced"
            log.info("  %s: causal bias %.2f REDUCES %s (conf %.2f → %.2f)",
                     symbol, cb, bias, confidence, signal["confidence"])
    else:
        signal["_causal_bias"] = cb
        signal["_causal_effect"] = "neutral"

    return signal


# ──────────────────────────────────────────────────────────────────────
#  Core signal providers
# ──────────────────────────────────────────────────────────────────────


def signal_sma(symbol="EURUSD", ctx=None):
    df = get_historical_mt5(symbol, count=100, tf=15)
    if df is None or len(df) < 50:
        return {"bias": "neutral", "confidence": 0, "source": "sma"}
    c = df['close'].values
    s20, s50 = sum(c[-20:]) / 20, sum(c[-50:]) / 50
    if s20 > s50:
        return apply_causal_bias({"bias": "buy", "confidence": 0.6, "source": "sma"}, symbol, ctx=ctx)
    if s20 < s50:
        return apply_causal_bias({"bias": "sell", "confidence": 0.6, "source": "sma"}, symbol, ctx=ctx)
    return {"bias": "neutral", "confidence": 0, "source": "sma"}


def signal_wyckoff(symbol="EURUSD", ctx=None):
    try:
        sys.path.insert(0, str(SRC))
        from quant_nanggroe.engine.strategies.wyckoff import WyckoffStrategy
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 60:
            return {"bias": "neutral", "confidence": 0, "source": "wyckoff"}
        strat = WyckoffStrategy(lookback=50, volume_mult=1.3)
        signals = strat.generate_signals(df)
        recent = signals.tail(10)
        non_zero = recent[recent['entry'] != 0]
        if len(non_zero) > 0:
            last_sig = non_zero.iloc[-1]
            entry = last_sig['entry']
            idx_pos = 0
            for i in range(len(recent) - 1, -1, -1):
                if recent.iloc[i]['entry'] != 0:
                    idx_pos = len(recent) - 1 - i
                    break
            confidence = max(0.4, 0.65 - idx_pos * 0.08)
            if entry == 1:
                return apply_causal_bias({"bias": "buy", "confidence": min(1.0, confidence), "source": "wyckoff"}, symbol, ctx=ctx)
            elif entry == -1:
                return apply_causal_bias({"bias": "sell", "confidence": min(1.0, confidence), "source": "wyckoff"}, symbol, ctx=ctx)
    except Exception as e:
        log.warning(f"Wyckoff err: {e}")
    return {"bias": "neutral", "confidence": 0, "source": "wyckoff"}


def signal_aihf(symbol="EURUSD", ctx=None):
    try:
        _path = os.environ.get("QNA_EXT_AI_HEDGE_FUND", "E:/ai-hedge-fund")
        sys.path.insert(0, _path)
        from src.main import run_hedge_fund
        res = run_hedge_fund({"symbol": symbol})
        b = "neutral" if res.get("decision", "hold") == "hold" else res["decision"]
        return apply_causal_bias(
            {"bias": b, "confidence": res.get("confidence", 0.5), "source": "aihf"}, symbol, ctx=ctx)
    except Exception as e:
        log.warning(f"AIHF err: {e}")
        return {"bias": "neutral", "confidence": 0, "source": "aihf"}


def signal_hidden(symbol="EURUSD", ctx=None):
    try:
        _path = os.environ.get("QNA_EXT_HIDDEN_REGIME", "E:/hidden-regime")
        sys.path.insert(0, _path)
        import yfinance as yf
        from hidden_regime import create_financial_pipeline
        p = create_financial_pipeline()
        ticker = symbol.replace("EURUSD", "EURUSD=X")
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df is not None and len(df) > 20:
            p.data.load_data(data=df)
            p.update()
            model = p.model
            if hasattr(model, 'decode_states'):
                states = model.decode_states(p.observations) if hasattr(p, 'observations') else model.decode_states(model.emission_means_)
                if states is not None and len(states) > 0:
                    current_state = int(states[-1])
                    state_labels = {0: "bearish", 1: "neutral", 2: "bullish"}
                    if current_state in state_labels:
                        m = {"bullish": "buy", "bearish": "sell"}
                        reg = state_labels[current_state]
                        if reg in m:
                            return apply_causal_bias(
                                {"bias": m[reg], "confidence": 0.45, "source": "hidden"}, symbol, ctx=ctx)
    except Exception as e:
        log.warning(f"Hidden err: {e}")
    return {"bias": "neutral", "confidence": 0, "source": "hidden"}


def signal_tradingagents(symbol="EURUSD", ctx=None):
    try:
        _path = os.environ.get("QNA_EXT_TRADING_AGENTS", "E:/tradingagents")
        sys.path.insert(0, _path)
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        cfg = DEFAULT_CONFIG.copy()
        if os.environ.get("QNA_ALLOW_PAID_LLM", "").strip().lower() not in {"1", "true", "yes"}:
            provider = cfg.get("llm_provider", "openai")
            if provider in {"openai", "anthropic", "azure", "bedrock", "google"}:
                log.info(
                    "TradingAgents skipped: paid LLM provider '%s' blocked by QNA_ALLOW_PAID_LLM guard", provider)
                return {"bias": "neutral", "confidence": 0, "source": "tradingagents"}
        today = datetime.now().strftime("%Y-%m-%d")
        ta = TradingAgentsGraph(debug=False, config=cfg)
        result = ta.propagate(symbol.replace("EURUSD", "EURUSD=X"), today)
        rating = result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else result
        _ta_rank = {"buy": "buy", "overweight": "buy", "hold": "neutral",
                     "underweight": "sell", "sell": "sell"}
        bias = _ta_rank.get(str(rating).strip().lower(), "neutral")
        conf = 0.5 if bias != "neutral" else 0.0
        return apply_causal_bias(
            {"bias": bias, "confidence": conf, "source": "tradingagents"}, symbol, ctx=ctx)
    except Exception as e:
        log.warning(f"TradingAgents err: {e}")
        return {"bias": "neutral", "confidence": 0, "source": "tradingagents"}


def signal_aitrader(symbol="EURUSD", ctx=None):
    try:
        _cwd = os.environ.get("QNA_EXT_AI_TRADER", "E:/AI-Trader")
        r = subprocess.run(["node", "src/index.js", f"--symbol={symbol}"],
                           cwd=_cwd, capture_output=True, text=True, timeout=15)
        out = r.stdout.lower()
        if "buy" in out:
            return apply_causal_bias({"bias": "buy", "confidence": 0.5, "source": "aitrader"}, symbol, ctx=ctx)
        if "sell" in out:
            return apply_causal_bias({"bias": "sell", "confidence": 0.5, "source": "aitrader"}, symbol, ctx=ctx)
    except Exception:
        pass
    return {"bias": "neutral", "confidence": 0, "source": "aitrader"}


def signal_langalpha(symbol="EURUSD", ctx=None):
    try:
        _path = os.environ.get("QNA_EXT_LANG_ALPHA", "E:/LangAlpha")
        sys.path.insert(0, _path)
        from ptc_cli.main import research
        res = research(symbol)
        if res and isinstance(res, dict):
            b = res.get("signal", "neutral")
            if b == "hold":
                b = "neutral"
            return apply_causal_bias(
                {"bias": b, "confidence": res.get("confidence", 0.4), "source": "langalpha"}, symbol, ctx=ctx)
    except Exception:
        pass
    return {"bias": "neutral", "confidence": 0, "source": "langalpha"}


def signal_aimarketmaker(symbol="EURUSD", ctx=None):
    try:
        _path = os.environ.get("QNA_EXT_AI_MARKET_MAKER", "E:/ai-market-maker")
        sys.path.insert(0, _path)
        from aimm.execution.executor import execute_strategy as aimm_execute
        res = aimm_execute(symbol, mode="signal")
        if isinstance(res, dict):
            bias = res.get("decision", "neutral")
            if bias == "hold":
                bias = "neutral"
            return apply_causal_bias(
                {"bias": bias, "confidence": res.get("confidence", 0.5), "source": "aimm"}, symbol, ctx=ctx)
    except Exception as e:
        log.warning(f"AIMM err: {e}")
    return {"bias": "neutral", "confidence": 0, "source": "aimm"}


def signal_kronos(symbol="EURUSD", ctx=None):
    try:
        _path = os.environ.get("QNA_EXT_TRADING", str(pathlib.Path(__file__).resolve().parent.parent.parent.parent))
        sys.path.insert(0, _path)
        import pandas as pd
        import yfinance as yf
        from strategies.kronos_wrapper import KronosSignalProvider

        ticker = symbol.replace("EURUSD", "EURUSD=X")
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df is not None and len(df) > 200:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
            required = ['open', 'high', 'low', 'close', 'volume']
            if all(c in df.columns for c in required):
                df = df[required].dropna()
                if len(df) > 200:
                    strat = KronosSignalProvider(lookback=200, pred_len=5)
                    result = strat.generate_signals(df)
                    last = result.iloc[-1]
                    sig = int(last.get('entry', 0))
                    if sig > 0:
                        return apply_causal_bias(
                            {"bias": "buy", "confidence": 0.55, "source": "kronos"}, symbol, ctx=ctx)
                    elif sig < 0:
                        return apply_causal_bias(
                            {"bias": "sell", "confidence": 0.55, "source": "kronos"}, symbol, ctx=ctx)
    except Exception as e:
        log.warning(f"Kronos err: {e}")
    return {"bias": "neutral", "confidence": 0, "source": "kronos"}


def signal_pyportfolioopt(symbol="EURUSD", ctx=None):
    try:
        _path = os.environ.get("QNA_EXT_PYPORTFOLIO_OPT", "E:/PyPortfolioOpt")
        sys.path.insert(0, _path)
        from pypfopt.efficient_frontier import EfficientFrontier
        from pypfopt.expected_returns import mean_historical_return
        from pypfopt.risk_models import CovarianceShrinkage
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias": "neutral", "confidence": 0, "source": "ppo"}
        prices = df['close']
        mu = mean_historical_return(prices.to_frame(symbol))
        S = CovarianceShrinkage(prices.to_frame(symbol)).shrinkage()
        ef = EfficientFrontier(mu, S)
        try:
            weights = ef.max_sharpe()
            if symbol in weights:
                w = weights[symbol]
                return apply_causal_bias(
                    {"bias": "buy" if w > 0 else "sell", "confidence": min(abs(w), 1.0),
                     "source": "ppo", "weight": w}, symbol, ctx=ctx)
        except Exception:
            pass
    except Exception as e:
        log.warning(f"PyPortfolioOpt err: {e}")
    return {"bias": "neutral", "confidence": 0, "source": "ppo"}
