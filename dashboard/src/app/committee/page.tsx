"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { committeeApi } from "@/lib/api-client";
import type { CommitteeDecision, CommitteeStats, AgentVote } from "@/lib/api-client";
import { cn, formatPercent, formatCurrency } from "@/lib/utils";
import {
  Brain, Shield, TrendingUp, TrendingDown, Minus, RefreshCw, Play,
  AlertTriangle, CheckCircle2, XCircle, Vote, Users, BarChart3,
} from "lucide-react";

function VoteBar({ votes }: { votes: AgentVote[] }) {
  const bull = votes.filter(v => v.vote === "bull").length;
  const bear = votes.filter(v => v.vote === "bear").length;
  const neutral = votes.filter(v => v.vote === "neutral").length;
  const total = votes.length || 1;

  return (
    <div className="flex items-center gap-1 h-2 rounded-full overflow-hidden bg-white/5">
      <div className="h-full bg-emerald-500/80 transition-all duration-500" style={{ width: `${(bull / total) * 100}%` }} />
      <div className="h-full bg-red-500/80 transition-all duration-500" style={{ width: `${(bear / total) * 100}%` }} />
      <div className="h-full bg-white/20 transition-all duration-500" style={{ width: `${(neutral / total) * 100}%` }} />
    </div>
  );
}

function DecisionCard({ d }: { d: CommitteeDecision }) {
  const [expanded, setExpanded] = useState(false);
  const isBuy = d.decision === "BUY";
  const isSell = d.decision === "SELL";
  const isVetoed = d.risk_veto;

  return (
    <div
      className={cn(
        "group relative rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden",
        isVetoed
          ? "bg-red-500/5 border-red-500/20 hover:border-red-500/30"
          : isBuy
            ? "bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/30"
            : isSell
              ? "bg-amber-500/5 border-amber-500/20 hover:border-amber-500/30"
              : "bg-white/[0.02] border-white/[0.06] hover:border-white/10",
      )}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <Badge variant={isBuy ? "success" : isSell ? "warning" : "default"}>
              {d.decision}
            </Badge>
            <span className="text-xs font-mono text-white/40">{d.symbol}</span>
          </div>
          <div className="flex items-center gap-2">
            {isVetoed && (
              <Badge variant="danger">
                <Shield className="w-3 h-3 mr-1" />
                RISK VETO
              </Badge>
            )}
            <span className="text-xs text-white/30 font-mono">
              {new Date(d.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1">
            <VoteBar votes={d.votes} />
          </div>
          <span className={cn(
            "text-sm font-mono font-medium",
            d.confidence >= 70 ? "text-emerald-400" : d.confidence >= 50 ? "text-amber-400" : "text-white/40",
          )}>
            {formatPercent(d.confidence)}
          </span>
        </div>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-white/[0.06] space-y-2">
            {d.votes.map((v, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={cn(
                  "font-medium min-w-[80px]",
                  v.vote === "bull" ? "text-emerald-400" : v.vote === "bear" ? "text-red-400" : "text-white/40",
                )}>
                  {v.agent}
                </span>
                <span className="text-white/50 flex-1">{v.reasoning}</span>
              </div>
            ))}
            {isVetoed && d.risk_reason && (
              <div className="mt-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300">
                <Shield className="w-3 h-3 inline mr-1" />
                Risk Officer: {d.risk_reason}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function CommitteeContent() {
  const [decisions, setDecisions] = useState<CommitteeDecision[]>([]);
  const [stats, setStats] = useState<CommitteeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [debateSymbol, setDebateSymbol] = useState("EURUSD");
  const [debating, setDebating] = useState(false);
  const [debateResult, setDebateResult] = useState<CommitteeDecision | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [d, s] = await Promise.allSettled([
        committeeApi.listDecisions(50),
        committeeApi.getStats(),
      ]);
      if (d.status === "fulfilled") setDecisions(d.value);
      if (s.status === "fulfilled") setStats(s.value);
    } catch {
      setError("Backend unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const runDebate = async () => {
    setDebating(true);
    try {
      const result = await committeeApi.runDebate({ symbol: debateSymbol });
      setDebateResult({
        id: "debate-" + Date.now(),
        timestamp: new Date().toISOString(),
        symbol: debateSymbol,
        decision: result.decision as CommitteeDecision["decision"],
        confidence: result.confidence,
        votes: result.votes,
        risk_veto: result.risk_veto,
      });
    } catch { /* ignore */ }
    setDebating(false);
  };

  if (loading) return <LoadingSkeleton variant="page" />;
  if (error) return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <AlertTriangle className="w-10 h-10 text-amber-400 mb-3" />
      <p className="text-sm text-white/50">{error}</p>
      <Button onClick={loadData} variant="ghost" size="sm" className="mt-3">
        <RefreshCw className="w-4 h-4 mr-2" />
        Retry
      </Button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Committee</h1>
          <p className="text-sm text-white/40 mt-1">Per-pair agent voting &amp; risk veto</p>
        </div>
        <Button onClick={loadData} variant="ghost" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatusCard title="Decisions" value={stats?.total_decisions ?? 0} icon={<BarChart3 className="w-4 h-4" />} />
        <StatusCard title="BUY" value={stats?.buy_count ?? 0} icon={<TrendingUp className="w-4 h-4" />} variant="success" />
        <StatusCard title="SELL" value={stats?.sell_count ?? 0} icon={<TrendingDown className="w-4 h-4" />} variant="warning" />
        <StatusCard title="Avg Confidence" value={stats ? `${Math.round(stats.avg_confidence)}%` : "—"} icon={<Brain className="w-4 h-4" />} />
        <StatusCard title="Risk Vetoes" value={stats?.risk_veto_count ?? 0} icon={<Shield className="w-4 h-4" />} variant="danger" />
      </div>

      {/* Run Debate */}
      <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Play className="w-4 h-4 text-emerald-400" />
            <span className="text-sm font-medium text-white">Run Committee Debate</span>
          </div>
          <input
            type="text"
            value={debateSymbol}
            onChange={(e) => setDebateSymbol(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm text-white font-mono focus:outline-none focus:border-emerald-500/50 w-32"
            placeholder="Symbol"
          />
          <Button onClick={runDebate} disabled={debating} size="sm">
            {debating ? "Debating..." : "Run"}
          </Button>
        </div>
        {debateResult && (
          <div className="mt-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={debateResult.decision === "BUY" ? "success" : debateResult.decision === "SELL" ? "warning" : "default"}>
                {debateResult.decision}
              </Badge>
              <span className="text-xs text-white/40 font-mono">{debateResult.symbol}</span>
              <span className="text-xs text-emerald-400 font-mono">{formatPercent(debateResult.confidence)}</span>
            </div>
            <VoteBar votes={debateResult.votes} />
          </div>
        )}
      </div>

      {/* Decisions */}
      <div>
        <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">Recent Decisions</h2>
        <div className="grid gap-3">
          {decisions.length === 0 ? (
            <div className="text-center py-12 text-white/30 text-sm">
              No committee decisions yet. Start the daemon to generate decisions.
            </div>
          ) : (
            decisions.map((d) => <DecisionCard key={d.id} d={d} />)
          )}
        </div>
      </div>
    </div>
  );
}

export default function CommitteePage() {
  return (
    <ErrorBoundary>
      <CommitteeContent />
    </ErrorBoundary>
  );
}
