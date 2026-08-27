"""
Ensemble Dashboard — real-time view of multi-signal voting.

Shows:
- All signal providers and their current votes
- Consensus strength and final decision
- Risk metrics (Kelly, Monte Carlo)
- Active positions and P&L

Runs as a simple terminal dashboard or API endpoint.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from quant_nanggroe.engine.agentic.adapters import ALL_ADAPTERS
from quant_nanggroe.engine.agentic.voting import SignalVotingSystem
from quant_nanggroe.engine.risk.enhanced_analytics import EnhancedRiskAnalytics
from quant_nanggroe.engine.scanner.multi_pair import MultiPairScanner

logger = logging.getLogger(__name__)


class EnsembleDashboard:
    """Real-time dashboard for ensemble trading system.

    Usage:
        dashboard = EnsembleDashboard()
        report = dashboard.generate_report("EURUSD")
        print(dashboard.format_terminal(report))
    """

    def __init__(self):
        self.voter = SignalVotingSystem()
        self.analytics = EnhancedRiskAnalytics()
        self.scanner = MultiPairScanner()

    def generate_report(self, symbol: str, dataframe=None) -> dict[str, Any]:
        """Generate a full report for a symbol."""
        # Fetch signals from all adapters
        signals = []
        adapter_results = []
        for adapter in ALL_ADAPTERS:
            try:
                sig = adapter.fetch_signal(symbol, dataframe=dataframe)
                if sig:
                    signals.append(sig)
                    adapter_results.append({
                        "source": adapter.source_name,
                        "bias": sig.bias.value,
                        "confidence": sig.confidence,
                        "timestamp": sig.timestamp,
                    })
            except Exception as e:
                adapter_results.append({
                    "source": adapter.source_name,
                    "bias": "error",
                    "confidence": 0,
                    "error": str(e),
                })

        # Run voting
        vote_result = self.voter.vote(signals) if signals else None

        # Get pair info
        pair_info = self.scanner.pairs.get(symbol)

        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals": adapter_results,
            "vote": {
                "final_bias": vote_result.final_bias.value if vote_result else "neutral",
                "confidence": round(vote_result.weighted_confidence, 4) if vote_result else 0,
                "consensus": round(vote_result.consensus_strength, 4) if vote_result else 0,
                "dissenters": len(vote_result.dissenters) if vote_result else 0,
            },
            "pair": pair_info.to_dict() if pair_info else None,
            "scanner_summary": self.scanner.get_summary(),
        }

    def format_terminal(self, report: dict[str, Any]) -> str:
        """Format report for terminal display."""
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"  ENSEMBLE DASHBOARD — {report['symbol']}")
        lines.append(f"  {report['timestamp']}")
        lines.append(f"{'='*60}")

        # Signals
        lines.append("\n  SIGNAL PROVIDERS:")
        for sig in report["signals"]:
            status = "OK" if sig["bias"] != "error" else "ERR"
            conf = f"{sig['confidence']:.2f}" if sig["confidence"] else "—"
            lines.append(f"    [{status}] {sig['source']:20s} → {sig['bias']:8s} (conf={conf})")

        # Vote
        vote = report["vote"]
        lines.append("\n  VOTE RESULT:")
        lines.append(f"    Decision:    {vote['final_bias'].upper()}")
        lines.append(f"    Confidence:  {vote['confidence']:.2%}")
        lines.append(f"    Consensus:   {vote['consensus']:.2%}")
        lines.append(f"    Dissenters:  {vote['dissenters']}")

        # Pair
        if report["pair"]:
            p = report["pair"]
            lines.append("\n  PAIR INFO:")
            lines.append(f"    Spread:    {p['spread_pips']} pips")
            lines.append(f"    Mode:      {p['trade_mode']}")
            lines.append(f"    Ask/Bid:   {p['ask']} / {p['bid']}")

        # Scanner
        s = report["scanner_summary"]
        lines.append(f"\n  SCANNER: {s['tradeable']}/{s['total_pairs']} tradeable, avg spread={s['avg_spread']} pips")
        lines.append(f"{'='*60}")

        return "\n".join(lines)

    def generate_multi_symbol_report(self, symbols: list[str], dataframe_map: dict = None) -> str:
        """Generate a multi-symbol overview."""
        df_map = dataframe_map or {}
        reports = []
        for sym in symbols:
            reports.append(self.generate_report(sym, df_map.get(sym)))

        lines = []
        lines.append(f"{'='*70}")
        lines.append(f"  MULTI-SYMBOL ENSEMBLE OVERVIEW — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"{'='*70}")
        lines.append(f"  {'Symbol':12s} {'Decision':10s} {'Conf':>8s} {'Consensus':>10s} {'Spread':>8s}")
        lines.append(f"  {'-'*60}")

        for r in reports:
            v = r["vote"]
            spread = r["pair"]["spread_pips"] if r["pair"] else "—"
            lines.append(
                f"  {r['symbol']:12s} {v['final_bias']:10s} {v['confidence']:>8.2%} {v['consensus']:>10.2%} {str(spread):>8s}"
            )

        lines.append(f"{'='*70}")
        return "\n".join(lines)


if __name__ == "__main__":
    dashboard = EnsembleDashboard()
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    print(dashboard.generate_multi_symbol_report(symbols))
    for sym in symbols[:2]:
        report = dashboard.generate_report(sym)
        print(dashboard.format_terminal(report))
