"""Core signal providers — built-in strategies that run locally or call external ecosystems."""

import subprocess
import sys
from datetime import datetime

from quant_nanggroe.hedge_fund.utils.config import SRC, log
from quant_nanggroe.hedge_fund.utils.data import get_historical_mt5


def signal_sma(symbol="EURUSD"):
    df = get_historical_mt5(symbol, count=100, tf=15)
    if df is None or len(df) < 50:
        return {"bias":"neutral","confidence":0,"source":"sma"}
    c = df['close'].values
    s20, s50 = sum(c[-20:])/20, sum(c[-50:])/50
    if s20 > s50: return {"bias":"buy","confidence":0.6,"source":"sma"}
    if s20 < s50: return {"bias":"sell","confidence":0.6,"source":"sma"}
    return {"bias":"neutral","confidence":0,"source":"sma"}


def signal_wyckoff(symbol="EURUSD"):
    try:
        sys.path.insert(0, str(SRC))
        from strategy_registry import WyckoffStrategy
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 60:
            return {"bias":"neutral","confidence":0,"source":"wyckoff"}
        strat = WyckoffStrategy(lookback=50, volume_mult=1.3)
        signals = strat.generate_signals(df)
        recent = signals.tail(10)
        non_zero = recent[recent['entry'] != 0]
        if len(non_zero) > 0:
            last_sig = non_zero.iloc[-1]
            entry = last_sig['entry']
            idx_pos = 0
            for i in range(len(recent)-1, -1, -1):
                if recent.iloc[i]['entry'] != 0:
                    idx_pos = len(recent) - 1 - i
                    break
            confidence = max(0.4, 0.65 - idx_pos * 0.08)
            if entry == 1:
                return {"bias":"buy","confidence":min(1.0, confidence),"source":"wyckoff"}
            elif entry == -1:
                return {"bias":"sell","confidence":min(1.0, confidence),"source":"wyckoff"}
    except Exception as e:
        log.warning(f"Wyckoff err: {e}")
    return {"bias":"neutral","confidence":0,"source":"wyckoff"}


