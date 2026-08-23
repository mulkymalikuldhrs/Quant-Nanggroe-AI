"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cpu,
  DollarSign,
  Download,
  FileText,
  Filter,
  GitBranch,
  Play,
  RefreshCw,
  ScrollText,
  Shield,
  ShieldAlert,
  Sliders,
  Terminal,
  TrendingUp,
  Users,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";

const PIPELINE_COMPONENTS = [
  {
    id: "data_fetch", name: "Data Fetch", stage: 1, icon: Download,
    description: "OHLCV + market data from yfinance / MT5 / data providers",
    status: "operational" as const,
    config: { sources: ["yfinance", "MT5", "DataProviderManager"], cache_ttl: 300, fallback_enabled: true },
    metrics: { last_fetch: "12s ago", bars: 500, symbols: 5 },
  },
  {
    id: "regime_detection", name: "Regime Detection", stage: 2, icon: Activity,
    description: "HMM-based market regime detection (trending, ranging, volatile, crisis, recovery)",
    status: "operational" as const,
    config: { method: "HMM", lookback: 100, min_confidence: 0.35 },
    metrics: { regime: "ranging", confidence: 0.72, last_detected: "12s ago" },
  },
  {
    id: "aihf_bridge", name: "AIHF Bridge", stage: 3, icon: Brain,
    description: "20 AI agents vote on market direction",
    status: "operational" as const,
    config: { agents: 20, override_threshold: 0.6, min_consensus: 0.3 },
    metrics: { agents_contributing: 14, buy_conf: 0.45, sell_conf: 0.32 },
  },
  {
    id: "hf_bridge", name: "Hedge Fund Bridge", stage: 4, icon: TrendingUp,
    description: "hedge_fund.py's 10 core signal providers",
    status: "operational" as const,
    config: { providers: 10, skip_qna_evolved: true, method: "weighted_vote" },
    metrics: { vote: "buy", confidence: 0.58, providers_contributing: 6 },
  },
  {
    id: "strategy_loading", name: "Strategy + Genes", stage: 5, icon: GitBranch,
    description: "Auto-discover strategies + MUE-X evolved genes",
    status: "operational" as const,
    config: { auto_discover: true, gene_loader: true },
    metrics: { canonical: 28, genes: 34, active: 17 },
  },
  {
    id: "regime_filter", name: "RegimeFilter", stage: 6, icon: Filter,
    description: "Filters strategies by regime compatibility (min 0.35)",
    status: "operational" as const,
    config: { min_compatibility: 0.35, enabled: true },
    metrics: { compatible: 12, total: 62, filtered_out: 50 },
  },
  {
    id: "ensemble_voting", name: "Ensemble Voting", stage: 7, icon: Users,
    description: "Regime-weighted voting across strategies",
    status: "operational" as const,
    config: { weights: "regime_based", max_candidates: 15, min_consensus: 0.3 },
    metrics: { buy_weight: 0.55, sell_weight: 0.28, consensus: "buy" },
  },
  {
    id: "council_debate", name: "Council Debate", stage: 8, icon: Users,
    description: "Multi-agent council debate when confidence < threshold",
    status: "operational" as const,
    config: { debate_threshold: 0.6, council_size: 5, debate_rounds: 3 },
    metrics: { debates_held: 2, override_rate: "33%", avg_confidence_boost: 0.12 },
  },
  {
    id: "risk_check", name: "Risk Check", stage: 9, icon: Shield,
    description: "9-gate RiskManager: KillSwitch, CooldownGuard, ATR sizing",
    status: "operational" as const,
    config: { kill_switch: true, max_risk_per_trade: 0.01, cooldown_minutes: 5, max_positions: 3 },
    metrics: { kill_switch: "inactive", cooldown: "ready", max_positions: "3/3" },
  },
  {
    id: "final_decider", name: "Final Decider", stage: 10, icon: ShieldAlert,
    description: "One Final Veto — portfolio + risk + kelly + SL/TP",
    status: "operational" as const,
    config: { min_confidence: 0.6, min_rr_ratio: 2.5, kelly_fraction: 0.25, min_regime_compat: 0.35 },
    metrics: { last_decision: "buy", confidence: 0.72, kelly: 0.18 },
  },
  {
    id: "execution", name: "Execution (MT5/Paper)", stage: 11, icon: Terminal,
    description: "MT5 live execution or Paper mode",
    status: "operational" as const,
    config: { mode: "paper", broker: "MT5", slippage: 0.001, order_type: "MARKET" },
    metrics: { mode: "paper", orders_filled: 0, last_execution: "never" },
  },
  {
    id: "strategy_logger", name: "Strategy Logger", stage: 12, icon: ScrollText,
    description: "Logs EVERY triggered strategy",
    status: "operational" as const,
    config: { log_dir: "data", log_all_signals: true, log_format: "json" },
    metrics: { total_logs: 128, last_log: "23s ago", strategies_logged: 17 },
  },
  {
    id: "pnl_evaluator", name: "PnL Evaluator", stage: 13, icon: DollarSign,
    description: "Closed-PnL evaluation → fine-tune trigger",
    status: "operational" as const,
    config: { stats_dir: "data/strategy_stats", min_trades_for_eval: 3, fine_tune_win_rate: 0.4, fine_tune_sharpe: 0.5 },
    metrics: { trades_evaluated: 0, fine_tunes_triggered: 0, avg_win_rate: "—" },
  },
  {
    id: "evolve", name: "Evolve & Repeat", stage: 14, icon: RefreshCw,
    description: "Self-correcting loop — lessons recorded → auto-improve",
    status: "operational" as const,
    config: { self_correction: true, lesson_path: "data/lessons.json", auto_repeat: true },
    metrics: { cycle_count: 5, lessons_learned: 12, unresolved: 3 },
  },
  {
    id: "hf_standalone", name: "Hedge Fund (Standalone)", stage: 15, icon: Cpu,
    description: "Original standalone — now bridged as signal provider",
    status: "archived" as const,
    config: { file: "hedge_fund.py", lines: 6693, status: "bridge_active", paper_only: true },
    metrics: { run_count: 0, trades: 0, logs: "none" },
  },
];

