"""Multi-provider weighted vote aggregation with Bayesian performance-based weights.

Architecture:
  1. Each provider votes (buy/sell/neutral) with a confidence score.
  2. Votes are weighted by each provider's Bayesian posterior win rate.
  3. Correlation cap prevents highly correlated sub-strategies from dominating.
  4. DXY macro context biases confidence (without overriding signal).
  5. CONFIDENCE_THRESHOLD from risk constants gates the final decision.

Usage:
    from quant_nanggroe.hedge_fund.signals.aggregator import aggregate
    signal = aggregate("EURUSD", ctx=causal_ctx, tracker=signal_tracker)
"""

import csv
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import numpy as np

from quant_nanggroe.engine.causal.models import CausalContext
from quant_nanggroe.engine.risk.constants import CONFIDENCE_THRESHOLD
from quant_nanggroe.hedge_fund.signals.registry import (
    ALL_PROVIDERS,
    CORE_PROVIDERS,
)
from quant_nanggroe.hedge_fund.signals.tracker import SignalTracker
from quant_nanggroe.hedge_fund.utils.config import VOTE_LOG, log

# ── Weights & Caps ────────────────────────────────────────────────────

MAX_CORE_WEIGHT_FRACTION = 0.40   # Core providers cap: max 40% of total weight
MAX_EVOLVED_WEIGHT_FRACTION = 0.05  # Single evolved strategy: max 5% of total weight
DEFAULT_CONFIDENCE = 0.50
CORRELATION_BUCKETS = {
    "sma": ["sma"],
    "wyckoff": ["wyckoff"],
    "qna_smc": ["qna_SMCStrategy", "qna_SMCStrategyOld"],
    "qna_msnr": ["qna_MSNRStrategy"],
    "qna_meanrev": ["qna_MeanReversionStrategy"],
    "qna_wyckoff": ["qna_WyckoffStrategy"],
    "qna_fibo": ["qna_FiboStrategy"],
    "qna_emaadx": ["qna_EMAADXStrategy"],
    "qna_amdx": ["qna_AMDXStrategy"],
    "qna_algebra": ["qna_AlgebraStrategy"],
    "qna_quarterly": ["qna_QuarterlyTheoryStrategy"],
    "external": ["aihf", "tradingagents", "langalpha",
                  "aimm", "kronos", "ppo"],
}


def _provider_name(provider) -> str:
    return getattr(provider, "__name__", str(provider))


def _correlation_bucket(name: str) -> str:
    for bucket, prefixes in CORRELATION_BUCKETS.items():
        for prefix in prefixes:
            if name.startswith(prefix):
                return bucket
    return "other"


def _bayesian_weight(tracker: Optional[SignalTracker], provider_name: str) -> float:
    """Compute Bayesian-smoothed weight for a provider.

    Uses Beta(1 + wins, 1 + losses) posterior.
    Prior = Beta(1, 1) → uniform [0, 1].

    Returns weight in [0.1, 3.0] where:
        1.0 = no track record (default)
        >1.5 = proven performer
        <0.5 = poor track record
    """
    if tracker is None:
        return 1.0  # No tracker — equal weight

    wr = tracker.win_rate(provider_name, window=30)
    if wr <= 0:
        return 1.0  # No closed trades yet

    # Beta posterior: alpha = wins + 1, beta = losses + 1
    alpha = wr * 30 + 1  # approximate from window
    beta_param = (1 - wr) * 30 + 1
    posterior_mean = alpha / (alpha + beta_param)

    # Map posterior mean [0, 1] to weight [0.1, 3.0]
    # Center at 1.0 for posterior = 0.5
    if posterior_mean > 0.5:
        weight = 1.0 + (posterior_mean - 0.5) * 4.0  # max 3.0 at 1.0
    else:
        weight = 0.1 + posterior_mean * 1.8  # min 0.1 at 0.0

    return min(3.0, max(0.1, weight))


# ── Main aggregator ───────────────────────────────────────────────────


