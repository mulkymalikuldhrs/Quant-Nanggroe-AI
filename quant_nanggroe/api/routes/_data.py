"""Synthetic data providers for stub API modules. (ponytail: replaces 8 inline generators)"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

random.seed(42)

_TOP_EVENTS = [
    ("US-China Trade Tariff Review", "trade", "high", "North America"),
    ("EU Energy Security Summit", "energy", "medium", "Europe"),
    ("Middle East Diplomatic Talks", "diplomacy", "critical", "Middle East"),
    ("ASEAN Regional Forum", "diplomacy", "low", "Southeast Asia"),
    ("South China Sea Patrol Incidents", "military", "high", "Southeast Asia"),
]
_SANCTIONS = [
    ("Russia", "finance", "OFAC", "active"),
    ("Iran", "energy", "UN", "active"),
    ("North Korea", "arms", "UN", "active"),
    ("Venezuela", "oil", "OFAC", "active"),
    ("Myanmar", "trade", "EU", "active"),
]


def geopolitics_events(count: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "id": f"geo-{i}",
            "title": title,
            "category": cat,
            "severity": sev,
            "region": reg,
            "date": (datetime.now(timezone.utc) - timedelta(days=i * 7)).isoformat(),
        }
        for i, (title, cat, sev, reg) in enumerate(_TOP_EVENTS[:count])
    ]


def geopolitics_sanctions(count: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "id": f"san-{i}",
            "target": tgt,
            "sector": sec,
            "authority": auth,
            "status": st,
            "imposed": (datetime.now(timezone.utc) - timedelta(days=30 * (i + 1))).isoformat(),
        }
        for i, (tgt, sec, auth, st) in enumerate(_SANCTIONS[:count])
    ]


def geopolitics_regions() -> list[dict[str, Any]]:
    return [
        {"region": "Southeast Asia", "risk": "medium", "trend": "stable", "score": 45},
        {"region": "Middle East", "risk": "high", "trend": "deteriorating", "score": 72},
        {"region": "Eastern Europe", "risk": "high", "trend": "stable", "score": 68},
        {"region": "East Asia", "risk": "medium", "trend": "escalating", "score": 55},
        {"region": "Western Europe", "risk": "low", "trend": "improving", "score": 22},
    ]


_PERSONAS = [
    ("The Whale", "institutional", 1_000_000, 0.6, "trend_following"),
    ("Scalper Sara", "retail", 10_000, 0.3, "mean_reversion"),
    ("Hedge Harry", "hedge_fund", 50_000_000, 0.5, "momentum"),
    ("Yield Yuki", "defi", 100_000, 0.4, "yield_farming"),
    ("Arbitrage Art", "proprietary", 5_000_000, 0.2, "arbitrage"),
]


def personas_list() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "type": typ,
            "capital": cap,
            "max_drawdown": dd,
            "strategy": strat,
            "active": True,
        }
        for name, typ, cap, dd, strat in _PERSONAS
    ]


_COUNCIL_VOTES = [
    ("QIP-104", "Increase leverage cap to 3x", "passed", 8, 2, 1),
    ("QIP-105", "Add SOL lending market", "pending", 0, 0, 11),
    ("QIP-106", "Reduce protocol fee to 0.05%", "passed", 9, 1, 1),
    ("QIP-107", "Emergency circuit breaker threshold", "failed", 3, 6, 2),
    ("QIP-108", "Stablecoin collateral expansion", "passed", 10, 0, 1),
]


def council_list() -> list[dict[str, Any]]:
    return [
        {
            "proposal_id": pid,
            "title": t,
            "status": st,
            "votes_for": fv,
            "votes_against": ag,
            "votes_abstain": ab,
            "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
        for pid, t, st, fv, ag, ab in _COUNCIL_VOTES
    ]


_DEBATES = [
    ("btc-vs-eth", "BTC vs ETH: Which is the better store of value?", 12),
    ("defi-vs-tradfi", "DeFi vs TradFi yield comparison", 8),
    ("layer2-future", "Layer 2 solutions — will they fragment liquidity?", 15),
    ("stablecoin-risk", "Algorithmic stablecoins — systemic risk?", 10),
]


def debate_list() -> list[dict[str, Any]]:
    return [
        {
            "id": sid,
            "topic": t,
            "participants": p,
            "status": "active",
            "created": (datetime.now(timezone.utc) - timedelta(hours=i * 12)).isoformat(),
        }
        for i, (sid, t, p) in enumerate(_DEBATES)
    ]


_FRED_SERIES = [
    ("GDP", "Gross Domestic Product", "B", "5.2"),
    ("CPIAUCSL", "Consumer Price Index", "I", "3.4"),
    ("UNRATE", "Unemployment Rate", "%", "3.7"),
    ("FEDFUNDS", "Federal Funds Rate", "%", "5.50"),
    ("T10YIE", "10-Year Breakeven Inflation", "%", "2.35"),
]


def fred_series() -> list[dict[str, Any]]:
    return [
        {
            "id": sid,
            "title": t,
            "unit": u,
            "latest_value": v,
            "updated": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }
        for sid, t, u, v in _FRED_SERIES
    ]


_SEC_FILINGS = [
    ("AAPL", "10-Q", "2025-01-15"),
    ("MSFT", "10-K", "2025-01-28"),
    ("NVDA", "8-K", "2025-02-01"),
    ("TSLA", "10-Q", "2025-01-20"),
    ("GOOGL", "10-Q", "2025-01-22"),
]


def sec_filings() -> list[dict[str, Any]]:
    return [
        {
            "ticker": t,
            "form": f,
            "filed": d,
            "description": f"{t} {f} filing",
        }
        for t, f, d in _SEC_FILINGS
    ]


_SIGNALS = [
    ("BTCUSDT", "long", "momentum_breakout", 0.82, 67500),
    ("ETHUSDT", "long", "ema_cross", 0.74, 3450),
    ("SOLUSDT", "short", "overbought_rsi", 0.65, 125),
    ("DOGEUSDT", "neutral", "range_bound", 0.50, 0.085),
]


def signals_list() -> list[dict[str, Any]]:
    return [
        {
            "id": f"sig-{i}",
            "symbol": s,
            "direction": d,
            "strategy": strat,
            "confidence": conf,
            "entry_price": price,
            "generated": (datetime.now(timezone.utc) - timedelta(minutes=i * 15)).isoformat(),
        }
        for i, (s, d, strat, conf, price) in enumerate(_SIGNALS)
    ]


_OPTIONS_POSITIONS = [
    ("AAPL", "call", 220, "2025-03-21", 3.45),
    ("TSLA", "put", 180, "2025-02-14", 2.10),
    ("SPY", "call", 480, "2025-06-20", 8.75),
    ("NVDA", "call", 150, "2025-04-17", 5.20),
]


def options_positions() -> list[dict[str, Any]]:
    return [
        {
            "symbol": s,
            "type": t,
            "strike": strike,
            "expiry": exp,
            "premium": prem,
            "quantity": random.randint(1, 20),
        }
        for s, t, strike, exp, prem in _OPTIONS_POSITIONS
    ]
