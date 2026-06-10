"""
Token Reduction Utilities — concept adapted from rtk-reduce-tokenLLM.

rtk-reduce-tokenLLM is a Rust CLI that reduces LLM token consumption by
filtering verbose command output (build logs, test results, etc.) before
sending to the LLM. It uses TOML-based filter definitions.

This Python adaptation provides:
  - Output filtering for common command outputs
  - Token estimation for text strings
  - Configurable filter rules (Python dicts instead of TOML)
  - Integration with agent tools to reduce context window usage

Note: rtk-reduce-tokenLLM is Rust-based. This is a Python port of the concept,
not a direct code copy.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    """
    Rough token count estimation.

    Uses the common heuristic of ~4 characters per token for English text.
    Actual tokenization varies by model, but this is sufficient for filtering.

    Args:
        text: Input text.
        chars_per_token: Average characters per token (4.0 for English, ~2.0 for CJK).

    Returns:
        Estimated token count.
    """
    return max(1, int(len(text) / chars_per_token))


# ---------------------------------------------------------------------------
# Filter rules (adapted from rtk's TOML filter definitions)
# ---------------------------------------------------------------------------

@dataclass
class FilterRule:
    """
    A single filter rule for reducing output.

    Adapted from rtk's TOML filter format:
      - name: Filter identifier
      - pattern: Regex pattern to match lines
      - action: What to do with matching lines (keep/drop/summarize)
      - max_lines: Maximum lines to keep from matching section
    """
    name: str
    pattern: str
    action: str = "drop"  # "keep", "drop", "summarize"
    max_lines: int = 0  # 0 = unlimited for "keep", or max to keep for "summarize"

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, line: str) -> bool:
        return bool(self._compiled.search(line))


# Default filter rules for common verbose outputs
DEFAULT_FILTERS: List[FilterRule] = [
    # Build/test noise
    FilterRule("pip_progress", r"^(Downloading|Collecting|Requirement already)", "drop"),
    FilterRule("npm_progress", r"^(npm WARN|added \d+ packages)", "drop"),
    FilterRule("pip_install", r"^\s*(Installing|Building wheel)", "drop"),
    # Test output
    FilterRule("pytest_dots", r"^[\.FEsx]+$", "summarize", max_lines=1),
    FilterRule("unittest_ok", r"^(ok|Ran \d+ test)", "keep", max_lines=5),
    # Git noise
    FilterRule("git_stat", r"^\s*\d+ files? changed", "keep", max_lines=3),
    # Docker/build noise
    FilterRule("docker_pull", r"^(Pulling from|Digest|Status)", "keep", max_lines=3),
    # Stack traces - keep but limit
    FilterRule("traceback", r"(Traceback|File \")", "keep", max_lines=15),
    # Empty/repetitive lines
    FilterRule("blank_lines", r"^\s*$", "drop"),
]


# ---------------------------------------------------------------------------
# Output Filter
# ---------------------------------------------------------------------------

class OutputFilter:
    """
    Filters verbose command output to reduce LLM token consumption.

    Adapted from rtk-reduce-tokenLLM's core concept:
      - Match lines against filter rules
      - Drop, keep, or summarize matched sections
      - Track reduction statistics
      - Preserve important lines (errors, warnings, results)
    """

    def __init__(
        self,
        rules: Optional[List[FilterRule]] = None,
        max_output_lines: int = 200,
        max_output_chars: int = 8000,
        preserve_patterns: Optional[List[str]] = None,
    ) -> None:
        """
        Args:
            rules: Filter rules. Defaults to DEFAULT_FILTERS.
            max_output_lines: Maximum lines in filtered output.
            max_output_chars: Maximum characters in filtered output.
            preserve_patterns: Regex patterns for lines that should ALWAYS be kept.
        """
        self.rules = rules or DEFAULT_FILTERS
        self.max_output_lines = max_output_lines
        self.max_output_chars = max_output_chars
        self._preserve_compiled = [
            re.compile(p, re.IGNORECASE) for p in (preserve_patterns or [
                r"error",
                r"failed",
                r"critical",
                r"exception",
                r"fatal",
                r"warning:.*error",
                r"assertion",
                r"test.*fail",
            ])
        ]

    def filter(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Filter text to reduce token consumption.

        Args:
            text: Raw command output text.

        Returns:
            Tuple of (filtered_text, stats_dict) where stats includes:
              - original_chars, filtered_chars, reduction_pct
              - original_tokens, filtered_tokens, token_reduction_pct
              - rules_applied: count of rules that matched
        """
        if not text:
            return text, self._empty_stats()

        lines = text.split("\n")
        original_chars = len(text)
        original_tokens = estimate_tokens(text)

        filtered_lines: List[str] = []
        rules_applied = 0

        # Track summarize sections
        summarize_buffers: Dict[str, List[str]] = {}

        for line in lines:
            # Always preserve lines matching preserve patterns
            if self._should_preserve(line):
                filtered_lines.append(line)
                continue

            # Check against filter rules
            action = self._determine_action(line)
            if action == "keep":
                filtered_lines.append(line)
            elif action == "summarize":
                # Buffer for summarization
                rule_name = self._matching_rule_name(line)
                if rule_name:
                    summarize_buffers.setdefault(rule_name, []).append(line)
            # "drop" → skip line
            if action != "keep":
                rules_applied += 1

        # Add summarized sections
        for rule_name, buffered_lines in summarize_buffers.items():
            if buffered_lines:
                rule = next((r for r in self.rules if r.name == rule_name), None)
                if rule and rule.max_lines > 0:
                    count = len(buffered_lines)
                    shown = buffered_lines[:rule.max_lines]
                    filtered_lines.append(f"[{rule_name}: {count} lines, showing {len(shown)}]")
                    filtered_lines.extend(shown)
                else:
                    filtered_lines.append(f"[{rule_name}: {len(buffered_lines)} lines omitted]")

        # Enforce max lines
        if len(filtered_lines) > self.max_output_lines:
            half = self.max_output_lines // 2
            filtered_lines = (
                filtered_lines[:half]
                + [f"... [{len(filtered_lines) - self.max_output_lines} lines truncated] ..."]
                + filtered_lines[-half:]
            )

        result = "\n".join(filtered_lines)

        # Enforce max chars
        if len(result) > self.max_output_chars:
            result = result[:self.max_output_chars] + "\n... [output truncated]"

        filtered_chars = len(result)
        filtered_tokens = estimate_tokens(result)

        stats = {
            "original_chars": original_chars,
            "filtered_chars": filtered_chars,
            "reduction_pct": round((1 - filtered_chars / original_chars) * 100, 1) if original_chars > 0 else 0.0,
            "original_tokens": original_tokens,
            "filtered_tokens": filtered_tokens,
            "token_reduction_pct": round((1 - filtered_tokens / original_tokens) * 100, 1) if original_tokens > 0 else 0.0,
            "rules_applied": rules_applied,
        }

        return result, stats

    def _should_preserve(self, line: str) -> bool:
        """Check if line matches any preserve pattern."""
        return any(p.search(line) for p in self._preserve_compiled)

    def _determine_action(self, line: str) -> str:
        """Determine the action for a line based on filter rules."""
        for rule in self.rules:
            if rule.matches(line):
                return rule.action
        return "keep"  # Default: keep unmatched lines

    def _matching_rule_name(self, line: str) -> Optional[str]:
        """Get the name of the first matching rule."""
        for rule in self.rules:
            if rule.matches(line):
                return rule.name
        return None

    @staticmethod
    def _empty_stats() -> Dict[str, Any]:
        return {
            "original_chars": 0,
            "filtered_chars": 0,
            "reduction_pct": 0.0,
            "original_tokens": 0,
            "filtered_tokens": 0,
            "token_reduction_pct": 0.0,
            "rules_applied": 0,
        }


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def reduce_output(
    text: str,
    max_lines: int = 200,
    max_chars: int = 8000,
) -> Tuple[str, Dict[str, Any]]:
    """
    Quick-filter verbose output to reduce token usage.

    Args:
        text: Raw command output.
        max_lines: Maximum lines to keep.
        max_chars: Maximum characters to keep.

    Returns:
        Tuple of (filtered_text, stats_dict).
    """
    f = OutputFilter(max_output_lines=max_lines, max_output_chars=max_chars)
    return f.filter(text)
