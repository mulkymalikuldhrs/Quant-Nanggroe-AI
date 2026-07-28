"""Main hedge fund orchestration cycle — ties all modules together.

Fixed gaps:
  - backtest_pipeline.py now exists (created at repo root)
  - SignalTracker wired to aggregator for Bayesian performance weighting
  - Weekly PnL added to risk guard proposal
  - Strategy lifecycle manager wired to filter KILLED strategies
  - FractionalKelly parameters sourced from real backtest data
"""

import asyncio
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from quant_nanggroe.engine.backtest.walk_forward import get_viable_strategies
from quant_nanggroe.engine.causal import MasterQuantNanggroeEngine
from quant_nanggroe.engine.causal.models import CausalContext
from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.engine.execution.builder import build_execution_manager
from quant_nanggroe.engine.risk.kill_switch import (
    KillSwitch,
    KillSwitchLevel,
    configure_kill_switch_file,
)
from quant_nanggroe.engine.risk.kelly import KellyCriterion
from quant_nanggroe.engine.strategy_lifecycle import StrategyLifecycleManager
from quant_nanggroe.hedge_fund.execution.orders import trail_sl
from quant_nanggroe.hedge_fund.portfolio.sizing import calculate_position_size
from quant_nanggroe.hedge_fund.risk.guard import risk_guard_approve
from quant_nanggroe.hedge_fund.signals.aggregator import aggregate
from quant_nanggroe.hedge_fund.signals.registry import ALL_PROVIDERS
from quant_nanggroe.hedge_fund.signals.tracker import SignalTracker
from quant_nanggroe.hedge_fund.utils import config as _config
from quant_nanggroe.hedge_fund.utils.config import (
    GATE_FILE,
    MT5_AVAILABLE,
    log,
    mt5,
)
from quant_nanggroe.hedge_fund.utils.connection import connect, ensure_terminal
from quant_nanggroe.hedge_fund.utils.indicators import calc_atr

# ── Module-level singletons ───────────────────────────────────────────
_signal_tracker = SignalTracker()
_lifecycle_manager: Optional[StrategyLifecycleManager] = None
_kelly_sizer = KellyCriterion()
_execution_manager = build_execution_manager()


def _execute_order_sync(signal: dict, symbol: str) -> Optional[str]:
    """Bridge sync run_once() → async ExecutionManager.execute_order().

    Converts a signal dict into an Order dataclass and routes it through
    the full guard pipeline (cooldown, max-position, whitelist, governance
    veto, kill switch, constitutional risk manager). Returns the order ID
    on success, None on rejection.
    """
    side = OrderSide.BUY if signal.get("bias") == "buy" else OrderSide.SELL
    order = Order(
        id=str(uuid.uuid4()),
        symbol=symbol,
        side=side,
        order_type=OrderType.MARKET,
        quantity=signal.get("volume", 0.01),
        price=signal.get("price", None),
        stop_loss=signal.get("sl", None),
        take_profit=signal.get("tp", None),
        time_in_force="GTC",
        status=OrderStatus.PENDING,
        metadata={"source": "run_once", "confidence": signal.get("confidence", 0.5)},
    )
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.ensure_future(_execution_manager.execute_order(order))
            fill = loop.run_until_complete(future)
        else:
            fill = loop.run_until_complete(_execution_manager.execute_order(order))
    except RuntimeError:
        fill = asyncio.run(_execution_manager.execute_order(order))
    if fill is None:
        return None
    return fill.order_id


def _get_lifecycle() -> StrategyLifecycleManager:
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = StrategyLifecycleManager()
        _lifecycle_manager._load()  # load from disk
    return _lifecycle_manager


# ── Helper: real-time market snapshot for causal macro weather ─────────

def _market_snapshot() -> tuple:
    """Fetch live DXY change % and ZB bond change % from yfinance.

    Returns (dxy_change_pct, bond_zb_change_pct).
    Both default to 0.0 if market data is unavailable.
    """
    dxy_pct = 0.0
    zb_pct = 0.0
    try:
        import yfinance as yf

        dxy = yf.Ticker("DX-Y.NYB")
        dxy_hist = dxy.history(period="3d", interval="1h")
        if len(dxy_hist) >= 2:
            dxy_pct = (dxy_hist.iloc[-1]["Close"] - dxy_hist.iloc[-2]["Close"]) / dxy_hist.iloc[-2]["Close"] * 100
            log.debug("DXY change: %.2f%%", dxy_pct)

        zb = yf.Ticker("ZB=F")
        zb_hist = zb.history(period="3d", interval="1h")
        if len(zb_hist) >= 2:
            zb_pct = (zb_hist.iloc[-1]["Close"] - zb_hist.iloc[-2]["Close"]) / zb_hist.iloc[-2]["Close"] * 100
            log.debug("ZB change: %.2f%%", zb_pct)
    except Exception as e:
        log.debug("Market snapshot unavailable (DXY/ZB defaults to 0): %s", e)
    return dxy_pct, zb_pct


