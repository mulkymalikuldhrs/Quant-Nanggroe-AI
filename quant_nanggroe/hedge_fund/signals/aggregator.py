"""Multi-provider weighted vote aggregation with market context boost."""

import csv
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from quant_nanggroe.hedge_fund.utils.config import VOTE_LOG, log
from quant_nanggroe.hedge_fund.signals.registry import ALL_PROVIDERS


def _timeout_call(fn, args=(), timeout=8):
    res = {"bias": "neutral", "confidence": 0, "source": fn.__name__ if hasattr(fn, '__name__') else "?"}
    def target():
        try:
            r = fn(*args)
            if isinstance(r, dict):
                res.update(r)
        except Exception as e:
            res["_error"] = str(e)
    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        log.warning(f"  {fn.__name__}: timeout ({timeout}s)")
    return res


def aggregate(symbol="EURUSD"):
    votes = []
    results = []

    context_boost = {"buy": 1.0, "sell": 1.0}
    dxy_trend = "unknown"
    dxy_price = "?"
    try:
        from market_context import get_currency_strength, get_dxy
        dxy = get_dxy()
        dxy_trend = dxy.get("trend", "unknown")
        dxy_price = dxy.get("price", "?")
        _ = get_currency_strength()

        if dxy_trend == "bull":
            context_boost["buy"] *= 0.85
            log.info(f"  DXY bull (${dxy_price}) -> buy confidence x0.85")
        elif dxy_trend == "bear":
            context_boost["sell"] *= 0.85
            log.info(f"  DXY bear (${dxy_price}) -> sell confidence x0.85")
    except Exception as e:
        log.debug(f"Market context unavailable: {e}")

    max_workers = min(20, len(ALL_PROVIDERS))
    log.info(f"  Parallel voting: {len(ALL_PROVIDERS)} providers via {max_workers} workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        fut_to_provider = {executor.submit(provider, symbol): provider for provider in ALL_PROVIDERS}
        for future in as_completed(fut_to_provider, timeout=30):
            provider = fut_to_provider[future]
            try:
                v = future.result(timeout=5)
                results.append(v)
                if v["bias"] != "neutral":
                    v["confidence"] = v.get("confidence", 0.5) * context_boost.get(v["bias"], 1.0)
                    v["confidence"] = min(v["confidence"], 1.0)
                    votes.append(v)
                    log.info(f"  {v['source']}: {v['bias']} (conf={v['confidence']:.2f})")
                else:
                    log.info(f"  {v['source']}: neutral")
            except Exception as e:
                log.warning(f"  {provider.__name__}: {e}")

    if not votes:
        log.warning("  No providers voted - staying neutral")
        return {"bias":"neutral","confidence":0,"votes":[],"context_used":dxy_trend}

    total_conf_buy = sum(v.get("confidence", 0.5) for v in votes if v["bias"] == "buy")
    total_conf_sell = sum(v.get("confidence", 0.5) for v in votes if v["bias"] == "sell")
    total_all = total_conf_buy + total_conf_sell

    log.info(f"  Weighted: buy={total_conf_buy:.2f} sell={total_conf_sell:.2f} total={total_all:.2f}")

    needs_header = not VOTE_LOG.exists() or VOTE_LOG.stat().st_size == 0
    with open(VOTE_LOG, 'a', newline='') as f:
        w = csv.writer(f)
        if needs_header:
            w.writerow(["time","symbol","buy_conf","sell_conf","total","providers","result","dxy"])
        provider_names = ",".join(v["source"] for v in votes)
        result = "buy" if total_conf_buy > total_conf_sell else "sell" if total_conf_sell > total_conf_buy else "neutral"
        w.writerow([datetime.now().isoformat(), symbol, round(total_conf_buy,2), round(total_conf_sell,2), round(total_all,2), provider_names, result, dxy_price])

    if total_conf_buy > total_conf_sell and total_all > 0:
        return {"bias":"buy","confidence":min(total_conf_buy/total_all, 1.0), "votes":votes, "total_conf": total_all}
    if total_conf_sell > total_conf_buy and total_all > 0:
        return {"bias":"sell","confidence":min(total_conf_sell/total_all, 1.0), "votes":votes, "total_conf": total_all}
    return {"bias":"neutral","confidence":0,"votes":votes}