def aggregate(symbol="EURUSD", ctx: Optional[CausalContext] = None,
              tracker: Optional[SignalTracker] = None,
              providers: Optional[list] = None):
    """Multi-provider vote aggregation with Bayesian weights + correlation cap.

    Args:
        symbol: Trading symbol to vote on.
        ctx: Optional CausalContext for macro bias.
        tracker: Optional SignalTracker for performance-based weights.
        providers: Optional provider list override. Defaults to ALL_PROVIDERS.

    Returns:
        dict with keys: bias, confidence, votes, total_conf, weights_used.
    """
    provider_list = providers if providers is not None else ALL_PROVIDERS
    votes = []
    results = []

    # ── DXY macro context ────────────────────────────────────────────────
    context_boost = {"buy": 1.0, "sell": 1.0}
    dxy_trend = "unknown"
    dxy_price = "?"
    try:
        from quant_nanggroe.hedge_fund.tools.market_context import (
            get_currency_strength,
            get_dxy,
        )
        dxy = get_dxy()
        dxy_trend = dxy.get("trend", "unknown")
        dxy_price = dxy.get("price", "?")
        _ = get_currency_strength()

        if dxy_trend == "bull":
            context_boost["buy"] *= 0.85
            log.info("  DXY bull ($%s) -> buy confidence x0.85", dxy_price)
        elif dxy_trend == "bear":
            context_boost["sell"] *= 0.85
            log.info("  DXY bear ($%s) -> sell confidence x0.85", dxy_price)
    except Exception as e:
        log.debug("Market context unavailable: %s", e)

    # ── Parallel execution ──────────────────────────────────────────────
    n_providers = len(provider_list)
    max_workers = min(40, n_providers)
    log.info("  Parallel voting: %d providers via %d workers", n_providers, max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        fut_to_provider = {
            executor.submit(provider, symbol, ctx=ctx): provider
            for provider in provider_list
        }
        for future in as_completed(fut_to_provider, timeout=45):
            provider = fut_to_provider[future]
            p_name = _provider_name(provider)
            try:
                v = future.result(timeout=8)
                results.append(v)
                if v["bias"] != "neutral":
                    # Apply DXY context boost
                    v["confidence"] = v.get("confidence", DEFAULT_CONFIDENCE) * context_boost.get(v["bias"], 1.0)
                    v["confidence"] = min(v["confidence"], 1.0)
                    votes.append(v)
                    log.info("  %s: %s (conf=%.2f)", v["source"], v["bias"], v["confidence"])
                else:
                    log.info("  %s: neutral", v["source"])
            except Exception as e:
                log.warning("  %s: %s", p_name, e)

    if not votes:
        log.warning("  No providers voted — staying neutral")
        return {"bias": "neutral", "confidence": 0, "votes": [],
                "context_used": dxy_trend}

    # ── Bayesian performance-weighted aggregation ──────────────────────
    bucket_weights: dict[str, float] = defaultdict(float)
    bucket_votes: dict[str, list[dict]] = defaultdict(list)
    provider_weights: dict[str, float] = {}

    for v in votes:
        p_name = v.get("source", "unknown")
        bucket = _correlation_bucket(p_name)
        weight = _bayesian_weight(tracker, p_name)
        provider_weights[p_name] = weight

        # Apply correlation cap per bucket
        cumulative = bucket_weights[bucket] + weight
        max_bucket_weight = 0.15  # no single bucket exceeds 15% of total pool

        # Core strategy providers get a higher bucket cap
        if bucket == "external":
            max_bucket_weight = MAX_CORE_WEIGHT_FRACTION

        if cumulative > max_bucket_weight:
            weight = max(0, max_bucket_weight - bucket_weights[bucket])
            if weight <= 0:
                continue  # bucket saturated — skip this provider's vote

        bucket_weights[bucket] += weight
        bucket_votes[bucket].append({**v, "_weight": weight})

    # ── Aggregate by direction ─────────────────────────────────────────
    buy_conf = 0.0
    sell_conf = 0.0
    total_weight = 0.0
    detailed_votes = []

    for bucket, b_votes in bucket_votes.items():
        for v in b_votes:
            w = v["_weight"]
            conf = v.get("confidence", DEFAULT_CONFIDENCE)
            weighted = w * conf
            if v["bias"] == "buy":
                buy_conf += weighted
            elif v["bias"] == "sell":
                sell_conf += weighted
            total_weight += w
            detailed_votes.append({
                "source": v["source"],
                "bias": v["bias"],
                "confidence": conf,
                "weight": round(w, 4),
                "bucket": bucket,
            })

    # ── Final decision ─────────────────────────────────────────────────
    log.info("  Bayesian-weighted: buy=%.2f sell=%.2f total_weight=%.2f",
             buy_conf, sell_conf, total_weight)

    if total_weight <= 0:
        return {"bias": "neutral", "confidence": 0, "votes": detailed_votes,
                "total_conf": 0}

    buy_score = buy_conf / total_weight
    sell_score = sell_conf / total_weight

    # CONFIDENCE_THRESHOLD gate from constitutional risk constants
    if buy_score > sell_score and buy_score >= CONFIDENCE_THRESHOLD:
        bias = "buy"
        confidence = buy_score
    elif sell_score > buy_score and sell_score >= CONFIDENCE_THRESHOLD:
        bias = "sell"
        confidence = sell_score
    else:
        bias = "neutral"
        confidence = max(buy_score, sell_score)
        log.info("  Confidence %.2f below threshold %.2f — staying neutral",
                 confidence, CONFIDENCE_THRESHOLD)

    result = {
        "bias": bias,
        "confidence": min(confidence, 1.0),
        "votes": detailed_votes,
        "total_conf": buy_score + sell_score,
        "weights_used": provider_weights,
        "dxy_trend": dxy_trend,
    }

    # ── CSV logging ────────────────────────────────────────────────────
    try:
        needs_header = not VOTE_LOG.exists() or VOTE_LOG.stat().st_size == 0
        with open(VOTE_LOG, 'a', newline='') as f:
            w = csv.writer(f)
            if needs_header:
                w.writerow(["time", "symbol", "buy_conf", "sell_conf",
                            "total_weight", "n_votes", "result", "dxy"])
            n_votes = len(detailed_votes)
            w.writerow([
                datetime.now().isoformat(),
                symbol,
                round(buy_score, 4),
                round(sell_score, 4),
                round(total_weight, 2),
                n_votes,
                bias,
                dxy_price,
            ])
    except Exception as e:
        log.debug("Vote log write failed: %s", e)

    return result