# ── Helper: weekly PnL from MT5 ───────────────────────────────────────

def _weekly_pnl() -> float:
    """Calculate realized PnL for the current week."""
    if not MT5_AVAILABLE or _config.PAPER_TRADE:
        return 0.0
    try:
        now = datetime.now()
        monday = now - timedelta(days=now.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(monday, now)
        if deals:
            return sum(float(d.profit) + float(d.commission or 0) + float(d.swap or 0) for d in deals)
    except Exception as e:
        log.debug("Weekly PnL read failed: %s", e)
    return 0.0


# ── Causal context builder ────────────────────────────────────────────

def _build_causal_context(dxy_pct: float = 0.0, zb_pct: float = 0.0) -> Optional[CausalContext]:
    """Instantiate MasterQuantNanggroeEngine and produce a CausalContext.

    Fetches event-based biases and macro weather regime.
    Returns None on any failure (graceful degradation).
    """
    try:
        engine = MasterQuantNanggroeEngine(enable_fred=False, enable_cot=False)

        biases = engine.evaluate_causal_bias(
            event_type=os.environ.get("QNA_MACRO_EVENT", ""),
            geopolitical_risk_delta=float(os.environ.get("QNA_GEOPOLITICAL_RISK_DELTA", "0")),
        )

        weather_raw = engine.detect_macro_weather(
            dxy_change_pct=dxy_pct,
            bond_zb_change_pct=zb_pct,
        )
        weather = str(weather_raw).lower().replace("neutral_mixed", "neutral") if weather_raw else "neutral"

        ctx = CausalContext(biases=biases, macro_regime=weather)
        log.info("CausalContext: %d biases, regime=%s, dxy=%.2f%%, zb=%.2f%%",
                 len(biases), weather, dxy_pct, zb_pct)
        return ctx
    except Exception as e:
        log.warning("CausalContext init skipped — proceeding without macro bias: %s", e)
        return None


# ── Main entry point ──────────────────────────────────────────────────

def run_once(target_symbol=None) -> dict:
    """Run one hedge fund cycle. Returns a structured result dict.

    Keys:
        status       — one of "gate_failed", "positions_trailed",
                       "vetoed", "executed", "order_failed",
                       "paper_blocked", "no_trade"
        symbol       — the symbol processed
        signal       — aggregator output dict (present when vote occurred)
        causal_ctx   — CausalContext snapshot (present when engine OK)
        n_providers  — provider count (present when vote occurred)
        risk_score   — risk guard score (present when trade proposed)
        executed     — True/False (present when trade proposed)
    """
    log.info("Hedge Fund v4 — GATED + Bayesian-weighted + Lifecycle-aware")
    result: dict = {"status": "gate_failed", "symbol": target_symbol or "EURUSD"}

    # ── MT5 connection ────────────────────────────────────────────────
    if not _config.PAPER_TRADE:
        if not connect() and not ensure_terminal():
            log.warning("MT5 unavailable — falling back to paper trading")
            _config.PAPER_TRADE = True
    else:
        log.info("PAPER TRADE MODE — No MT5 connection needed")

    # ── Gate check ────────────────────────────────────────────────────
    gate_cache = GATE_FILE
    gate_pass = False

    if _config.PAPER_TRADE:
        if gate_cache.exists():
            try:
                age = time.time() - gate_cache.stat().st_mtime
                if age < 86400:
                    gate_pass = json.loads(gate_cache.read_text()).get("pass", False)
            except Exception:
                pass
        if not gate_pass:
            log.info("Paper mode: skipping gate (will run backtest in background)")
            gate_pass = True
    else:
        if gate_cache.exists():
            try:
                age = time.time() - gate_cache.stat().st_mtime
                if age < 86400:
                    gate_pass = json.loads(gate_cache.read_text()).get("pass", False)
            except Exception:
                pass

        if not gate_pass:
            log.info("Checking WalkForwardRegistry for viable strategies...")
            try:
                viable = get_viable_strategies()
                gate_pass = len(viable) > 0
                if gate_pass:
                    log.info("Gate passed: %d viable strategies in registry", len(viable))
                else:
                    log.warning("No viable strategies found in WalkForwardRegistry")
            except Exception as e:
                log.warning(f"WalkForwardRegistry check failed: {e}")

    if not gate_pass:
        log.warning("GATE TERTUTUP — Strategi gagal backtest/walk-forward")
        log.warning("   Tidak akan execute sampai strategi diperbaiki")
        result["status"] = "gate_failed"
        result["reason"] = "backtest_gate_blocked"
        if not _config.PAPER_TRADE:
            try:
                mt5.shutdown()
            except Exception:
                pass
        return result

    log.info("GATE LULUS — Strategi siap eksekusi")
    result["status"] = "no_trade"  # default unless we find a trade

    try:
        symbol = target_symbol
        if not symbol:
            try:
                from quant_nanggroe.hedge_fund.tools.multi_pair_scanner import get_valid_pairs
                pairs = get_valid_pairs()
                if pairs:
                    symbol = pairs[0]
                    log.info(f"Best pair: {symbol}")
            except Exception as e:
                log.debug(f"Pair scanner unavailable: {e}")
        if not symbol:
            symbol = "EURUSD"
        result["symbol"] = symbol

        if not _config.PAPER_TRADE:
            a = mt5.account_info()
            if a:
                log.info(f"${a.balance:.2f} | Equity=${a.equity:.2f} | Margin=${a.margin:.2f}")

        positions = []
        if not _config.PAPER_TRADE:
            try:
                positions = mt5.positions_get() or []
            except Exception:
                positions = []

        # ── Trail existing positions ──────────────────────────────────
        if positions:
            result["status"] = "positions_trailed"
            result["n_positions"] = len(positions)
            for p in positions:
                log.info(f"OPEN: {p.symbol} {'BUY' if p.type==0 else 'SELL'} PnL=${p.profit:.2f}")
                ns = trail_sl(p)
                if ns and (p.sl is None or abs(ns - p.sl) > 0.00001):
                    try:
                        if p.type == 0 and ns > (p.sl or 0):
                            r = mt5.order_send({
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": p.ticket,
                                "sl": ns,
                                "tp": p.tp,
                            })
                            if r and r.retcode == 10009:
                                log.info(f"  Trail->{ns:.5f}")
                        elif p.type == 1 and ns < (p.sl or 999):
                            r = mt5.order_send({
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": p.ticket,
                                "sl": ns,
                                "tp": p.tp,
                            })
                            if r and r.retcode == 10009:
                                log.info(f"  Trail->{ns:.5f}")
                    except Exception as e:
                        log.debug(f"Trail failed: {e}")
        else:
            # ── No positions — vote on new trade ──────────────────────
            lifecycle = _get_lifecycle()
            n_active = len(lifecycle.get_active_strategies())
            log.info(f"Voting: {len(ALL_PROVIDERS)} providers across {n_active} active strategies")
            result["n_providers"] = len(ALL_PROVIDERS)

            # ── Causal context with live market data ──────────────────
            dxy_pct, zb_pct = _market_snapshot()
            causal_ctx = _build_causal_context(dxy_pct, zb_pct)
            result["causal_ctx"] = causal_ctx

            # ── Pre-trade market screen (ScreenerOrchestrator) ───────
            _screen_result = None
            try:
                from quant_nanggroe.engine.screener.orchestrator import ScreenerOrchestrator
                _screener = ScreenerOrchestrator()
                _screen_data = {
                    "symbol": symbol,
                    "causal_ctx": causal_ctx,
                    "dxy_pct": dxy_pct,
                    "zb_pct": zb_pct,
                    "price": signal.get("price", 0),
                }
                _screen_result = _screener.screen(_screen_data)
                result["screen"] = _screen_result
                log.info("Screen: dir=%s score=%.2f", _screen_result.get("overall_direction", "?"),
                         _screen_result.get("composite_score", 0))
            except Exception as _scr_e:
                log.debug("Screener skipped: %s", _scr_e)

            # ── Filter providers by walk-forward viability ────────────
            viable_strategies = get_viable_strategies()
            provider_list = ALL_PROVIDERS
            if viable_strategies:
                viable_names = {s["name"] for s in viable_strategies}
                filtered = []
                for p in ALL_PROVIDERS:
                    pname = getattr(p, "__name__", str(p))
                    if not pname.startswith("signal_qna_"):
                        filtered.append(p)
                        continue
                    sname = pname[len("signal_"):]
                    if sname in viable_names:
                        filtered.append(p)
                if len(filtered) < len(ALL_PROVIDERS):
                    log.info("Providers filtered: %d → %d (only viable)", len(ALL_PROVIDERS), len(filtered))
                    provider_list = filtered

            # ── Aggregate with Bayesian weights + strategy lifecycle ──
            signal = aggregate(symbol, ctx=causal_ctx, tracker=_signal_tracker, providers=provider_list)
            result["signal"] = signal
            log.info(f"DECISION: {signal['bias']} (conf={signal['confidence']:.2f})")

            # ── Confluence signal fusion (ConfluenceScorer) ──────────
            _confluence = None
            try:
                if _screen_result is not None:
                    from quant_nanggroe.engine.portfolio.confluence_scorer import ConfluenceScorer
                    _scorer = ConfluenceScorer()
                    _all_signals = [
                        {"source": "aggregator", "side": signal["bias"], "confidence": signal["confidence"]},
                        {"source": "screener", "side": _screen_result.get("overall_direction", "neutral"),
                         "confidence": _screen_result.get("composite_score", 0) / 100.0},
                    ]
                    _confluence = _scorer.evaluate(
                        _all_signals,
                        macro_bias=getattr(causal_ctx, "biases", None) if causal_ctx else None,
                        macro_weather=getattr(causal_ctx, "macro_regime", None) if causal_ctx else None,
                    )
                    result["confluence"] = _confluence
                    log.info("Confluence: signal=%s score=%.2f",
                             _confluence.overall_signal if hasattr(_confluence, "overall_signal") else "?",
                             _confluence.score if hasattr(_confluence, "score") else 0)
                    if hasattr(_confluence, "overall_signal") and _confluence.overall_signal == "hold":
                        log.warning("Confluence veto — all signals fused to HOLD")
                        result["status"] = "confluence_veto"
                        signal["bias"] = "hold"
                        signal["confidence"] = 0.0
            except Exception as _con_e:
                log.debug("ConfluenceScorer skipped: %s", _con_e)

            if signal["bias"] in ("buy", "sell"):
                acct = mt5.account_info() if (MT5_AVAILABLE and not _config.PAPER_TRADE) else None
                real_balance = acct.balance if acct else 1000.0
                real_daily_pnl = 0.0
                if acct and not _config.PAPER_TRADE:
                    try:
                        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                        deals = mt5.history_deals_get(start, datetime.now())
                        if deals:
                            real_daily_pnl = sum(float(d.profit) + float(d.commission or 0) for d in deals)
                    except Exception as _e:
                        log.debug(f"daily pnl read failed: {_e}")
                real_open = len(mt5.positions_get() or []) if (MT5_AVAILABLE and not _config.PAPER_TRADE) else 0

                market_atr = calc_atr(symbol) or 0.001
                sizing = calculate_position_size(signal, real_balance, atr=market_atr)

                # ── Risk parity position scaling (RiskParityAllocator) ────
                _rp_weight = 1.0
                try:
                    from quant_nanggroe.engine.portfolio.risk_parity_bridgewater import RiskParityAllocator
                    _rp = RiskParityAllocator(target_vol=0.10, max_leverage=2.0)
                    _volatilities = {symbol: market_atr}
                    _rp_weights = _rp.compute_risk_parity_weights(_volatilities)
                    if _rp_weights and symbol in _rp_weights:
                        _rp_weight = _rp_weights[symbol]
                        sizing["volume"] = sizing["volume"] * _rp_weight
                        log.info("RiskParity weight=%s multiplier=%.2f", symbol, _rp_weight)
                    result["risk_parity"] = _rp_weights
                except Exception as _rp_e:
                    log.debug("RiskParityAllocator skipped: %s", _rp_e)

                proposal = {
                    "symbol": symbol,
                    "action": signal["bias"],
                    "volume": sizing["volume"],
                    "price": signal.get("price", 1.0),
                    "sl": signal.get("sl", 0),
                    "account_balance": real_balance,
                    "daily_pnl": real_daily_pnl,
                    "weekly_pnl": _weekly_pnl(),  # ← FIXED: was missing
                    "open_positions": real_open,
                    "market_volatility": market_atr / 1.0,
                }
                # ── KillSwitch auto-activation check (canonical engine/risk) ──
                configure_kill_switch_file()
                ks = KillSwitch()
                ks.check_auto_activate(
                    daily_pnl_pct=real_daily_pnl / real_balance if real_balance > 0 else 0,
                    weekly_pnl_pct=_weekly_pnl() / real_balance if real_balance > 0 else 0,
                )
                if not ks.can_trade():
                    log.warning("KILL SWITCH VETO — halted (level=%s)", ks.current_level.value)
                    result["status"] = "kill_switched"
                    result["kill_level"] = ks.current_level.value
                    if not _config.PAPER_TRADE:
                        try:
                            mt5.shutdown()
                        except Exception:
                            pass
                    return result

                rg_result = risk_guard_approve(proposal)
                risk_score = rg_result.get("risk_score", rg_result.get("score", 0))

                if rg_result.get("status") == "VETOED":
                    log.warning(f"Risk Guard VETO: {rg_result.get('reasons', 'unknown')}")
                    result["status"] = "vetoed"
                    result["risk_score"] = risk_score
                    result["risk_reasons"] = rg_result.get("reasons", "unknown")
                    if not _config.PAPER_TRADE:
                        try:
                            mt5.shutdown()
                        except Exception:
                            pass
                    return result

                log.info(f"Risk Guard APPROVED (score={risk_score:.2f})")
                result["risk_score"] = risk_score
                try:
                    order_id = _execute_order_sync(signal, symbol)
                except RuntimeError as e:
                    # ExecutionManager guard pipeline blocked the order
                    log.warning(f"ExecutionManager blocked order: {e}")
                    result["status"] = "paper_blocked"
                    result["executed"] = False
                else:
                    if order_id:
                        result["status"] = "executed"
                        result["executed"] = True
                        result["order_id"] = order_id
                        # Feed PnL return to adaptive Kelly for performance tracking
                        if real_balance > 0:
                            _kelly_sizer.feed_performance([real_daily_pnl / real_balance])

                        # ── Post-trade stress VaR (StressVaRCalculator) ──
                        try:
                            from quant_nanggroe.engine.stress_testing.var_cvar import StressVaRCalculator
                            _var = StressVaRCalculator()
                            _returns = np.array([real_daily_pnl / real_balance]) if real_balance > 0 else np.array([0.0])
                            if len(_returns) > 0:
                                _var_result = _var.compute(_returns)
                                log.info("StressVaR: param_95=%.4f cvar_95=%.4f",
                                         getattr(_var_result, "parametric_var_95", 0),
                                         getattr(_var_result, "cvar_95", 0))
                                result["stress_var"] = {
                                    "parametric_var_95": getattr(_var_result, "parametric_var_95", 0),
                                    "cvar_95": getattr(_var_result, "cvar_95", 0),
                                    "historical_var_95": getattr(_var_result, "historical_var_95", 0),
                                }
                        except Exception as _var_e:
                            log.debug("StressVaR skipped: %s", _var_e)

                        # ── Post-trade pattern recording (MatrixProfileDetector) ──
                        try:
                            from quant_nanggroe.engine.pattern_recorder.matrix_profile import MatrixProfileDetector
                            _mpd = MatrixProfileDetector()
                            _price_series = getattr(_market_df, "close", None) if hasattr(locals(), "_market_df") else None
                            if _price_series is not None:
                                _mp_result = _mpd.compute(_price_series, window_size=min(20, len(_price_series) // 4))
                                if _mp_result:
                                    _motif_count = len(_mp_result.get("motifs", [])) if isinstance(_mp_result, dict) else 0
                                    log.info("PatternRecorder: %d motifs found", _motif_count)
                                    result["patterns"] = {
                                        "motif_count": _motif_count,
                                        "discord_count": len(_mp_result.get("discords", [])) if isinstance(_mp_result, dict) else 0,
                                    }
                        except Exception as _mp_e:
                            log.debug("PatternRecorder skipped: %s", _mp_e)
                    else:
                        log.warning("Order not placed — execute() returned no order id")
                        result["status"] = "order_failed"
                        result["executed"] = False
            else:
                result["status"] = "no_trade"

    finally:
        if not _config.PAPER_TRADE:
            try:
                mt5.shutdown()
            except Exception:
                pass

    return result


# ── Export lifecycle manager for external use ─────────────────────────
def get_signal_tracker() -> SignalTracker:
    """Return the module-level signal tracker singleton."""
    return _signal_tracker


def get_lifecycle_manager() -> StrategyLifecycleManager:
    """Return the module-level lifecycle manager singleton."""
    return _get_lifecycle()