def signal_aihf(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/ai-hedge-fund')
        from src.main import run_hedge_fund
        res = run_hedge_fund({"symbol": symbol})
        b = "neutral" if res.get("decision","hold")=="hold" else res["decision"]
        return {"bias":b,"confidence":res.get("confidence",0.5),"source":"aihf"}
    except Exception as e:
        log.warning(f"AIHF err: {e}")
        return {"bias":"neutral","confidence":0,"source":"aihf"}


def signal_hidden(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/hidden-regime')
        import yfinance as yf
        from hidden_regime import create_financial_pipeline
        p = create_financial_pipeline()
        ticker = symbol.replace("EURUSD","EURUSD=X")
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
                        m = {"bullish":"buy", "bearish":"sell"}
                        reg = state_labels[current_state]
                        if reg in m:
                            return {"bias":m[reg], "confidence":0.45, "source":"hidden"}
    except Exception as e:
        log.warning(f"Hidden err: {e}")
    return {"bias":"neutral","confidence":0,"source":"hidden"}


def signal_tradingagents(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/tradingagents')
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        import os
        cfg = DEFAULT_CONFIG.copy()
        if os.environ.get("QNA_ALLOW_PAID_LLM", "").strip().lower() not in {"1", "true", "yes"}:
            provider = cfg.get("llm_provider", "openai")
            if provider in {"openai", "anthropic", "azure", "bedrock", "google"}:
                log.info("TradingAgents skipped: paid LLM provider '%s' blocked by QNA_ALLOW_PAID_LLM guard", provider)
                return {"bias": "neutral", "confidence": 0, "source": "tradingagents"}
        today = datetime.now().strftime("%Y-%m-%d")
        ta = TradingAgentsGraph(debug=False, config=cfg)
        result = ta.propagate(symbol.replace("EURUSD", "EURUSD=X"), today)
        rating = result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else result
        _ta_rank = {"buy": "buy", "overweight": "buy", "hold": "neutral",
                    "underweight": "sell", "sell": "sell"}
        bias = _ta_rank.get(str(rating).strip().lower(), "neutral")
        conf = 0.5 if bias != "neutral" else 0.0
        return {"bias": bias, "confidence": conf, "source": "tradingagents"}
    except Exception as e:
        log.warning(f"TradingAgents err: {e}")
        return {"bias": "neutral", "confidence": 0, "source": "tradingagents"}


def signal_aitrader(symbol="EURUSD"):
    try:
        r = subprocess.run(["node","src/index.js",f"--symbol={symbol}"],
                          cwd="E:/AI-Trader",capture_output=True,text=True,timeout=15)
        out = r.stdout.lower()
        if "buy" in out: return {"bias":"buy","confidence":0.5,"source":"aitrader"}
        if "sell" in out: return {"bias":"sell","confidence":0.5,"source":"aitrader"}
    except Exception:
        pass
    return {"bias":"neutral","confidence":0,"source":"aitrader"}


def signal_langalpha(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/LangAlpha')
        from ptc_cli.main import research
        res = research(symbol)
        if res and isinstance(res, dict):
            b = res.get("signal","neutral")
            if b == "hold": b = "neutral"
            return {"bias":b,"confidence":res.get("confidence",0.4),"source":"langalpha"}
    except Exception:
        pass
    return {"bias":"neutral","confidence":0,"source":"langalpha"}


def signal_aimarketmaker(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/ai-market-maker')
        from aimm.execution.executor import execute_strategy as aimm_execute
        res = aimm_execute(symbol, mode="signal")
        if isinstance(res, dict):
            bias = res.get("decision", "neutral")
            if bias == "hold": bias = "neutral"
            return {"bias": bias, "confidence": res.get("confidence", 0.5), "source": "aimm"}
    except Exception as e:
        log.warning(f"AIMM err: {e}")
    return {"bias":"neutral","confidence":0,"source":"aimm"}


def signal_kronos(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/trading')
        import pandas as pd
        import yfinance as yf
        from strategies.kronos_wrapper import KronosSignalProvider

        ticker = symbol.replace("EURUSD", "EURUSD=X")
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df is not None and len(df) > 200:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
            required = ['open','high','low','close','volume']
            if all(c in df.columns for c in required):
                df = df[required].dropna()
                if len(df) > 200:
                    strat = KronosSignalProvider(lookback=200, pred_len=5)
                    result = strat.generate_signals(df)
                    last = result.iloc[-1]
                    sig = int(last.get('entry', 0))
                    if sig > 0:
                        return {"bias": "buy", "confidence": 0.55, "source": "kronos"}
                    elif sig < 0:
                        return {"bias": "sell", "confidence": 0.55, "source": "kronos"}
    except Exception as e:
        log.warning(f"Kronos err: {e}")
    return {"bias": "neutral", "confidence": 0, "source": "kronos"}


def signal_pyportfolioopt(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/PyPortfolioOpt')
        from pypfopt.efficient_frontier import EfficientFrontier
        from pypfopt.expected_returns import mean_historical_return
        from pypfopt.risk_models import CovarianceShrinkage
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"ppo"}
        prices = df['close']
        mu = mean_historical_return(prices.to_frame(symbol))
        S = CovarianceShrinkage(prices.to_frame(symbol)).shrinkage()
        ef = EfficientFrontier(mu, S)
        try:
            weights = ef.max_sharpe()
            if symbol in weights:
                w = weights[symbol]
                return {"bias":"buy" if w > 0 else "sell","confidence":min(abs(w), 1.0),"source":"ppo","weight":w}
        except Exception:
            pass
    except Exception as e:
        log.warning(f"PyPortfolioOpt err: {e}")
    return {"bias":"neutral","confidence":0,"source":"ppo"}
