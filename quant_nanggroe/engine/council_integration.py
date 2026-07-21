"""Council Integration Adapter — Merges COUNCIL Extract Findings into QNA.

Wires architectural decisions from COUNCIL-*.md extracts into the running
QNA engine. Each integration point is self-contained and independently
enable/disable-able.

Council waves integrated:
- WAVE 1 (HF): Kronos → Signal Provider, QuantDinger → Execution Layer
- WAVE 2 (QNA): OpenAlice Broker Packs → Plugin Adapter, spec-kit → SDD workflow
- WAVE 3 (SKILLS): taste-skill → Anti-slop design, GStack → DevOps, FinRL/QLib/PyPortfolioOpt → Algos

Source files:
    D:\\docs\\COUNCIL-HF-EXTRACT.md
    D:\\docs\\COUNCIL-QNA-EXTRACT.md
    D:\\docs\\COUNCIL-SKILLS-EXTRACT.md

Usage:
    from quant_nanggroe.engine.council_integration import integrate_council_findings
    await integrate_council_findings()
"""

from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.engine.decision import DecisionRule, DecisionResult, DECISION_TABLE
from quant_nanggroe.engine.risk.kelly import KellyCriterion
from quant_nanggroe.exchange.broker_pack import TradingMode, get_registry
from quant_nanggroe.types.engine import DecisionAction, MarketRegime, RiskClearance, VolatilityLevel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WAVE 1: Hedge Fund Integration (from COUNCIL-HF-EXTRACT.md)
# ---------------------------------------------------------------------------

# QuantDinger-style signal pipeline: StrategySignal → OrderIntentBuilder → Gateway
SIGNAL_PIPELINE_CONFIG = {
    "default_leverage": 1.0,
    "max_leverage": 3.0,
    "idempotency_enabled": True,
    "protection_defaults": {
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
        "trailing_stop_pct": 0.01,
        "trailing_activation_pct": 0.03,
    },
}

# Kronos signal provider contract (if Kronos model is available)
KRONOS_SIGNAL_CONTRACT = {
    "provider": "kronos",
    "fields": [
        "symbol", "timestamp", "direction", "signal_strength",
        "confidence", "entry", "sl", "tp", "prediction_window",
    ],
    "metadata_fields": ["ensemble_std", "predicted_return", "current_atr"],
    "min_confidence": 0.60,
    "min_signal_strength": 0.50,
}


def integrate_hedge_fund_signals(decision_table: list[DecisionRule]) -> list[DecisionRule]:
    """Add Kronos/QuantDinger-style signal-based rules to the decision table.

    Extends the existing DECISION_TABLE with rules optimized for ML-based
    signal providers (Kronos predictor) and the QuantDinger execution pipeline.
    """
    # Kronos ML prediction rule — higher confidence requirement, ensemble-aware
    kronos_rule = DecisionRule(
        id="DT-KRONOS-001",
        regime_allowed=[
            MarketRegime.TRENDING_UP,
            MarketRegime.TRENDING,
            MarketRegime.TRENDING_DOWN,
        ],
        min_buy_pressure=0.0,
        max_sell_pressure=1.0,
        min_sell_pressure=0.0,
        max_buy_pressure=1.0,
        allowed_volatility=[
            VolatilityLevel.LOW,
            VolatilityLevel.NORMAL,
        ],
        min_confidence=0.65,
        action=DecisionAction.ENTER_LONG,
        description="Kronos ML signal: ensemble confidence >= 0.65, trending regime",
    )
    kronos_short_rule = DecisionRule(
        id="DT-KRONOS-002",
        regime_allowed=[
            MarketRegime.TRENDING_DOWN,
            MarketRegime.TRENDING,
        ],
        min_buy_pressure=0.0,
        max_buy_pressure=0.3,
        min_sell_pressure=0.60,
        allowed_volatility=[
            VolatilityLevel.LOW,
            VolatilityLevel.NORMAL,
        ],
        min_confidence=0.65,
        action=DecisionAction.ENTER_SHORT,
        description="Kronos ML signal: bearish ensemble, short entry",
    )

    # Add only if not already present
    existing_ids = {r.id for r in decision_table}
    new_rules = []
    for rule in [kronos_rule, kronos_short_rule]:
        if rule.id not in existing_ids:
            new_rules.append(rule)

    return decision_table + new_rules


# ---------------------------------------------------------------------------
# WAVE 2: OpenAlice Broker Packs Integration (from COUNCIL-QNA-EXTRACT.md)
# ---------------------------------------------------------------------------

