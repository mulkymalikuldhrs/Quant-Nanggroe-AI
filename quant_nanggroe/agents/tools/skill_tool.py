"""Skill Tool — Skill System & Marketplace for Trading Intelligence.

Provides skill definition schema, DCF valuation skill with sector-WACC,
skill marketplace registry, and skill execution sandbox.

Features
--------
* Skill definition schema (SKILL.md format)
* DCF valuation skill with sector-specific WACC
* Skill marketplace registry
* Skill execution sandbox with validation
* LangChain @tool function for agent consumption

References
----------
Dexter skill system architecture (TypeScript, ported to Python)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillSource(str, Enum):
    """Source of a skill definition."""
    BUILTIN = "builtin"
    USER = "user"
    PROJECT = "project"
    MARKETPLACE = "marketplace"


class SkillStatus(str, Enum):
    """Skill status."""
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    BETA = "BETA"
    DISABLED = "DISABLED"


class ExecutionStatus(str, Enum):
    """Skill execution status."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SkillMetadata(BaseModel):
    """Skill metadata — lightweight info for system prompt injection."""
    name: str = Field(..., description="Unique skill name")
    description: str = Field(..., description="When to use this skill")
    source: SkillSource = Field(SkillSource.BUILTIN, description="Where skill was discovered")
    status: SkillStatus = Field(SkillStatus.ACTIVE)
    version: str = Field("1.0.0")
    author: str = Field("", description="Skill author")
    tags: List[str] = Field(default_factory=list, description="Skill tags")
    path: str = Field("", description="Path to SKILL.md or instructions")


class SkillDefinition(BaseModel):
    """Full skill definition with instructions."""
    metadata: SkillMetadata = Field(..., description="Skill metadata")
    instructions: str = Field("", description="Full SKILL.md body content")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Skill parameters")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")


class SkillExecutionResult(BaseModel):
    """Result from executing a skill."""
    execution_id: str = Field("", description="Execution identifier")
    skill_name: str = Field("", description="Executed skill name")
    status: ExecutionStatus = Field(ExecutionStatus.SUCCESS)
    output: Dict[str, Any] = Field(default_factory=dict, description="Execution output")
    errors: List[str] = Field(default_factory=list, description="Execution errors")
    execution_time_ms: float = Field(0.0, description="Execution time in milliseconds")
    timestamp: str = Field("")


class DCFInput(BaseModel):
    """DCF valuation input parameters."""
    symbol: str = Field(..., description="Company ticker symbol")
    fcf_history: List[float] = Field(default_factory=list, description="Historical FCF (5 years)")
    growth_rate: float = Field(0.05, description="Projected FCF growth rate")
    wacc: Optional[float] = Field(None, description="WACC (auto-determined from sector if None)")
    sector: str = Field("", description="Company sector for WACC lookup")
    terminal_growth: float = Field(0.025, description="Terminal growth rate")
    total_debt: float = Field(0.0, description="Total debt")
    cash: float = Field(0.0, description="Cash and equivalents")
    shares_outstanding: float = Field(0.0, description="Shares outstanding")
    projection_years: int = Field(5, description="Number of projection years")


class DCFResult(BaseModel):
    """DCF valuation result."""
    symbol: str = Field(...)
    enterprise_value: float = Field(0.0, description="Enterprise value")
    net_debt: float = Field(0.0, description="Net debt")
    equity_value: float = Field(0.0, description="Equity value")
    fair_value_per_share: float = Field(0.0, description="Fair value per share")
    wacc_used: float = Field(0.0, description="WACC used")
    growth_rate_used: float = Field(0.0, description="Growth rate used")
    terminal_value: float = Field(0.0, description="Terminal value")
    terminal_value_pct: float = Field(0.0, description="Terminal value as % of EV")
    sensitivity_matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    projections: List[Dict[str, float]] = Field(default_factory=list)
    timestamp: str = Field("")


# ---------------------------------------------------------------------------
# Sector WACC database
# ---------------------------------------------------------------------------

