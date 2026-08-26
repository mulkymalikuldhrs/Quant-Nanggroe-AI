"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { causalApi } from "@/lib/api-client";
import type {
  CausalStatus, CotData, MsiData, SmtPair, ThesisData,
  BiasData, MacroWeather, CausalPipelineStage,
} from "@/lib/api-client";
import { cn, formatPercent } from "@/lib/utils";
import {
  Database, RefreshCw, TrendingUp, TrendingDown, Minus, AlertTriangle,
  Globe, Activity, BarChart3, Zap, Shield, GitBranch, Cpu,
} from "lucide-react";

function CausalPipelineRow({ stage }: { stage: CausalPipelineStage }) {
  const isActive = stage.status === "active";
  const isError = stage.status === "error";

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02]">
      <div className={cn(
        "w-2 h-2 rounded-full",
        isActive ? "bg-emerald-500" : isError ? "bg-red-500" : "bg-white/20",
      )} />
      <span className="text-sm text-white/70 flex-1">{stage.name}</span>
      <span className="text-xs font-mono text-white/30">{stage.data_points} pts</span>
      <span className="text-xs font-mono text-white/30">
        {stage.last_run ? new Date(stage.last_run).toLocaleTimeString() : "—"}
      </span>
      <Badge variant={isActive ? "success" : isError ? "danger" : "default"}>
        {stage.status}
      </Badge>
    </div>
  );
}

function CotRow({ inst }: { inst: CotData["instruments"][0] }) {
  const SentIcon = inst.sentiment === "bullish" ? TrendingUp : inst.sentiment === "bearish" ? TrendingDown : Minus;
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02]">
      <span className="text-sm text-white/70 flex-1">{inst.name}</span>
      <span className={cn("text-xs font-mono", inst.net_long > 0 ? "text-emerald-400" : "text-red-400")}>
        {inst.net_long > 0 ? "+" : ""}{inst.net_long}
      </span>
      <span className={cn("text-xs font-mono", inst.change_week > 0 ? "text-emerald-400" : "text-red-400")}>
        {inst.change_week > 0 ? "+" : ""}{inst.change_week}
      </span>
      <Badge variant={inst.sentiment === "bullish" ? "success" : inst.sentiment === "bearish" ? "danger" : "default"}>
        <SentIcon className="w-3 h-3 mr-1" />
        {inst.sentiment}
      </Badge>
    </div>
  );
}

function BiasRow({ bias }: { bias: BiasData }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02]">
      <span className="text-sm text-white/70 flex-1">{bias.name}</span>
      <span className="text-xs font-mono text-white/40">{bias.source}</span>
      <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full",
            bias.direction === "bullish" ? "bg-emerald-500" : bias.direction === "bearish" ? "bg-red-500" : "bg-white/30",
          )}
          style={{ width: `${bias.strength * 100}%` }}
        />
      </div>
      <Badge variant={bias.direction === "bullish" ? "success" : bias.direction === "bearish" ? "danger" : "default"}>
        {bias.direction}
      </Badge>
    </div>
  );
}

