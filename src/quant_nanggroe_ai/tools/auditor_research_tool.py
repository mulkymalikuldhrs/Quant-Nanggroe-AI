#!/usr/bin/env python3
"""
Post-Trade Auditor + Research/Improvement Agent (L5 - Learning Layer)
Trade audit (plan vs execution), edge decay detection, strategy refinement
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger("HermesQuantOS.AuditorResearch")


class AuditorResearchTool:
    """L5 Agent: Auditor + Research - Self-improvement loop"""

    def __init__(self):
        self.audit_log = []
        self.improvement_suggestions = []

    def audit_recent(self) -> str:
        """Audit recent trades for plan vs execution alignment"""
        from tools.journal_tool import JournalTool
        journal = JournalTool()

        stats = json.loads(journal.get_stats())
        total = stats.get("total_trades", 0)

        if total == 0:
            return json.dumps({"message": "No trades to audit yet"})

        # Analyze patterns
        win_rate = float(stats.get("win_rate", "0%").replace("%", ""))
        avg_rr = stats.get("avg_rr_achieved", 0)
        profit_factor = stats.get("profit_factor", 0)

        findings = []

        if win_rate < 40:
            findings.append("LOW WIN RATE - Consider tightening entry criteria")
        if profit_factor < 1.5:
            findings.append("LOW PROFIT FACTOR - Review stop loss placement")
        if avg_rr < 1.5:
            findings.append("LOW R:R RATIO - Take profits too early or stop losses too wide")

        result = {
            "total_trades_audited": total,
            "win_rate": stats.get("win_rate"),
            "profit_factor": profit_factor,
            "avg_rr": avg_rr,
            "findings": findings if findings else ["Performance within acceptable parameters"],
            "audit_timestamp": datetime.now().isoformat()
        }

        self.audit_log.append(result)
        return json.dumps(result, indent=2)

    def suggest_improvements(self) -> str:
        """Generate improvement suggestions based on audit findings"""
        suggestions = []

        if self.audit_log:
            latest_audit = self.audit_log[-1]
            for finding in latest_audit.get("findings", []):
                if "LOW WIN RATE" in finding:
                    suggestions.append({
                        "area": "Entry Quality",
                        "suggestion": "Increase confluence requirement from 3/5 to 4/5",
                        "expected_impact": "Higher win rate, fewer trades"
                    })
                if "LOW PROFIT FACTOR" in finding:
                    suggestions.append({
                        "area": "Risk Management",
                        "suggestion": "Tighten stop losses using ATR multiplier of 1.0 instead of 1.5",
                        "expected_impact": "Better R:R, smaller losses"
                    })
                if "LOW R:R" in finding:
                    suggestions.append({
                        "area": "Exit Strategy",
                        "suggestion": "Use trailing stop after 1R profit reached",
                        "expected_impact": "Better capture of trends"
                    })

        if not suggestions:
            suggestions.append({
                "area": "General",
                "suggestion": "System performing within parameters. Continue monitoring.",
                "expected_impact": "Maintain current edge"
            })

        self.improvement_suggestions.extend(suggestions)

        return json.dumps({
            "improvement_suggestions": suggestions,
            "total_suggestions_generated": len(self.improvement_suggestions),
            "note": "All suggestions require manual review before implementation.",
            "timestamp": datetime.now().isoformat()
        }, indent=2)

    def detect_edge_decay(self) -> str:
        """Detect if trading edge is decaying over time"""
        if len(self.audit_log) < 3:
            return json.dumps({
                "status": "INSUFFICIENT_DATA",
                "message": "Need at least 3 audit cycles to detect edge decay"
            })

        # Compare recent vs earlier performance
        recent = self.audit_log[-3:]
        recent_win_rates = [float(a.get("win_rate", "0%").replace("%", "")) for a in recent]

        if len(recent_win_rates) >= 3:
            trend = "DECLINING" if recent_win_rates[-1] < recent_win_rates[0] else "STABLE"
            decay_detected = trend == "DECLINING" and (recent_win_rates[0] - recent_win_rates[-1]) > 10
        else:
            trend = "UNKNOWN"
            decay_detected = False

        return json.dumps({
            "edge_decay_detected": decay_detected,
            "trend": trend,
            "recent_win_rates": recent_win_rates,
            "recommendation": "REVIEW STRATEGY" if decay_detected else "CONTINUE MONITORING",
            "timestamp": datetime.now().isoformat()
        })
