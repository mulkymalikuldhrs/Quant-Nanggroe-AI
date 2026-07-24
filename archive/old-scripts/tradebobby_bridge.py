#!/usr/bin/env python3
"""
tradebobby_bridge.py — TradeBobbyTerminal ↔ Hedge Fund Adapter

Bridge antara TradeBobby (Node.js web terminal :3333) dan hedge fund
pipeline Python (E:\\trading\\hedge_fund.py).

Fungsi:
1. Cek health TradeBobby daemon via HTTP
2. Fetch trade_brief.json (synthesis agent output)
3. Parse: risk_index, regime, top_setups
4. Convert confidence score → vote bias untuk hedge fund aggregator
5. Log vote ke data/votes.csv

Usage:
    python tradebobby_bridge.py              # One-shot scan + vote
    python tradebobby_bridge.py --watch      # Continuous loop
    python tradebobby_bridge.py --health     # Health check only

Requires: TradeBobby running at http://localhost:3333
"""
import sys
import json
import time
import logging
import csv
import os
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TRADEBOBBY_URL = "http://localhost:3333"
HEALTH_ENDPOINT = f"{TRADEBOBBY_URL}/api/health"
BRIEF_ENDPOINT = f"{TRADEBOBBY_URL}/api/trade-brief.json"
TIMEOUT = 10
WATCH_INTERVAL = 300  # 5 menit

SRC = Path(r"E:/trading")
VOTE_LOG = SRC / "data" / "votes.csv"
os.makedirs(SRC / "data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] tradebobby_bridge: %(message)s",
)
log = logging.getLogger("tradebobby_bridge")

# ─── SOURCE NAME ──────────────────────────────────────────────────────────────
SOURCE_NAME = "tradebobby"


# ─── HTTP HELPERS ─────────────────────────────────────────────────────────────
def http_get(url: str, timeout: int = TIMEOUT) -> dict | None:
    """GET JSON from URL, return parsed dict or None."""
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except HTTPError as e:
        log.warning("HTTP %d from %s", e.code, url)
        return None
    except (URLError, ConnectionRefusedError) as e:
        log.warning("Connection failed to %s: %s", url, e)
        return None
    except json.JSONDecodeError as e:
        log.warning("Invalid JSON from %s: %s", url, e)
        return None
    except Exception as e:
        log.error("Unexpected error fetching %s: %s", url, e)
        return None


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
def check_health() -> bool:
    """Check if TradeBobby is alive. Returns True if healthy."""
    data = http_get(HEALTH_ENDPOINT, timeout=5)
    if data is None:
        log.warning("❌ TradeBobby UNREACHABLE at %s", TRADEBOBBY_URL)
        return False

    status = data.get("status", "unknown")
    if status == "ok" or status == "degraded":
        log.info("✅ TradeBobby HEALTHY (status=%s)", status)
        return True

    log.warning("⚠️  TradeBobby status=%s", status)
    return False


# ─── FETCH SYNTHESIS BRIEF ────────────────────────────────────────────────────
def fetch_brief() -> dict | None:
    """Fetch trade-agent synthesis output."""
    data = http_get(BRIEF_ENDPOINT)
    if data is None:
        log.warning("Could not fetch trade brief from %s", BRIEF_ENDPOINT)
        return None
    log.info("📊 Trade brief fetched: risk_index=%s, regime=%s",
             data.get("risk_index"), data.get("regime"))
    return data


# ─── PARSE & CONVERT ──────────────────────────────────────────────────────────
def parse_setups(brief: dict) -> list[dict]:
    """Convert TradeBobby setups to hedge fund votes.

    TradeBobby setup confidence → vote bias mapping:
         9-10: buy/sell with confidence 0.85
         7-8:  buy/sell with confidence 0.70
         5-6:  buy/sell with confidence 0.50
         <5:   neutral
    """
    setups = brief.get("top_setups", [])
    if not setups:
        log.info("No top_setups in trade brief")
        return []

    votes = []
    for s in setups:
        symbol = s.get("symbol", "")
        direction = s.get("direction", "").lower()
        score = int(s.get("score", 0))

        if direction not in ("buy", "sell"):
            continue

        if score >= 9:
            confidence = 0.85
        elif score >= 7:
            confidence = 0.70
        elif score >= 5:
            confidence = 0.50
        else:
            confidence = 0.0

        votes.append({
            "source": SOURCE_NAME,
            "symbol": symbol,
            "bias": direction if confidence > 0 else "neutral",
            "confidence": confidence,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        })

    return votes


def parse_risk_vote(brief: dict) -> dict | None:
    """Convert risk_index menjadi risk gate recommendation.

    risk_index 0-100:
       0-25:  RISK ON → full size
       25-50: MILD → standard size
       50-75: CAUTIOUS → half size
       75-100: RISK OFF → skip trading
    """
    risk_idx = brief.get("risk_index")
    if risk_idx is None:
        return None

    if risk_idx < 25:
        recommendation = "full_size"
        risk_level = "low"
    elif risk_idx < 50:
        recommendation = "standard"
        risk_level = "mild"
    elif risk_idx < 75:
        recommendation = "half_size"
        risk_level = "cautious"
    else:
        recommendation = "skip"
        risk_level = "high"

    return {
        "source": SOURCE_NAME,
        "risk_index": risk_idx,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── VOTE LOGGING ─────────────────────────────────────────────────────────────
def log_votes(votes: list[dict]):
    """Append votes to votes.csv (hedge fund format)."""
    if not votes:
        log.info("No votes to log")
        return

    file_exists = VOTE_LOG.exists()
    fieldnames = ["timestamp", "source", "symbol", "bias", "confidence", "score"]

    try:
        with open(VOTE_LOG, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for v in votes:
                writer.writerow(v)
        log.info("✅ Logged %d vote(s) to %s", len(votes), VOTE_LOG)
    except Exception as e:
        log.error("Failed to write votes: %s", e)


def log_risk(risk: dict | None):
    """Log risk recommendation as comment line in votes.csv."""
    if risk is None:
        return
    try:
        with open(VOTE_LOG, "a") as f:
            f.write(f"# RISK: index={risk['risk_index']} level={risk['risk_level']} "
                    f"rec={risk['recommendation']} ts={risk['timestamp']}\n")
        log.info("✅ Risk recommendation logged: %s", risk["recommendation"])
    except Exception as e:
        log.error("Failed to log risk: %s", e)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def run_once() -> bool:
    """One scan cycle. Returns True if successful."""
    if not check_health():
        return False

    brief = fetch_brief()
    if brief is None:
        return False

    votes = parse_setups(brief)
    risk = parse_risk_vote(brief)

    log_votes(votes)
    log_risk(risk)

    summary = {
        "alive": True,
        "symbols_scanned": len(brief.get("top_setups", [])),
        "votes_generated": len(votes),
        "regime": brief.get("regime", "unknown"),
        "risk_index": brief.get("risk_index", "N/A"),
        "risk_recommendation": risk["recommendation"] if risk else "N/A",
    }
    log.info("Summary: %s", json.dumps(summary))
    return True


def watch_loop():
    """Continuous watch mode."""
    log.info("🔄 Watch mode started (interval=%ds)", WATCH_INTERVAL)
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            log.info("Stopped by user")
            break
        except Exception as e:
            log.error("Watch cycle error: %s", e)
        time.sleep(WATCH_INTERVAL)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch_loop()
    elif "--health" in sys.argv:
        alive = check_health()
        sys.exit(0 if alive else 1)
    else:
        success = run_once()
        sys.exit(0 if success else 1)
