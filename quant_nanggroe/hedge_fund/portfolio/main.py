"""Main hedge fund orchestration cycle — ties all modules together."""

import json
import subprocess
import sys
import time
from datetime import datetime

from quant_nanggroe.hedge_fund.utils import config as _config
from quant_nanggroe.hedge_fund.utils.config import (
    GATE_FILE,
    MT5_AVAILABLE,
    _QNA_DIR,
    log,
    mt5,
)
from quant_nanggroe.hedge_fund.utils.connection import connect, ensure_terminal
from quant_nanggroe.hedge_fund.utils.indicators import calc_atr
from quant_nanggroe.hedge_fund.signals.registry import ALL_PROVIDERS
from quant_nanggroe.hedge_fund.signals.aggregator import aggregate
from quant_nanggroe.hedge_fund.risk.gate import check_gate
from quant_nanggroe.hedge_fund.risk.guard import risk_guard_approve
from quant_nanggroe.hedge_fund.execution.orders import execute, trail_sl


def run_once(target_symbol=None):
    log.info("Hedge Fund v3 -- GATED")

    if not PAPER_TRADE:
        if not connect() and not ensure_terminal():
            log.warning("MT5 unavailable - falling back to paper trading")
            _config.PAPER_TRADE = True
    else:
        log.info("PAPER TRADE MODE - No MT5 connection needed")

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
            log.info("Running backtest + walk-forward...")
            try:
                r = subprocess.run([sys.executable, str(_QNA_DIR / 'backtest_pipeline.py')],
                                  capture_output=True, text=True, timeout=120)
                gate_pass = '"pass": true' in (r.stdout + r.stderr)
            except Exception as e:
                log.warning(f"Backtest failed: {e}")

    if not gate_pass:
        log.warning("GATE TERTUTUP - Strategi gagal backtest/walk-forward")
        log.warning("   Tidak akan execute sampai strategi diperbaiki")
        if not _config.PAPER_TRADE:
            try:
                mt5.shutdown()
            except Exception:
                pass
        return

    log.info("GATE LULUS - Strategi siap eksekusi")

    try:
        symbol = target_symbol
        if not symbol:
            try:
                from multi_pair_scanner import get_valid_pairs
                pairs = get_valid_pairs()
                if pairs:
                    symbol = pairs[0]
                    log.info(f"Best pair: {symbol}")
            except Exception as e:
                log.debug(f"Pair scanner unavailable: {e}")
        if not symbol:
            symbol = "EURUSD"

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

        if positions:
            for p in positions:
                log.info(f"OPEN: {p.symbol} {'BUY' if p.type==0 else 'SELL'} PnL=${p.profit:.2f}")
                ns = trail_sl(p)
                if ns and (p.sl is None or abs(ns-p.sl) > 0.00001):
                    try:
                        if p.type == 0 and ns > (p.sl or 0):
                            r = mt5.order_send({"action":mt5.TRADE_ACTION_SLTP,"position":p.ticket,"sl":ns,"tp":p.tp})
                            if r and r.retcode == 10009: log.info(f"  Trail->{ns:.5f}")
                        elif p.type == 1 and ns < (p.sl or 999):
                            r = mt5.order_send({"action":mt5.TRADE_ACTION_SLTP,"position":p.ticket,"sl":ns,"tp":p.tp})
                            if r and r.retcode == 10009: log.info(f"  Trail->{ns:.5f}")
                    except Exception as e:
                        log.debug(f"Trail failed: {e}")
        else:
            log.info(f"Voting: {len(ALL_PROVIDERS)} providers")
            signal = aggregate(symbol)
            log.info(f"DECISION: {signal['bias']} (conf={signal['confidence']:.2f})")
            if signal["bias"] in ("buy", "sell"):
                try:
                    from risk_guard import approve as rg_approve
                except Exception as e:
                    log.error(f"Risk guard import FAILED - blocking trade (fail-closed): {e}")
                    if not _config.PAPER_TRADE:
                        try:
                            mt5.shutdown()
                        except Exception:
                            pass
                    return

                acct = mt5.account_info() if (MT5_AVAILABLE and not _config.PAPER_TRADE) else None
                real_balance = acct.balance if acct else 1000.0
                real_daily_pnl = 0.0
                if acct and not _config.PAPER_TRADE:
                    try:
                        from datetime import datetime as _dt
                        start = _dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
                        deals = mt5.history_deals_get(start, _dt.now())
                        if deals:
                            real_daily_pnl = sum(float(d.profit) + float(d.commission or 0) for d in deals)
                    except Exception as _e:
                        log.debug(f"daily pnl read failed: {_e}")
                real_open = len(mt5.positions_get() or []) if (MT5_AVAILABLE and not _config.PAPER_TRADE) else 0

                proposal = {
                    "symbol": symbol,
                    "action": signal["bias"],
                    "volume": max(0.01, round(real_balance / 10000, 2)),
                    "price": signal.get("price", 1.0),
                    "sl": signal.get("sl", 0),
                    "account_balance": real_balance,
                    "daily_pnl": real_daily_pnl,
                    "open_positions": real_open,
                    "market_volatility": (calc_atr(symbol) or 0.001) / 1.0,
                }
                rg_result = risk_guard_approve(proposal)

                if rg_result.get("status") == "VETOED":
                    log.warning(f"Risk Guard VETO: {rg_result.get('reasons', 'unknown')}")
                    if not _config.PAPER_TRADE:
                        try:
                            mt5.shutdown()
                        except Exception:
                            pass
                    return
                log.info(f"Risk Guard APPROVED (score={rg_result.get('risk_score', rg_result.get('score',0)):.2f})")

                execute(signal, symbol)

    finally:
        if not _config.PAPER_TRADE:
            try:
                mt5.shutdown()
            except Exception:
                pass