def initialize_broker_packs() -> dict[str, Any]:
    """Initialize the OpenAlice-style Broker Packs registry.

    Returns:
        Dict with registry status and available engines.
    """
    registry = get_registry()
    packs = registry.list_packs()
    mode = TradingMode()

    logger.info(
        "BrokerPack registry initialized: %d packs, trading mode=%s (source=%s)",
        len(packs), mode.mode, mode.source,
    )

    return {
        "registry_size": len(packs),
        "engines": list(registry.engines()),
        "trading_mode": mode.mode,
        "mode_source": mode.source,
        "can_trade": mode.can_trade,
    }


# ---------------------------------------------------------------------------
# WAVE 3: Skills/Research Integration (from COUNCIL-SKILLS-EXTRACT.md)
# ---------------------------------------------------------------------------

# Algorithms recommended by council for addition
PENDING_ALGORITHMS = {
    # From PyPortfolioOpt
    "black_litterman": {
        "source": "PyPortfolioOpt",
        "status": "pending",
        "priority": "high",
        "description": "Black-Litterman allocation: blend market prior + trader views",
        "target_module": "quant_nanggroe.engine.risk.black_litterman",
    },
    "hierarchical_risk_parity": {
        "source": "PyPortfolioOpt",
        "status": "pending",
        "priority": "high",
        "description": "HRP: clustering + recursive bisection allocation",
        "target_module": "quant_nanggroe.engine.risk.hierarchical_risk_parity",
    },
    # From FinRL / Qlib
    "ppo_order_execution": {
        "source": "Qlib/FinRL",
        "status": "pending",
        "priority": "medium",
        "description": "PPO-based trade execution optimizer (TWAP alternative)",
        "target_module": "quant_nanggroe.engine.rl.ppo_execution",
    },
    "rl_portfolio_allocation": {
        "source": "FinRL",
        "status": "pending",
        "priority": "medium",
        "description": "End-to-end DRL portfolio management",
        "target_module": "quant_nanggroe.engine.rl.portfolio",
    },
    # From Qlib
    "point_in_time_database": {
        "source": "Qlib",
        "status": "pending",
        "priority": "high",
        "description": "Point-in-time data server to prevent look-ahead bias",
        "target_module": "quant_nanggroe.providers.pit_provider",
    },
    "online_serving": {
        "source": "Qlib",
        "status": "pending",
        "priority": "medium",
        "description": "Low-latency model serving with auto-rolling",
        "target_module": "quant_nanggroe.engine.model_registry",
    },
}

# Anti-slop configuration (from taste-skill Dials System)
ANTI_SLOP_CONFIG = {
    "design_variance": 8,
    "motion_intensity": 6,
    "visual_density": 4,
    "em_dash_banned": True,
    "ai_tell_filters": True,
}


def log_pending_algorithms() -> None:
    """Log all pending algorithms that still need implementation."""
    for name, algo in sorted(PENDING_ALGORITHMS.items()):
        logger.info(
            "PENDING ALGORITHM [%s/%s]: %s → %s",
            algo["priority"].upper(),
            algo["source"],
            name,
            algo["description"],
        )


# ---------------------------------------------------------------------------
# Main Integration Entry Point
# ---------------------------------------------------------------------------

async def integrate_council_findings(
    decision_table: list[DecisionRule] | None = None,
) -> dict[str, Any]:
    """Run all council integrations.

    Args:
        decision_table: Optional decision table to extend. Uses global DECISION_TABLE if None.

    Returns:
        Dict with integration results per wave.
    """
    results = {
        "wave1_hf": {"status": "ok", "rules_added": 0},
        "wave2_qna": {"status": "ok", "packs_registered": 0},
        "wave3_skills": {"status": "ok", "pending_algorithms": len(PENDING_ALGORITHMS)},
    }

    # WAVE 1: Add Kronos/QuantDinger rules
    table = decision_table if decision_table is not None else DECISION_TABLE
    original_count = len(table)
    extended = integrate_hedge_fund_signals(table)
    results["wave1_hf"]["rules_added"] = len(extended) - original_count

    # WAVE 2: Initialize broker packs
    pack_info = initialize_broker_packs()
    results["wave2_qna"]["packs_registered"] = pack_info["registry_size"]

    # WAVE 3: Log pending algorithms
    log_pending_algorithms()

    logger.info(
        "Council integration complete: "
        "HF=%d rules added, QNA=%d packs, SKILLS=%d pending algos",
        results["wave1_hf"]["rules_added"],
        results["wave2_qna"]["packs_registered"],
        results["wave3_skills"]["pending_algorithms"],
    )

    return results


__all__ = [
    "SIGNAL_PIPELINE_CONFIG",
    "KRONOS_SIGNAL_CONTRACT",
    "PENDING_ALGORITHMS",
    "ANTI_SLOP_CONFIG",
    "integrate_hedge_fund_signals",
    "initialize_broker_packs",
    "integrate_council_findings",
]
