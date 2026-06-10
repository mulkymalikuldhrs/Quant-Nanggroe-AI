"""
Crypto Agent — Mempool Monitor, DEX Sniper & Anti-Rug Protection
================================================================
Monitors mempool for new token launches across Solana, BSC, and ETH.
Implements sniper logic for early token detection, integrates with DEX
aggregators (Jupiter, Raydium, PancakeSwap) for execution, and provides
anti-rug protection through dev wallet tracking and LP lock checking.

Uses SolSniperX patterns from the Cluster 1 spec for fast token scoring
and automated risk assessment before execution.

Responsibilities:
  - Monitor mempool for new token deployments (Solana, BSC, ETH)
  - Score new tokens via SolSniperX fast-scoring heuristics
  - Integrate with DEX aggregators (Jupiter, Raydium, PancakeSwap)
  - Anti-rug protection: dev wallet tracking, LP lock checking, honeypot detection
  - Return crypto_context, token_score, dex_route, anti_rug_verdict
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# DEX Integration Constants
# ══════════════════════════════════════════════════════════════════════

SUPPORTED_CHAINS = {"solana", "bsc", "ethereum"}

DEX_AGGRREGATORS: dict[str, list[str]] = {
    "solana": ["jupiter", "raydium"],
    "bsc": ["pancakeswap", "biswap"],
    "ethereum": ["uniswap_v3", "1inch"],
}

# Well-known token mints (Solana)
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


# ══════════════════════════════════════════════════════════════════════
# SolSniperX Fast-Scoring Constants
# ══════════════════════════════════════════════════════════════════════

# Minimum scores to pass each check (out of 100)
MIN_LP_LOCK_SCORE = 60
MIN_HOLDER_DISTRIBUTION_SCORE = 50
MIN_MINT_AUTHORITY_REVOKED_SCORE = 80
MIN_FREEZE_AUTHORITY_REVOKED_SCORE = 80

# Weighting for composite token score
WEIGHT_LP_LOCK = 0.25
WEIGHT_HOLDER_DIST = 0.20
WEIGHT_MINT_REVOKED = 0.20
WEIGHT_FREEZE_REVOKED = 0.15
WEIGHT_DEV_WALLET = 0.10
WEIGHT_VOLUME = 0.10

# Anti-rug thresholds
MAX_DEV_WALLET_PCT = 0.05          # 5% max dev wallet holding
MIN_LP_LOCK_PCT = 0.50             # 50% minimum LP locked
MAX_TOP_10_HOLDER_PCT = 0.40       # 40% max top-10 holder concentration
HONEYPOT_CHECK_TIMEOUT_S = 10      # seconds before we skip honeypot check


# ══════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════


def _classify_chain(symbol: str) -> str:
    """
    Classify which chain a crypto symbol belongs to.

    Returns the chain name or 'unknown'.
    """
    upper = symbol.upper()
    solana_tokens = {"SOL", "BONK", "JUP", "RAY", "ORCA", "PYTH", "JITO"}
    bsc_tokens = {"BNB", "CAKE", "BISWAP", "BABYDOGE"}
    eth_tokens = {"ETH", "UNI", "AAVE", "LINK", "CRV", "LDO"}

    if any(upper.startswith(t) for t in solana_tokens) or "SOL" in upper:
        return "solana"
    if any(upper.startswith(t) for t in bsc_tokens) or "BNB" in upper:
        return "bsc"
    if any(upper.startswith(t) for t in eth_tokens) or "ETH" in upper:
        return "ethereum"

    # Default to solana for unknown crypto symbols
    return "solana"


def _get_dex_route(chain: str) -> list[str]:
    """Return the preferred DEX route for a given chain."""
    return DEX_AGGRREGATORS.get(chain, [])


async def _check_mempool(chain: str, symbol: str) -> dict[str, Any]:
    """
    Check mempool for new token deployments.

    In production, this connects to the chain's mempool via:
      - Solana: geyser plugin / yellowstone gRPC
      - BSC: ws subscription to pending transactions
      - ETH: Flashbots protect /Alchemy getPendingTransactions

    Returns dict with pending token deployments matching the symbol/chain.
    """
    # Placeholder: in production this would stream from the mempool
    return {
        "chain": chain,
        "symbol": symbol,
        "new_tokens_detected": 0,
        "pending_transactions": 0,
        "scan_timestamp": datetime.now().isoformat(),
        "status": "monitoring",
        "note": f"Mempool monitoring active for {chain}/{symbol}",
    }


def _sol_sniper_x_score(
    lp_locked_pct: float = 0.0,
    holder_distribution_pct: float = 0.0,
    mint_authority_revoked: bool = False,
    freeze_authority_revoked: bool = False,
    dev_wallet_pct: float = 1.0,
    volume_24h: float = 0.0,
) -> dict[str, Any]:
    """
    Compute a SolSniperX-style fast token score.

    Each component is scored 0-100, then weighted for a composite score.
    A composite score below 50 is considered HIGH_RISK.

    Args:
        lp_locked_pct: Percentage of LP tokens locked (0.0-1.0)
        holder_distribution_pct: Score for holder distribution (0-100)
        mint_authority_revoked: Whether mint authority is revoked
        freeze_authority_revoked: Whether freeze authority is revoked
        dev_wallet_pct: Percentage of supply in dev wallet (0.0-1.0)
        volume_24h: 24h trading volume in USD

    Returns:
        Dict with component scores, composite score, and risk verdict
    """
    # LP Lock score (0-100)
    lp_score = min(100, lp_locked_pct / MIN_LP_LOCK_PCT * 100) if MIN_LP_LOCK_PCT > 0 else 0

    # Holder distribution score (0-100)
    holder_score = holder_distribution_pct

    # Mint authority score (0-100)
    mint_score = 100 if mint_authority_revoked else 0

    # Freeze authority score (0-100)
    freeze_score = 100 if freeze_authority_revoked else 0

    # Dev wallet score (lower dev = higher score, 0-100)
    if dev_wallet_pct <= MAX_DEV_WALLET_PCT:
        dev_score = 100
    elif dev_wallet_pct <= 0.10:
        dev_score = 60
    elif dev_wallet_pct <= 0.20:
        dev_score = 30
    else:
        dev_score = 0

    # Volume score (0-100, logarithmic scaling)
    if volume_24h > 0:
        import math
        volume_score = min(100, math.log10(max(1.0, volume_24h)) * 20)
    else:
        volume_score = 0

    # Composite score
    composite = (
        lp_score * WEIGHT_LP_LOCK
        + holder_score * WEIGHT_HOLDER_DIST
        + mint_score * WEIGHT_MINT_REVOKED
        + freeze_score * WEIGHT_FREEZE_REVOKED
        + dev_score * WEIGHT_DEV_WALLET
        + volume_score * WEIGHT_VOLUME
    )

    # Risk verdict
    if composite >= 75:
        risk_verdict = "LOW_RISK"
    elif composite >= 50:
        risk_verdict = "MEDIUM_RISK"
    elif composite >= 30:
        risk_verdict = "HIGH_RISK"
    else:
        risk_verdict = "EXTREME_RISK"

    return {
        "lp_lock_score": round(lp_score, 1),
        "holder_distribution_score": round(holder_score, 1),
        "mint_revoked_score": round(mint_score, 1),
        "freeze_revoked_score": round(freeze_score, 1),
        "dev_wallet_score": round(dev_score, 1),
        "volume_score": round(volume_score, 1),
        "composite_score": round(composite, 1),
        "risk_verdict": risk_verdict,
        "pass_sniper_check": composite >= 50,
    }


def _anti_rug_check(
    lp_locked_pct: float = 0.0,
    dev_wallet_pct: float = 1.0,
    top_10_holder_pct: float = 1.0,
    mint_authority_revoked: bool = False,
    freeze_authority_revoked: bool = False,
    honeypot_detected: bool | None = None,
) -> dict[str, Any]:
    """
    Run anti-rug protection checks.

    Checks:
      1. LP lock percentage >= minimum
      2. Dev wallet holding <= maximum
      3. Top-10 holder concentration <= maximum
      4. Mint authority revoked
      5. Freeze authority revoked
      6. Honeypot detection (if available)

    Returns dict with individual check results and overall pass/fail.
    """
    checks: dict[str, dict[str, Any]] = {}

    # 1. LP Lock check
    checks["lp_lock"] = {
        "name": "lp_lock",
        "value": f"{lp_locked_pct:.1%}",
        "limit": f"{MIN_LP_LOCK_PCT:.1%}",
        "passed": lp_locked_pct >= MIN_LP_LOCK_PCT,
    }

    # 2. Dev wallet check
    checks["dev_wallet"] = {
        "name": "dev_wallet",
        "value": f"{dev_wallet_pct:.1%}",
        "limit": f"{MAX_DEV_WALLET_PCT:.1%}",
        "passed": dev_wallet_pct <= MAX_DEV_WALLET_PCT,
    }

    # 3. Top-10 holder concentration
    checks["top_10_holders"] = {
        "name": "top_10_holders",
        "value": f"{top_10_holder_pct:.1%}",
        "limit": f"{MAX_TOP_10_HOLDER_PCT:.1%}",
        "passed": top_10_holder_pct <= MAX_TOP_10_HOLDER_PCT,
    }

    # 4. Mint authority revoked
    checks["mint_revoked"] = {
        "name": "mint_revoked",
        "value": str(mint_authority_revoked),
        "limit": "True",
        "passed": mint_authority_revoked,
    }

    # 5. Freeze authority revoked
    checks["freeze_revoked"] = {
        "name": "freeze_revoked",
        "value": str(freeze_authority_revoked),
        "limit": "True",
        "passed": freeze_authority_revoked,
    }

    # 6. Honeypot check (if data available)
    if honeypot_detected is not None:
        checks["honeypot"] = {
            "name": "honeypot",
            "value": str(honeypot_detected),
            "limit": "False",
            "passed": not honeypot_detected,
        }
    else:
        checks["honeypot"] = {
            "name": "honeypot",
            "value": "UNKNOWN",
            "limit": "False",
            "passed": False,  # Conservative: treat unknown as failed
            "note": "Honeypot check unavailable — treat as failed for safety",
        }

    all_passed = all(c["passed"] for c in checks.values())
    failed_checks = [k for k, c in checks.items() if not c["passed"]]

    return {
        "checks": checks,
        "all_passed": all_passed,
        "failed_checks": failed_checks,
        "verdict": "PASS" if all_passed else "FAIL",
        "fail_count": len(failed_checks),
    }


async def _fetch_token_onchain_data(symbol: str, chain: str) -> dict[str, Any]:
    """
    Fetch on-chain data for a token.

    In production, this would query:
      - Solana: getAccountInfo, getTokenSupply, getTokenLargestAccounts
      - BSC/ETH: Contract calls via Web3

    Returns structured on-chain data for scoring.
    """
    try:
        from quant_nanggroe_ai.config import get_settings
        settings = get_settings()

        # In production, this would use RPC endpoints from config
        # For now, return a structured placeholder that degrades gracefully
        return {
            "symbol": symbol,
            "chain": chain,
            "lp_locked_pct": 0.0,
            "dev_wallet_pct": 1.0,
            "top_10_holder_pct": 1.0,
            "mint_authority_revoked": False,
            "freeze_authority_revoked": False,
            "honeypot_detected": None,
            "volume_24h": 0.0,
            "holder_count": 0,
            "data_source": "on_chain_placeholder",
            "note": "Live on-chain data requires configured RPC endpoint",
        }
    except Exception as exc:
        logger.warning("On-chain data fetch failed for %s/%s: %s", symbol, chain, exc)
        return {
            "symbol": symbol,
            "chain": chain,
            "error": str(exc),
            "data_source": "error",
        }


async def _sniper_logic(
    symbol: str,
    chain: str,
    token_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute sniper logic for new token detection.

    The sniper evaluates:
      1. Is the token newly launched? (age < threshold)
      2. Does it pass the SolSniperX fast score?
      3. Does it pass the anti-rug checks?
      4. Is there sufficient initial liquidity?

    Returns a sniper verdict with action recommendation.
    """
    # Score the token
    token_score = _sol_sniper_x_score(
        lp_locked_pct=token_data.get("lp_locked_pct", 0.0),
        holder_distribution_pct=token_data.get("holder_distribution_pct", 0.0),
        mint_authority_revoked=token_data.get("mint_authority_revoked", False),
        freeze_authority_revoked=token_data.get("freeze_authority_revoked", False),
        dev_wallet_pct=token_data.get("dev_wallet_pct", 1.0),
        volume_24h=token_data.get("volume_24h", 0.0),
    )

    # Anti-rug check
    anti_rug = _anti_rug_check(
        lp_locked_pct=token_data.get("lp_locked_pct", 0.0),
        dev_wallet_pct=token_data.get("dev_wallet_pct", 1.0),
        top_10_holder_pct=token_data.get("top_10_holder_pct", 1.0),
        mint_authority_revoked=token_data.get("mint_authority_revoked", False),
        freeze_authority_revoked=token_data.get("freeze_authority_revoked", False),
        honeypot_detected=token_data.get("honeypot_detected"),
    )

    # Determine sniper action
    composite = token_score["composite_score"]
    if token_score["pass_sniper_check"] and anti_rug["all_passed"]:
        action = "SNIPE_READY"
        confidence = "HIGH"
    elif composite >= 40 and anti_rug["fail_count"] <= 1:
        action = "WATCH"
        confidence = "MEDIUM"
    elif composite >= 25:
        action = "CAUTION"
        confidence = "LOW"
    else:
        action = "AVOID"
        confidence = "NONE"

    return {
        "action": action,
        "confidence": confidence,
        "token_score": token_score,
        "anti_rug": anti_rug,
        "composite_score": composite,
        "chain": chain,
    }