type PipelineComponent = (typeof PIPELINE_COMPONENTS)[number];

export default function PipelinePage() {
  const { killSwitch } = useAppStore();
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [filter, setFilter] = useState<"all" | "operational" | "degraded" | "archived">("all");
  const [time, setTime] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [componentConfigs, setComponentConfigs] = useState<Record<string, Record<string, boolean>>>({});
  const [liveData, setLiveData] = useState<PipelineComponent[] | null>(null);

  const toggleConfig = useCallback((componentId: string, key: string) => {
    setComponentConfigs((prev) => ({
      ...prev,
      [componentId]: { ...(prev[componentId] || {}), [key]: !(prev[componentId]?.[key]) },
    }));
  }, []);

  const fetchPipelineStatus = useCallback(async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/pipeline/status`, { cache: "no-store" });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      if (data?.stages && Array.isArray(data.stages)) setLiveData(data.stages);
      setError(null);
    } catch (err) {
      console.debug("Pipeline API fetch failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPipelineStatus(); }, [fetchPipelineStatus]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      setTime(new Date());
      fetchPipelineStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchPipelineStatus]);

  // fail-closed: show empty state when backend unavailable, never fabricated metrics
  const components = liveData ?? [];
  const usingFallback = !liveData;
  const filtered = filter === "all" ? components : components.filter((c: PipelineComponent) => c.status === filter);

  // ── PipelineCard (moved inside for closure access) ─────────────
  function PipelineCard({ component, index }: { component: PipelineComponent; index: number }) {
    const [expanded, setExpanded] = useState(false);
    const Icon = component.icon;
    const isOperational = component.status === "operational";
    const statusColor = isOperational ? "text-emerald-400" : "text-gray-500";
    const statusBg = isOperational
      ? "bg-emerald-500/10 border-emerald-500/20"
      : "bg-gray-500/10 border-gray-500/20";

    return (
      <div className={`group rounded-xl border ${statusBg} backdrop-blur-sm transition-all duration-300 hover:border-white/20 hover:bg-white/[0.04]`}>
        <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center gap-4 p-4 text-left">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/[0.06] flex items-center justify-center text-xs font-mono text-white/40">
            {String(component.stage).padStart(2, "0")}
          </div>
          <div className={`flex-shrink-0 w-10 h-10 rounded-lg bg-white/[0.04] flex items-center justify-center ${statusColor}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium text-white/90 truncate">{component.name}</h3>
              <div className={`flex-shrink-0 w-1.5 h-1.5 rounded-full ${isOperational ? "bg-emerald-400" : "bg-gray-500"}`} />
            </div>
            <p className="text-xs text-white/40 mt-0.5 line-clamp-1">{component.description}</p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className={`text-[10px] uppercase tracking-wider font-medium ${statusColor}`}>{component.status}</span>
            {expanded ? <ChevronDown className="w-4 h-4 text-white/30" /> : <ChevronRight className="w-4 h-4 text-white/30" />}
          </div>
        </button>

        {expanded && (
          <div className="px-4 pb-4 pt-0 border-t border-white/[0.06] animate-slide-up">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3">
              <div>
                <h4 className="text-[10px] uppercase tracking-wider text-white/30 font-medium mb-2 flex items-center gap-1.5">
                  <Sliders className="w-3 h-3" /> Configuration
                </h4>
                <div className="space-y-1.5">
                  {Object.entries(component.config).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between py-1">
                      <span className="text-xs text-white/40 font-mono">{key.replace(/_/g, " ")}</span>
                      <div className="flex items-center gap-2">
                        {typeof value === "boolean" ? (
                          <button onClick={() => toggleConfig(component.id, key)}
                            className={`w-8 h-4 rounded-full transition-colors duration-200 cursor-pointer ${componentConfigs[component.id]?.[key] ?? value ? "bg-emerald-500" : "bg-white/[0.1]"} relative`}>
                            <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform duration-200 ${componentConfigs[component.id]?.[key] ?? value ? "translate-x-4" : "translate-x-0.5"}`} />
                          </button>
                        ) : (
                          <span className="text-xs text-white/70 font-mono bg-white/[0.04] px-2 py-0.5 rounded">{String(value)}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="text-[10px] uppercase tracking-wider text-white/30 font-medium mb-2 flex items-center gap-1.5">
                  <Activity className="w-3 h-3" /> Metrics
                </h4>
                <div className="space-y-1.5">
                  {Object.entries(component.metrics).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between py-1">
                      <span className="text-xs text-white/40 font-mono">{key.replace(/_/g, " ")}</span>
                      <span className="text-xs text-emerald-400/80 font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-[10px] uppercase tracking-wider font-medium transition-colors duration-200 border border-emerald-500/20 active:scale-95"
                    title={`Run ${component.id}`}
                  >
                    <Play className="w-3 h-3" /> Run
                  </button>
                  <button
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-white/60 text-[10px] uppercase tracking-wider font-medium transition-colors duration-200 border border-white/[0.06] active:scale-95"
                    title={`Configure ${component.id}`}
                  >
                    <Sliders className="w-3 h-3" /> Configure
                  </button>
                  <button
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-white/40 text-[10px] uppercase tracking-wider font-medium transition-colors duration-200 border border-white/[0.06] active:scale-95"
                    title={`View logs for ${component.id}`}
                  >
                    <FileText className="w-3 h-3" /> Logs
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {index < components.length - 1 && (
          <div className="flex justify-center pb-0">
            <div className="w-px h-4 bg-gradient-to-b from-white/[0.08] to-transparent" />
          </div>
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4 p-6">
        <LoadingSkeleton /><LoadingSkeleton /><LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <AlertTriangle className="w-12 h-12 text-amber-400" />
        <p className="text-white/60">{error}</p>
        <button onClick={() => { setError(null); setLoading(true); setTimeout(() => setLoading(false), 600); }}
          className="px-4 py-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-white/80 text-sm transition-colors">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white/90 tracking-tight">Pipeline</h1>
          <p className="text-sm text-white/40 mt-1">
            Autonomous Hedge Fund Pipeline — {components.length} stages, {components.filter((c: PipelineComponent) => c.status === "operational").length} operational
            {killSwitch && <span className="ml-2 text-red-400">· Kill Switch Active</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06]">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-white/60 font-mono">{time.toLocaleTimeString()}</span>
          </div>
          <button onClick={() => setAutoRefresh(!autoRefresh)}
            className={`p-2 rounded-lg transition-colors duration-200 ${autoRefresh ? "bg-emerald-500/10 text-emerald-400" : "bg-white/[0.04] text-white/40"}`}>
            <RefreshCw className={`w-4 h-4 ${autoRefresh ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-2">
        {(["all", "operational", "degraded", "archived"] as const).map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-[10px] uppercase tracking-wider font-medium transition-all duration-200 ${filter === f ? "bg-white/[0.08] text-white border border-white/[0.1]" : "text-white/30 hover:text-white/50 hover:bg-white/[0.04] border border-transparent"}`}>
            {f}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Stages", value: components.length, icon: GitBranch, color: "text-blue-400" },
          { label: "Operational", value: components.filter((c: PipelineComponent) => c.status === "operational").length, icon: CheckCircle2, color: "text-emerald-400" },
          { label: "Degraded", value: components.filter((c) => (c.status as string) === "degraded").length, icon: AlertTriangle, color: "text-amber-400" },
          { label: "Health", value: `${Math.round((components.filter((c: PipelineComponent) => c.status === "operational").length / components.length) * 100)}%`, icon: Activity, color: "text-violet-400" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 backdrop-blur-sm hover:border-white/10 transition-colors duration-200">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg bg-white/[0.04] flex items-center justify-center ${stat.color}`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-semibold text-white/90">{stat.value}</p>
                <p className="text-[10px] uppercase tracking-wider text-white/30">{stat.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {liveData && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px]">
          <Activity className="w-3 h-3" /> Live data from API
        </div>
      )}

      <div className="rounded-xl bg-gradient-to-br from-white/[0.02] to-transparent border border-white/[0.06] p-6 backdrop-blur-sm">
        <h3 className="text-xs uppercase tracking-wider text-white/30 font-medium mb-4">Pipeline Flow</h3>
        <div className="flex flex-wrap items-center gap-2">
          {components.slice(0, 14).map((comp: PipelineComponent, i: number) => (
            <React.Fragment key={comp.id}>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] transition-colors cursor-default">
                <comp.icon className="w-3 h-3 text-emerald-400/80" />
                <span className="text-[10px] text-white/60 font-medium whitespace-nowrap">{comp.stage}. {comp.name}</span>
              </div>
              {i < 13 && <ChevronRight className="w-3 h-3 text-white/20 flex-shrink-0" />}
            </React.Fragment>
          ))}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <RefreshCw className="w-3 h-3 text-emerald-400" />
            <span className="text-[10px] text-emerald-400 font-medium">Repeat</span>
          </div>
        </div>
      </div>

      <div className="space-y-1">
        {filtered.map((component: PipelineComponent, index: number) => (
          <PipelineCard key={component.id} component={component} index={index} />
        ))}
      </div>
    </div>
  );
}