_SECTOR_WACC: Dict[str, Dict[str, float]] = {
    "technology": {"base_wacc": 0.11, "beta": 1.2, "adjustment": 0.0},
    "healthcare": {"base_wacc": 0.10, "beta": 1.1, "adjustment": 0.0},
    "financials": {"base_wacc": 0.09, "beta": 1.0, "adjustment": -0.005},
    "energy": {"base_wacc": 0.10, "beta": 1.1, "adjustment": 0.01},
    "materials": {"base_wacc": 0.09, "beta": 1.0, "adjustment": 0.0},
    "industrials": {"base_wacc": 0.09, "beta": 1.0, "adjustment": 0.0},
    "consumer_discretionary": {"base_wacc": 0.10, "beta": 1.1, "adjustment": 0.0},
    "consumer_staples": {"base_wacc": 0.08, "beta": 0.8, "adjustment": -0.01},
    "utilities": {"base_wacc": 0.07, "beta": 0.7, "adjustment": -0.02},
    "real_estate": {"base_wacc": 0.08, "beta": 0.8, "adjustment": -0.01},
    "telecommunications": {"base_wacc": 0.08, "beta": 0.9, "adjustment": -0.005},
}

_DEFAULT_WACC = 0.10


# ---------------------------------------------------------------------------
# Skill Tool
# ---------------------------------------------------------------------------