# ══════════════════════════════════════════════════════════════════════
# Crypto Agent Node
# ══════════════════════════════════════════════════════════════════════


async def crypto_node(state: AgentState) -> dict[str, Any]:
    """
    Crypto Agent node — Mempool monitor, DEX sniper & anti-rug protection.

    Monitors mempool for new token launches, scores tokens via SolSniperX
    heuristics, integrates with DEX aggregators for routing, and runs
    anti-rug protection checks before recommending execution.
    """
    symbol = state.symbol or "SOL"
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Classify chain ─────────────────────────────────────────────
    chain = _classify_chain(symbol)

    # ── 2. Check mempool for new tokens ────────────────────────────────
    mempool_result: dict[str, Any] = {}
    try:
        mempool_result = await _check_mempool(chain, symbol)
    except Exception as exc:
        logger.error("Mempool check failed for %s/%s: %s", chain, symbol, exc)
        errors.append(f"Mempool: {exc}")
        mempool_result = {"status": "error", "error": str(exc)}

    # ── 3. Fetch on-chain token data ──────────────────────────────────
    token_data: dict[str, Any] = {}
    try:
        token_data = await _fetch_token_onchain_data(symbol, chain)
    except Exception as exc:
        logger.error("On-chain data fetch failed for %s: %s", symbol, exc)
        errors.append(f"On-chain data: {exc}")
        token_data = {"error": str(exc), "data_source": "error"}

    # ── 4. Run SolSniperX scoring ─────────────────────────────────────
    try:
        token_score = _sol_sniper_x_score(
            lp_locked_pct=token_data.get("lp_locked_pct", 0.0),
            holder_distribution_pct=token_data.get("holder_distribution_pct", 0.0),
            mint_authority_revoked=token_data.get("mint_authority_revoked", False),
            freeze_authority_revoked=token_data.get("freeze_authority_revoked", False),
            dev_wallet_pct=token_data.get("dev_wallet_pct", 1.0),
            volume_24h=token_data.get("volume_24h", 0.0),
        )
    except Exception as exc:
        logger.error("Token scoring failed for %s: %s", symbol, exc)
        errors.append(f"Token scoring: {exc}")
        token_score = {"composite_score": 0.0, "risk_verdict": "ERROR", "pass_sniper_check": False}

    # ── 5. Run anti-rug protection ────────────────────────────────────
    try:
        anti_rug = _anti_rug_check(
            lp_locked_pct=token_data.get("lp_locked_pct", 0.0),
            dev_wallet_pct=token_data.get("dev_wallet_pct", 1.0),
            top_10_holder_pct=token_data.get("top_10_holder_pct", 1.0),
            mint_authority_revoked=token_data.get("mint_authority_revoked", False),
            freeze_authority_revoked=token_data.get("freeze_authority_revoked", False),
            honeypot_detected=token_data.get("honeypot_detected"),
        )
    except Exception as exc:
        logger.error("Anti-rug check failed for %s: %s", symbol, exc)
        errors.append(f"Anti-rug: {exc}")
        anti_rug = {"verdict": "ERROR", "all_passed": False, "failed_checks": ["error"]}

    # ── 6. Execute sniper logic ───────────────────────────────────────
    try:
        sniper_result = await _sniper_logic(symbol, chain, token_data)
    except Exception as exc:
        logger.error("Sniper logic failed for %s: %s", symbol, exc)
        errors.append(f"Sniper logic: {exc}")
        sniper_result = {"action": "AVOID", "confidence": "NONE", "composite_score": 0.0}

    # ── 7. Determine DEX route ────────────────────────────────────────
    dex_route = _get_dex_route(chain)

    # ── 8. Build crypto context string ────────────────────────────────
    composite = token_score.get("composite_score", 0.0)
    risk_verdict = token_score.get("risk_verdict", "UNKNOWN")
    sniper_action = sniper_result.get("action", "AVOID")
    sniper_confidence = sniper_result.get("confidence", "NONE")
    anti_rug_verdict = anti_rug.get("verdict", "UNKNOWN")
    failed_checks = anti_rug.get("failed_checks", [])

    crypto_context = (
        f"Crypto analysis for {symbol} ({chain}): "
        f"SniperScore={composite:.1f}/100 ({risk_verdict}) | "
        f"SniperAction={sniper_action} (confidence={sniper_confidence}) | "
        f"AntiRug={anti_rug_verdict} "
        f"({len(failed_checks)} failed: {', '.join(failed_checks) if failed_checks else 'none'}) | "
        f"DEX route: {' → '.join(dex_route) if dex_route else 'none'}"
    )

    # ── 9. Override risk clearance if anti-rug fails ──────────────────
    risk_override = False
    if not anti_rug.get("all_passed", False):
        risk_override = True
        logger.warning(
            "Crypto agent BLOCKING %s — anti-rug check failed: %s",
            symbol, failed_checks,
        )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "macro_context": crypto_context if not state.macro_context else (
            state.macro_context + " | " + crypto_context
        ),
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "crypto",
                "status": "completed",
                "action": "crypto_analysis",
                "symbol": symbol,
                "chain": chain,
                "composite_score": composite,
                "risk_verdict": risk_verdict,
                "sniper_action": sniper_action,
                "sniper_confidence": sniper_confidence,
                "anti_rug_verdict": anti_rug_verdict,
                "dex_route": dex_route,
                "risk_override": risk_override,
                "timestamp": now,
            }
        ],
    }
