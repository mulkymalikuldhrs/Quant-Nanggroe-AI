"""Bitcoin On-Chain Metrics Provider — hashrate, difficulty, fees, halving.

Ported from TradeBobbyTerminal/dashboard/onchain-btc.js.
Uses blockchain.info/q/* (no API key) and mempool.space free APIs.
TTLCache 600s. Graceful fallback — never crashes.
"""
from __future__ import annotations

import json
import logging
import math
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=600)

BLOCKCHAIN_INFO = "https://blockchain.info/q"
MEMPOOL_SPACE = "https://mempool.space/api/v1"

HALVING_INTERVAL = 210000
BLOCK_TIME_MIN = 10
SECONDS_PER_DAY = 86400

def _txt(url: str, timeout: int = 10) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode().strip()
    except Exception as exc:
        logger.debug("txt fetch failed %s: %s", url, exc)
        return None

def _json(url: str, timeout: int = 10) -> Optional[Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("json fetch failed %s: %s", url, exc)
        return None


def _halving_info(block_height: int) -> dict[str, Any]:
    epoch = block_height // HALVING_INTERVAL
    next_halving_block = (epoch + 1) * HALVING_INTERVAL
    blocks_to_next = next_halving_block - block_height
    days_to_next = round((blocks_to_next * BLOCK_TIME_MIN) / (60 * 24), 1)
    current_subsidy = 50.0 / (2 ** epoch)
    est_date = None
    if days_to_next > 0:
        est_date = datetime.now(timezone.utc).isoformat()
    return {
        "epoch": epoch,
        "current_subsidy_btc": current_subsidy,
        "next_halving_block": next_halving_block,
        "blocks_remaining": blocks_to_next,
        "days_remaining": days_to_next,
        "est_date": est_date,
    }


def _classify_fee_state(fastest_fee: int) -> str:
    if fastest_fee > 100:
        return "CONGESTED"
    if fastest_fee > 30:
        return "BUSY"
    if fastest_fee > 10:
        return "NORMAL"
    return "CALM"


class OnChainBTCProvider:
    """Bitcoin on-chain metrics from blockchain.info + mempool.space.

    All values cached for 600s. Every method returns a dict with
    at minimum a ``source`` key and never raises.
    """

    def __init__(self) -> None:
        self._cache = _CACHE

    def get_onchain_data(self) -> dict[str, Any]:
        """Return all on-chain metrics in one dict.

        Fetches hashrate, difficulty, market cap, total BTC supply,
        block count, fee estimates, 3d hashrate trend, block interval,
        and halving countdown. Carries forward previous values on
        partial fetch failure.
        """
        cache_key = "onchain_all"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        hashrate = _txt(f"{BLOCKCHAIN_INFO}/hashrate")
        difficulty = _txt(f"{BLOCKCHAIN_INFO}/getdifficulty")
        marketcap = _txt(f"{BLOCKCHAIN_INFO}/marketcap")
        totalbc = _txt(f"{BLOCKCHAIN_INFO}/totalbc")
        block_height = _txt(f"{BLOCKCHAIN_INFO}/getblockcount")
        fees = _json(f"{MEMPOOL_SPACE}/fees/recommended")
        hashrate_history = _json(f"{MEMPOOL_SPACE}/mining/hashrate/3d")
        block_time = _txt(f"{BLOCKCHAIN_INFO}/interval")

        out: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hashrate_ghs": float(hashrate) if hashrate else None,
            "hashrate_ehs": round(float(hashrate) / 1e9, 2) if hashrate else None,
            "difficulty": float(difficulty) if difficulty else None,
            "market_cap_satoshi": float(marketcap) if marketcap else None,
            "total_btc_satoshis": float(totalbc) if totalbc else None,
            "total_btc": round(float(totalbc) / 1e8, 2) if totalbc else None,
            "block_height": int(block_height) if block_height else None,
            "avg_block_time_sec": float(block_time) if block_time else None,
        }

        all_null = all(out.get(k) is None for k in (
            "hashrate_ghs", "hashrate_ehs", "difficulty", "market_cap_satoshi",
            "total_btc_satoshis", "total_btc", "block_height", "avg_block_time_sec"))
        if all_null:
            logger.warning("OnChainBTCProvider: all fetches failed")
            out["source"] = "failed"
            self._cache.set(cache_key, out)
            return out

        if fees and isinstance(fees, dict):
            out["fees"] = {
                "fastest_sat_vb": fees.get("fastestFee"),
                "half_hour_sat_vb": fees.get("halfHourFee"),
                "hour_sat_vb": fees.get("hourFee"),
                "economy_sat_vb": fees.get("economyFee"),
            }

        if out.get("block_height") is not None:
            out["halving"] = _halving_info(out["block_height"])

        if hashrate_history and isinstance(hashrate_history, dict):
            rates = hashrate_history.get("hashrates")
            if isinstance(rates, list) and len(rates) > 0:
                recent = rates[-1].get("avgHashrate") if isinstance(rates[-1], dict) else None
                oldest = rates[0].get("avgHashrate") if isinstance(rates[0], dict) else None
                if recent and oldest:
                    out["hashrate_trend_pct_3d"] = round(((recent - oldest) / oldest) * 100, 2)

        if isinstance(out.get("fees"), dict):
            fastest = out["fees"].get("fastest_sat_vb")
            if fastest is not None:
                out["fee_state"] = _classify_fee_state(fastest)

        out["source"] = "blockchain.info+mempool.space"
        self._cache.set(cache_key, out)
        return out

    def get_fees(self) -> dict[str, Any]:
        """Return fee estimates with state classification.

        Keys: fastest_sat_vb, half_hour_sat_vb, hour_sat_vb,
        economy_sat_vb, state, source.
        """
        data = self.get_onchain_data()
        fees = data.get("fees")
        if not fees:
            return {
                "fastest_sat_vb": None, "half_hour_sat_vb": None,
                "hour_sat_vb": None, "economy_sat_vb": None,
                "state": "unknown", "source": "failed",
            }
        return {
            "fastest_sat_vb": fees.get("fastest_sat_vb"),
            "half_hour_sat_vb": fees.get("half_hour_sat_vb"),
            "hour_sat_vb": fees.get("hour_sat_vb"),
            "economy_sat_vb": fees.get("economy_sat_vb"),
            "state": data.get("fee_state", "unknown"),
            "source": data["source"],
        }

    def get_hashrate(self) -> dict[str, Any]:
        """Return current hashrate with 3d trend.

        Keys: hashrate_ghs, hashrate_ehs, trend_pct_3d, source.
        """
        data = self.get_onchain_data()
        return {
            "hashrate_ghs": data.get("hashrate_ghs"),
            "hashrate_ehs": data.get("hashrate_ehs"),
            "trend_pct_3d": data.get("hashrate_trend_pct_3d"),
            "source": data["source"],
        }

    def get_halving_countdown(self) -> dict[str, Any]:
        """Return halving countdown info.

        Keys: epoch, current_subsidy_btc, next_halving_block,
        blocks_remaining, days_remaining, estimated_date_utc, source.
        """
        data = self.get_onchain_data()
        halving = data.get("halving")
        if not halving:
            return {
                "epoch": None, "current_subsidy_btc": None,
                "next_halving_block": None, "blocks_remaining": None,
                "days_remaining": None, "estimated_date_utc": None,
                "source": "failed",
            }

        est_date_utc = None
        if halving.get("days_remaining") and halving["days_remaining"] > 0:
            from datetime import timedelta
            est_date_utc = (datetime.now(timezone.utc) + timedelta(days=halving["days_remaining"])).isoformat()

        return {
            "epoch": halving["epoch"],
            "current_subsidy_btc": halving["current_subsidy_btc"],
            "next_halving_block": halving["next_halving_block"],
            "blocks_remaining": halving["blocks_remaining"],
            "days_remaining": halving["days_remaining"],
            "estimated_date_utc": est_date_utc,
            "source": data["source"],
        }