function DataPipelineContent() {
  const [status, setStatus] = useState<CausalStatus | null>(null);
  const [cot, setCot] = useState<CotData | null>(null);
  const [msi, setMsi] = useState<MsiData | null>(null);
  const [smtPairs, setSmtPairs] = useState<SmtPair[]>([]);
  const [thesis, setThesis] = useState<ThesisData | null>(null);
  const [biases, setBiases] = useState<BiasData[]>([]);
  const [weather, setWeather] = useState<MacroWeather | null>(null);
  const [pipeline, setPipeline] = useState<CausalPipelineStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.allSettled([
        causalApi.getStatus(),
        causalApi.getCotData(),
        causalApi.getMsi(),
        causalApi.getSmtPairs(),
        causalApi.getThesis(),
        causalApi.getBiases(),
        causalApi.getMacroWeather(),
        causalApi.getPipeline(),
      ]);
      if (results[0].status === "fulfilled") setStatus(results[0].value);
      if (results[1].status === "fulfilled") setCot(results[1].value);
      if (results[2].status === "fulfilled") setMsi(results[2].value);
      if (results[3].status === "fulfilled") setSmtPairs(results[3].value);
      if (results[4].status === "fulfilled") setThesis(results[4].value);
      if (results[5].status === "fulfilled") setBiases(results[5].value);
      if (results[6].status === "fulfilled") setWeather(results[6].value);
      if (results[7].status === "fulfilled") setPipeline(results[7].value);
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Pipeline</h1>
          <p className="text-sm text-white/40 mt-1">Causal engine, COT, SMT, macro weather, biases</p>
        </div>
        <Button onClick={loadData} variant="ghost" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Status + MSI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard
          title="Causal Engine"
          value={status?.running ? "Running" : "Idle"}
          icon={<Cpu className="w-4 h-4" />}
          variant={status?.running ? "success" : "default"}
        />
        <StatusCard title="MSI" value={msi ? `${msi.value}` : "—"} icon={<Activity className="w-4 h-4" />} />
        <StatusCard title="Macro Regime" value={weather?.regime ?? "—"} icon={<Globe className="w-4 h-4" />} />
        <StatusCard title="DXY" value={weather?.dxy ? weather.dxy.toFixed(2) : "—"} icon={<BarChart3 className="w-4 h-4" />} />
      </div>

      {/* Thesis */}
      {thesis && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-2">Current Thesis</h2>
          <p className="text-sm text-white/70 mb-2">{thesis.current_thesis}</p>
          <div className="flex items-center gap-4 text-xs text-white/40">
            <span>Confidence: <span className="text-emerald-400 font-mono">{formatPercent(thesis.confidence)}</span></span>
            <span>Drift: <span className={cn("font-mono", thesis.drift > 0.3 ? "text-amber-400" : "text-white/40")}>{thesis.drift.toFixed(2)}</span></span>
            <span>Factors: {thesis.factors.join(", ")}</span>
          </div>
        </div>
      )}

      {/* Macro Weather */}
      {weather && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">Macro Weather</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="text-center">
              <div className={cn("text-lg font-mono", weather.risk_on ? "text-emerald-400" : "text-red-400")}>
                {weather.risk_on ? "Risk-On" : "Risk-Off"}
              </div>
              <div className="text-xs text-white/30">Regime</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-mono text-white">{weather.vix?.toFixed(1) ?? "—"}</div>
              <div className="text-xs text-white/30">VIX</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-mono text-white">{weather.dxy?.toFixed(2) ?? "—"}</div>
              <div className="text-xs text-white/30">DXY</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-mono text-white">{Object.keys(weather.yields).length}</div>
              <div className="text-xs text-white/30">Yield Series</div>
            </div>
          </div>
        </div>
      )}

      {/* Two Column: COT + SMT */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* COT */}
        {cot && (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider">CFTC COT Data</h2>
              <span className="text-xs text-white/30 font-mono">
                {cot.updated_at ? new Date(cot.updated_at).toLocaleDateString() : "—"}
              </span>
            </div>
            <div className="space-y-1">
              {cot.instruments.length === 0 ? (
                <div className="text-center py-6 text-white/30 text-xs">No COT data available</div>
              ) : (
                cot.instruments.map((inst) => <CotRow key={inst.name} inst={inst} />)
              )}
            </div>
          </div>
        )}

        {/* SMT */}
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">SMT Divergences</h2>
          <div className="space-y-1">
            {smtPairs.length === 0 ? (
              <div className="text-center py-6 text-white/30 text-xs">No SMT data available</div>
            ) : (
              smtPairs.map((pair) => (
                <div key={pair.pair} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02]">
                  <span className="text-sm text-white/70 flex-1">{pair.pair}</span>
                  <span className="text-xs font-mono text-white/40">{pair.strength.toFixed(2)}</span>
                  <Badge variant={pair.divergence ? "warning" : "default"}>
                    {pair.divergence ? "Divergence" : "Aligned"}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Biases */}
      {biases.length > 0 && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">Detected Biases</h2>
          <div className="space-y-1">
            {biases.map((bias, i) => <BiasRow key={i} bias={bias} />)}
          </div>
        </div>
      )}

      {/* Causal Pipeline */}
      {pipeline.length > 0 && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">Causal Pipeline</h2>
          <div className="space-y-1">
            {pipeline.map((stage) => (
              <CausalPipelineRow key={stage.id} stage={stage} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DataPipelinePage() {
  return (
    <ErrorBoundary>
      <DataPipelineContent />
    </ErrorBoundary>
  );
}
