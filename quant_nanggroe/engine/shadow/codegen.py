"""Strategy Code Generator — Generate strategy code from templates.

Generates executable Python strategy code from structured strategy definitions.
Includes safe execution sandbox and strategy validation.

Ported from Vibe-Trading/agent/src/shadow_account/codegen.py
"""

from __future__ import annotations

import ast
import logging
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.shadow.extractor import ExtractedStrategy

logger = logging.getLogger(__name__)

# Safe imports permitted inside user/LLM strategy code (AST allowlist).
_ALLOWED_IMPORT_ROOTS = ("numpy", "np", "pandas", "pd", "quant_nanggroe")
# Dangerous builtins/calls blocked even inside the sandbox.
_FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "open", "input", "__import__",
    "getattr", "setattr", "delattr", "globals", "locals", "vars",
    "exit", "quit", "breakpoint",
}
_FORBIDDEN_ATTRS = {"__class__", "__subclasses__", "__bases__", "__mro__", "__dict__", "__globals__"}


@dataclass
class GeneratedCode:
    """Generated strategy code."""

    strategy_id: str
    code: str
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StrategyCodeGen:
    """Strategy Code Generator.

    Generates executable Python strategy code from structured strategy
    definitions. Includes:
    - Template-based code generation
    - Safe execution sandbox validation
    - Strategy compilation and validation

    Ported from Vibe-Trading/agent/src/shadow_account/codegen.py
    """

    STRATEGY_TEMPLATE = '''
"""Auto-generated strategy: {strategy_id}

Generated from: {source_hash}
Generated at: {generated_at}
Rules: {rule_count}
Markets: {markets}
Timeframe: {timeframe}
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from quant_nanggroe.engine.strategies.base import (
    SignalAction,
    Strategy,
    StrategyParameters,
    StrategySignal,
    StrategyType,
)


class {class_name}Parameters(StrategyParameters):
    """Parameters for {class_name}."""

{param_fields}


class {class_name}(Strategy):
    """Auto-generated strategy: {strategy_id}.

    {description}
    """

    def __init__(self, params: Optional[{class_name}Parameters] = None) -> None:
        self._params = params or {class_name}Parameters()

    @property
    def name(self) -> str:
        return "{strategy_id}"

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.TECHNICAL

    @property
    def description(self) -> str:
        return """{description}"""

    def generate_signal(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> StrategySignal:
        if not self.validate(df):
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reasoning="Insufficient data",
            )

        close = df["close"]
        current_price = float(close.iloc[-1])

{signal_logic}

        return StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            action=action,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            reasoning=reasoning,
        )

    def get_parameters(self) -> StrategyParameters:
        return self._params

    def validate(self, df: pd.DataFrame) -> bool:
        required = {{"high", "low", "close"}}
        if not required.issubset(df.columns):
            return False
        return len(df) >= 30
'''

    def generate(self, strategy: ExtractedStrategy) -> GeneratedCode:
        """Generate strategy code from an extracted strategy.

        Args:
            strategy: ExtractedStrategy to generate code for.

        Returns:
            GeneratedCode with the Python source code.
        """
        class_name = self._make_class_name(strategy.strategy_id)

        # Generate parameter fields
        param_fields = self._generate_param_fields(strategy)

        # Generate signal logic
        signal_logic = self._generate_signal_logic(strategy)

        # Generate description
        description = strategy.profile_summary or f"Auto-generated strategy with {len(strategy.rules)} rules"

        # Fill template
        code = self.STRATEGY_TEMPLATE.format(
            strategy_id=strategy.strategy_id,
            class_name=class_name,
            source_hash=strategy.source_hash,
            generated_at=strategy.extracted_at,
            rule_count=len(strategy.rules),
            markets=", ".join(strategy.markets),
            timeframe=strategy.timeframe,
            param_fields=param_fields,
            description=description,
            signal_logic=signal_logic,
        )

        # Validate
        is_valid, errors = self.validate_code(code)

        return GeneratedCode(
            strategy_id=strategy.strategy_id,
            code=code,
            is_valid=is_valid,
            validation_errors=errors,
            metadata={
                "class_name": class_name,
                "rule_count": len(strategy.rules),
            },
        )

    def validate_code(self, code: str) -> tuple:
        """Validate generated code for safety via AST allowlist.

        Permits only imports from safe roots (numpy/pandas/quant_nanggroe) and
        blocks dangerous builtins/attribute access. This defeats the regex-
        blocklist bypasses (e.g. ``getattr(__builtins__, '__import__')('os')``).

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors: List[str] = []

        # 1) Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, [f"Syntax error: {exc}"]

        # 2) AST walk — allowlist imports, blocklist dangerous nodes
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                else:
                    mods = [node.module or ""]
                for mod in mods:
                    root = mod.split(".")[0]
                    if root not in _ALLOWED_IMPORT_ROOTS:
                        errors.append(f"Import not allowed: '{mod}'")
            elif isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                if name in _FORBIDDEN_CALLS:
                    errors.append(f"Forbidden call: {name}()")
            elif isinstance(node, ast.Attribute):
                if node.attr in _FORBIDDEN_ATTRS:
                    errors.append(f"Forbidden attribute access: {node.attr}")
            elif isinstance(node, ast.Lambda):
                errors.append("Lambda expressions not allowed")

        return len(errors) == 0, errors

    def compile_strategy(self, code: str) -> Optional[type]:
        """Compile strategy code into a class (sandboxed exec).

        Args:
            code: Python source code.

        Returns:
            Strategy class, or None if compilation fails.
        """
        is_valid, errors = self.validate_code(code)
        if not is_valid:
            logger.error("Code validation failed: %s", errors)
            return None

        try:
            # ponytail: restricted builtins — keep import + class working but drop escapes
            import builtins as _builtins_mod
            _keep = ("abs", "min", "max", "sum", "len", "range", "enumerate", "zip",
                     "map", "filter", "float", "int", "bool", "str", "list", "dict",
                     "tuple", "set", "frozenset", "round", "pow", "__import__",
                     "__build_class__")
            safe_builtins = {k: _builtins_mod.__dict__.get(k) for k in _keep}
            for _bad in ("eval", "exec", "compile", "open", "input", "globals",
                         "locals", "vars", "getattr", "setattr", "delattr", "exit",
                         "quit", "breakpoint"):
                safe_builtins.pop(_bad, None)
            namespace: Dict[str, Any] = {"__builtins__": safe_builtins, "__name__": "__strategy__"}
            exec(compile(code, "<strategy>", "exec"), namespace)  # noqa: S102

            # Find the Strategy subclass (name-based; base may vary across modules)
            for name, obj in namespace.items():
                if isinstance(obj, type) and name.endswith("Strategy"):
                    return obj

            logger.error("No Strategy class found in compiled code")
            return None

        except Exception as exc:
            logger.error("Compilation failed: %s", exc)
            return None

    @staticmethod
    def _make_class_name(strategy_id: str) -> str:
        """Convert strategy_id to a valid Python class name."""
        parts = strategy_id.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts) + "Strategy"

    def _generate_param_fields(self, strategy: ExtractedStrategy) -> str:
        """Generate parameter fields for the strategy class."""
        fields = [
            "    min_confidence: float = 0.6",
        ]

        # Add rule-specific parameters
        for rule in strategy.rules:
            for key, value in rule.entry_conditions.items():
                if isinstance(value, dict) and "value" in value:
                    param_name = f"{key}_threshold"
                    fields.append(f"    {param_name}: float = {value['value']}")

        return "\n".join(fields)

    def _generate_signal_logic(self, strategy: ExtractedStrategy) -> str:
        """Generate signal logic from rules."""
        lines = []
        lines.append("        # Scoring")
        lines.append("        bullish_score = 0.0")
        lines.append("        bearish_score = 0.0")
        lines.append("        reasons = []")

        for rule in strategy.rules:
            lines.append(f"        # Rule: {rule.human_text}")

            for indicator, condition in rule.entry_conditions.items():
                if isinstance(condition, dict):
                    value = condition.get("value", 0)
                    operator = condition.get("operator", "gt")

                    if indicator == "rsi":
                        lines.append(f"        # RSI check")
                        lines.append("        delta = close.diff()")
                        lines.append("        gain = delta.where(delta > 0, 0.0)")
                        lines.append("        loss = (-delta).where(delta < 0, 0.0)")
                        lines.append("        avg_gain = gain.rolling(14, min_periods=14).mean()")
                        lines.append("        avg_loss = loss.rolling(14, min_periods=14).mean()")
                        lines.append("        rs = avg_gain / avg_loss.replace(0, np.nan)")
                        lines.append("        rsi = 100 - 100 / (1 + rs)")
                        if operator == "lt":
                            lines.append(f"        if float(rsi.iloc[-1]) < {value}:")
                            if rule.direction == "long":
                                lines.append("            bullish_score += 0.3")
                            else:
                                lines.append("            bearish_score += 0.3")
                        elif operator == "gt":
                            lines.append(f"        if float(rsi.iloc[-1]) > {value}:")
                            if rule.direction == "short":
                                lines.append("            bearish_score += 0.3")
                            else:
                                lines.append("            bullish_score += 0.3")

                    elif indicator == "sma_cross_above":
                        period = int(value) if isinstance(value, (int, float)) else 20
                        lines.append(f"        sma_{period} = close.rolling({period}, min_periods={period}).mean()")
                        lines.append(f"        if close.iloc[-1] > float(sma_{period}.iloc[-1]):")
                        lines.append("            bullish_score += 0.25")

                    elif indicator == "sma_cross_below":
                        period = int(value) if isinstance(value, (int, float)) else 20
                        lines.append(f"        sma_{period} = close.rolling({period}, min_periods={period}).mean()")
                        lines.append(f"        if close.iloc[-1] < float(sma_{period}.iloc[-1]):")
                        lines.append("            bearish_score += 0.25")

        # Signal determination
        lines.append("")
        lines.append("        total_score = bullish_score - bearish_score")
        lines.append("        confidence = min(0.9, abs(total_score) + 0.3)")
        lines.append("")
        lines.append("        if total_score > 0.3:")
        lines.append("            action = SignalAction.BUY")
        lines.append("            stop_loss = current_price * 0.98")
        lines.append("            take_profit = [current_price * 1.04]")
        lines.append("        elif total_score < -0.3:")
        lines.append("            action = SignalAction.SELL")
        lines.append("            stop_loss = current_price * 1.02")
        lines.append("            take_profit = [current_price * 0.96]")
        lines.append("        else:")
        lines.append("            action = SignalAction.HOLD")
        lines.append("            stop_loss = current_price")
        lines.append("            take_profit = [current_price]")
        lines.append("")
        lines.append("        risk = abs(current_price - stop_loss)")
        lines.append("        reward = abs(take_profit[0] - current_price)")
        lines.append("        rr_ratio = reward / risk if risk > 0 else 0")
        lines.append("        reasoning = '; '.join(reasons) if reasons else 'No signal'")

        return textwrap.indent("\n".join(lines), "        ")
