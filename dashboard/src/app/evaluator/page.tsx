"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { evaluatorApi } from "@/lib/api-client";
import type {
  StrategyRegistryEntry, EvaluatorEvolutionStatus, PipelineStatus,
} from "@/lib/api-client";
import { cn, formatPercent } from "@/lib/utils";
import {
  Sigma, Activity, CheckCircle2, XCircle, AlertTriangle,
  RefreshCw, TrendingUp, TrendingDown, Clock, Zap, FlaskConical,
  BarChart3, GitBranch, Shield,
} from "lucide-react";

function StrategyRow({ s }: { s: StrategyRegistryEntry }) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/10 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white truncate">{s.name}</span>
          <Badge variant={s.enabled ? "success" : "default"}>
            {s.enabled ? "Active" : "Disabled"}
          </Badge>
        </div>
        <p className="text-xs text-white/30 mt-0.5 truncate">{s.description}</p>
      </div>
      <div className="flex items-center gap-3 text-xs text-white/40">
        <span className="font-mono">{s.category}</span>
        <span>{s.asset_classes.join(", ")}</span>
        <span>{s.timeframes.join(", ")}</span>
      </div>
    </div>
  );
}

function PipelineStageRow({ stage }: { stage: PipelineStatus["stages"][0] }) {
  const isActive = stage.status === "active";
  const isError = stage.status === "error";

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02]">
      <div className={cn(
        "w-2 h-2 rounded-full",
        isActive ? "bg-emerald-500" : isError ? "bg-red-500" : "bg-white/20",
      )} />
      <span className="text-sm text-white/70 flex-1">{stage.name}</span>
      <span className="text-xs font-mono text-white/30">
        {stage.last_run ? new Date(stage.last_run).toLocaleTimeString() : "—"}
      </span>
      <Badge variant={isActive ? "success" : isError ? "danger" : "default"}>
        {stage.status}
      </Badge>
    </div>
  );
}

function EvaluatorContent() {
  const [strategies, setStrategies] = useState<StrategyRegistryEntry[]>([]);
  const [evolution, setEvolution] = useState<EvaluatorEvolutionStatus | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [reg, evo, pipe] = await Promise.allSettled([
        evaluatorApi.getRegistry(),
        evaluatorApi.getEvolutionStatus(),
        evaluatorApi.getPipelineStatus(),
      ]);
      if (reg.status === "fulfilled") setStrategies(reg.value);
      if (evo.status === "fulfilled") setEvolution(evo.value);
      if (pipe.status === "fulfilled") setPipeline(pipe.value);
    } catch {
      setError("Backend unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

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

  const filtered = strategies.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Strategy Evaluator</h1>
          <p className="text-sm text-white/40 mt-1">Rolling Sharpe, auto-disable, pipeline health</p>
        </div>
        <Button onClick={loadData} variant="ghost" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatusCard title="Total Strategies" value={strategies.length} icon={<Sigma className="w-4 h-4" />} />
        <StatusCard title="Active" value={strategies.filter(s => s.enabled).length} icon={<CheckCircle2 className="w-4 h-4" />} variant="success" />
        <StatusCard title="Disabled" value={strategies.filter(s => !s.enabled).length} icon={<XCircle className="w-4 h-4" />} variant="warning" />
        <StatusCard
          title="Pipeline"
          value={pipeline?.running ? "Running" : "Idle"}
          icon={<Activity className="w-4 h-4" />}
          variant={pipeline?.running ? "success" : "default"}
        />
        <StatusCard
          title="Success Rate"
          value={pipeline ? `${Math.round(pipeline.success_rate * 100)}%` : "—"}
          icon={<BarChart3 className="w-4 h-4" />}
        />
      </div>

      {/* Evolution Status */}
      {evolution && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">Evolution Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="text-center">
              <div className="text-lg font-mono text-white">{evolution.total_strategies}</div>
              <div className="text-xs text-white/30">Total</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-mono text-emerald-400">{evolution.active_strategies}</div>
              <div className="text-xs text-white/30">Active</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-mono text-red-400">{evolution.disabled_strategies}</div>
              <div className="text-xs text-white/30">Disabled</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-white/30 mt-1">Last Evaluation</div>
              <div className="text-sm font-mono text-white/60">
                {evolution.last_evaluation ? new Date(evolution.last_evaluation).toLocaleString() : "—"}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-white/30 mt-1">Last Evolution</div>
              <div className="text-sm font-mono text-white/60">
                {evolution.last_evolution ? new Date(evolution.last_evolution).toLocaleString() : "—"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline Stages */}
      {pipeline && pipeline.stages.length > 0 && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">Pipeline Stages</h2>
          <div className="space-y-1">
            {pipeline.stages.map((stage) => (
              <PipelineStageRow key={stage.id} stage={stage} />
            ))}
          </div>
        </div>
      )}

      {/* Strategy Registry */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider">Strategy Registry</h2>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-emerald-500/50 w-48"
            placeholder="Search strategies..."
          />
        </div>
        <div className="space-y-2">
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-white/30 text-sm">
              No strategies found in registry.
            </div>
          ) : (
            filtered.map((s) => <StrategyRow key={s.name} s={s} />)
          )}
        </div>
      </div>
    </div>
  );
}

export default function EvaluatorPage() {
  return (
    <ErrorBoundary>
      <EvaluatorContent />
    </ErrorBoundary>
  );
}