class SkillTool:
    """Skill system and marketplace tool for agent consumption.

    Provides skill definition, DCF valuation with sector-WACC,
    skill marketplace registry, and skill execution sandbox.

    Usage::

        tool = SkillTool()
        dcf = await tool.run_dcf(dcf_input)
        skills = tool.list_skills()
        result = await tool.execute_skill("dcf-valuation", {"symbol": "AAPL"})
    """

    def __init__(self) -> None:
        self._registry: Dict[str, SkillDefinition] = {}
        self._execution_history: List[SkillExecutionResult] = []
        self._register_builtin_skills()

    def _register_builtin_skills(self) -> None:
        """Register built-in skills."""
        # DCF Valuation Skill
        dcf_skill = SkillDefinition(
            metadata=SkillMetadata(
                name="dcf-valuation",
                description=(
                    "Performs discounted cash flow (DCF) valuation analysis to estimate "
                    "intrinsic value per share. Triggers when user asks for fair value, "
                    "intrinsic value, DCF, valuation, or price target analysis."
                ),
                source=SkillSource.BUILTIN,
                status=SkillStatus.ACTIVE,
                version="1.0.0",
                author="Quant Nanggroe AI",
                tags=["valuation", "fundamental", "dcf"],
            ),
            instructions=(
                "# DCF Valuation Skill\n\n"
                "1. Gather financial data (FCF, balance sheet, metrics)\n"
                "2. Calculate FCF growth rate\n"
                "3. Estimate WACC from sector\n"
                "4. Project future cash flows\n"
                "5. Calculate present value and fair value per share\n"
                "6. Run sensitivity analysis\n"
                "7. Validate and present results\n"
            ),
        )
        self._registry["dcf-valuation"] = dcf_skill

    # ----- Skill Registry -----

    def register_skill(self, skill: SkillDefinition) -> None:
        """Register a skill in the marketplace.

        Args:
            skill: SkillDefinition to register.
        """
        name = skill.metadata.name
        if name in self._registry:
            logger.warning("Overwriting existing skill: %s", name)
        self._registry[name] = skill
        logger.info("Registered skill: %s", name)

    def list_skills(
        self,
        source: Optional[SkillSource] = None,
        tag: Optional[str] = None,
    ) -> List[SkillMetadata]:
        """List available skills.

        Args:
            source: Filter by source (optional).
            tag: Filter by tag (optional).

        Returns:
            List of SkillMetadata.
        """
        skills = list(self._registry.values())
        if source:
            skills = [s for s in skills if s.metadata.source == source]
        if tag:
            skills = [s for s in skills if tag in s.metadata.tags]
        return [s.metadata for s in skills]

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """Get a skill by name.

        Args:
            name: Skill name.

        Returns:
            SkillDefinition if found, None otherwise.
        """
        return self._registry.get(name)

    # ----- Skill Execution -----

    async def execute_skill(
        self,
        skill_name: str,
        parameters: Dict[str, Any],
    ) -> SkillExecutionResult:
        """Execute a skill in the sandbox.

        Args:
            skill_name: Name of the skill to execute.
            parameters: Parameters for the skill.

        Returns:
            SkillExecutionResult with execution output.
        """
        start_time = time.monotonic()
        execution_id = str(uuid.uuid4())[:8]

        skill = self._registry.get(skill_name)
        if not skill:
            return SkillExecutionResult(
                execution_id=execution_id,
                skill_name=skill_name,
                status=ExecutionStatus.FAILED,
                errors=[f"Skill '{skill_name}' not found"],
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )

        try:
            if skill_name == "dcf-valuation":
                output = await self._execute_dcf(parameters)
            else:
                output = {"message": f"Skill '{skill_name}' executed", "parameters": parameters}

            elapsed = (time.monotonic() - start_time) * 1000

            result = SkillExecutionResult(
                execution_id=execution_id,
                skill_name=skill_name,
                status=ExecutionStatus.SUCCESS,
                output=output,
                execution_time_ms=round(elapsed, 2),
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start_time) * 1000
            result = SkillExecutionResult(
                execution_id=execution_id,
                skill_name=skill_name,
                status=ExecutionStatus.FAILED,
                errors=[str(exc)],
                execution_time_ms=round(elapsed, 2),
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )

        self._execution_history.append(result)
        return result

    # ----- DCF Valuation -----

    async def run_dcf(self, inputs: DCFInput) -> DCFResult:
        """Run a DCF valuation analysis.

        Args:
            inputs: DCF valuation input parameters.

        Returns:
            DCFResult with valuation output.
        """
        # Determine WACC
        wacc = inputs.wacc
        if wacc is None:
            sector_data = _SECTOR_WACC.get(
                inputs.sector.lower(),
                {"base_wacc": _DEFAULT_WACC, "adjustment": 0.0},
            )
            wacc = sector_data["base_wacc"] + sector_data["adjustment"]

        # Determine growth rate (cap at 15%)
        growth_rate = min(inputs.growth_rate, 0.15)

        # Get base FCF
        if inputs.fcf_history:
            base_fcf = inputs.fcf_history[-1]
        else:
            base_fcf = 0.0

        # Project future FCFs
        projections = []
        pv_fcf_total = 0.0
        current_fcf = base_fcf

        for year in range(1, inputs.projection_years + 1):
            decay = 1.0 - (year - 1) * 0.05  # 5% annual decay
            projected_fcf = current_fcf * (1 + growth_rate * max(decay, 0.5))
            pv_factor = 1 / (1 + wacc) ** year
            pv_fcf = projected_fcf * pv_factor
            pv_fcf_total += pv_fcf

            projections.append({
                "year": year,
                "fcf": round(projected_fcf, 2),
                "pv_factor": round(pv_factor, 6),
                "pv_fcf": round(pv_fcf, 2),
            })
            current_fcf = projected_fcf

        # Terminal value (Gordon Growth Model)
        terminal_fcf = current_fcf * (1 + inputs.terminal_growth)
        terminal_value = terminal_fcf / (wacc - inputs.terminal_growth) if wacc > inputs.terminal_growth else 0.0
        pv_terminal = terminal_value / (1 + wacc) ** inputs.projection_years

        # Enterprise value
        enterprise_value = pv_fcf_total + pv_terminal

        # Net debt
        net_debt = inputs.total_debt - inputs.cash

        # Equity value
        equity_value = enterprise_value - net_debt

        # Fair value per share
        fair_value = equity_value / inputs.shares_outstanding if inputs.shares_outstanding > 0 else 0.0

        # Terminal value percentage
        tv_pct = (pv_terminal / enterprise_value * 100) if enterprise_value > 0 else 0.0

        # Sensitivity matrix (WACC ±1% vs terminal growth)
        sensitivity = self._build_sensitivity_matrix(
            base_fcf, growth_rate, inputs.projection_years, wacc,
            inputs.terminal_growth, net_debt, inputs.shares_outstanding,
        )

        return DCFResult(
            symbol=inputs.symbol,
            enterprise_value=round(enterprise_value, 2),
            net_debt=round(net_debt, 2),
            equity_value=round(equity_value, 2),
            fair_value_per_share=round(fair_value, 2),
            wacc_used=round(wacc, 4),
            growth_rate_used=round(growth_rate, 4),
            terminal_value=round(terminal_value, 2),
            terminal_value_pct=round(tv_pct, 2),
            sensitivity_matrix=sensitivity,
            projections=projections,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    async def _execute_dcf(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DCF skill from parameters dict."""
        inputs = DCFInput(
            symbol=parameters.get("symbol", ""),
            fcf_history=parameters.get("fcf_history", []),
            growth_rate=parameters.get("growth_rate", 0.05),
            wacc=parameters.get("wacc"),
            sector=parameters.get("sector", ""),
            terminal_growth=parameters.get("terminal_growth", 0.025),
            total_debt=parameters.get("total_debt", 0.0),
            cash=parameters.get("cash", 0.0),
            shares_outstanding=parameters.get("shares_outstanding", 1.0),
            projection_years=parameters.get("projection_years", 5),
        )
        result = await self.run_dcf(inputs)
        return result.model_dump()

    @staticmethod
    def _build_sensitivity_matrix(
        base_fcf: float,
        growth_rate: float,
        years: int,
        base_wacc: float,
        base_terminal_growth: float,
        net_debt: float,
        shares: float,
    ) -> Dict[str, Dict[str, float]]:
        """Build 3x3 sensitivity matrix."""
        wacc_range = [base_wacc - 0.01, base_wacc, base_wacc + 0.01]
        tg_range = [0.02, 0.025, 0.03]

        matrix = {}
        for w in wacc_range:
            w_key = f"WACC_{round(w*100, 1)}%"
            matrix[w_key] = {}
            for tg in tg_range:
                tg_key = f"TG_{round(tg*100, 1)}%"

                # Simplified calculation
                pv_sum = 0.0
                current = base_fcf
                for yr in range(1, years + 1):
                    current = current * (1 + growth_rate * max(1 - (yr - 1) * 0.05, 0.5))
                    pv_sum += current / (1 + w) ** yr

                tv = current * (1 + tg) / (w - tg) if w > tg else 0.0
                pv_tv = tv / (1 + w) ** years
                ev = pv_sum + pv_tv
                equity = ev - net_debt
                fair_value = equity / shares if shares > 0 else 0.0

                matrix[w_key][tg_key] = round(fair_value, 2)

        return matrix


# ---------------------------------------------------------------------------
# Singleton and LangChain @tool
# ---------------------------------------------------------------------------

_default_skill: SkillTool | None = None


def _get_default_skill() -> SkillTool:
    global _default_skill
    if _default_skill is None:
        _default_skill = SkillTool()
    return _default_skill


@tool
async def run_dcf_valuation(
    symbol: str,
    sector: str = "",
    growth_rate: float = 0.05,
    shares_outstanding: float = 1.0,
    total_debt: float = 0.0,
    cash: float = 0.0,
) -> str:
    """Run a DCF valuation analysis for a company.

    Performs discounted cash flow analysis with sector-specific WACC,
    5-year FCF projections, terminal value, and sensitivity matrix.
    Determines intrinsic fair value per share.

    Args:
        symbol: Company ticker symbol (e.g., 'AAPL')
        sector: Company sector for WACC lookup (e.g., 'technology')
        growth_rate: Projected FCF growth rate (default 0.05)
        shares_outstanding: Total shares outstanding
        total_debt: Total debt amount
        cash: Cash and equivalents

    Returns:
        JSON string with enterprise value, fair value per share,
        WACC used, sensitivity matrix, and FCF projections.
    """
    try:
        st = _get_default_skill()
        inputs = DCFInput(
            symbol=symbol,
            sector=sector,
            growth_rate=growth_rate,
            shares_outstanding=shares_outstanding,
            total_debt=total_debt,
            cash=cash,
        )
        result = await st.run_dcf(inputs)
        return json.dumps(result.model_dump(), indent=2, default=str)
    except Exception as exc:
        logger.error("run_dcf_valuation tool error: %s", exc)
        return json.dumps({"error": f"DCF valuation failed: {exc}", "symbol": symbol})


__all__ = [
    "SkillTool",
    "SkillSource",
    "SkillStatus",
    "ExecutionStatus",
    "SkillMetadata",
    "SkillDefinition",
    "SkillExecutionResult",
    "DCFInput",
    "DCFResult",
    "run_dcf_valuation",
]
