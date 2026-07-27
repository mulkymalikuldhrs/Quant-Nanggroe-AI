"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { colonyApi, agentsApi } from "@/lib/api-client";
import type { Colony, Agent } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  Network,
  RefreshCw,
  AlertCircle,
  Plus,
  Play,
} from "lucide-react";

export default function ColonyPage() {
  const [colonies, setColonies] = useState<Colony[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [coloniesData, agentsData] = await Promise.all([
        colonyApi.list(),
        agentsApi.getStatus(),
      ]);
      setColonies(coloniesData);
      setAgents(agentsData.agents);
    } catch (err) {
      setError("Colony API unavailable — check backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return (
    <div className="space-y-4 animate-slide-up">
      <div className="h-8 w-48 rounded-lg bg-white/5 animate-pulse" />
      <LoadingSkeleton variant="page" />
    </div>
  );

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Network className="w-5 h-5 text-cyan-400" />
            Colony Network
          </h1>
          <p className="text-sm text-white/40 mt-0.5">{colonies.length} colonies &bull; {agents.length} agents</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-7 px-2 text-white/30 hover:text-white/50" onClick={loadData} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Colony engine status */}
      <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 flex items-center gap-3">
        <Badge variant="success" className="text-xs">Live</Badge>
        <p className="text-sm text-white/50">Colony orchestration powered by ColonyOrchestrator — real worker lifecycle, task dispatch, and health monitoring.</p>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <p className="text-sm text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={loadData}>
            <RefreshCw className="w-3 h-3 mr-1" /> Retry
          </Button>
        </div>
      )}

      {/* Colony Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatusCard title="Active Colonies" value={colonies.filter(c => c.status === "active").length} variant="success" />
        <StatusCard title="Total Agents" value={agents.length} />
        <StatusCard title="Avg Health" value={colonies.length > 0 ? `${Math.round(colonies.reduce((s, c) => s + c.health, 0) / colonies.length)}%` : "—"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Colony Grid */}
        <ChartCard title="Colonies" subtitle="Agent colony management" className="lg:col-span-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {colonies.map((colony) => (
              <Card key={colony.id} className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={cn("w-3 h-3 rounded-full", colony.status === "active" ? "bg-emerald-400" : "bg-amber-400")} />
                    <h3 className="text-sm font-medium text-white">{colony.name}</h3>
                  </div>
                  <Badge variant={colony.status === "active" ? "success" : "warning"} className="text-[10px]">
                    {colony.status}
                  </Badge>
                </div>
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-white/30">Health</span>
                      <span className="text-white/60">{colony.health}%</span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500" style={{ width: `${colony.health}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-white/30">Capacity</span>
                      <span className="text-white/60">{colony.agents}/{colony.capacity}</span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-purple-500/60" style={{ width: `${(colony.agents / colony.capacity) * 100}%` }} />
                    </div>
                  </div>
                  <p className="text-[10px] text-white/30">Schedule: {colony.schedule}</p>
                </div>
              </Card>
            ))}
          </div>
          <Button variant="glow" className="w-full mt-4">
            <Plus className="w-3.5 h-3.5 mr-1.5" /> Create Colony
          </Button>
        </ChartCard>

        {/* Agent Topology */}
        <ChartCard title="Agent Topology" subtitle="Network nodes">
          <div className="grid grid-cols-3 gap-2">
            {agents.map((agent, i) => (
              <div key={agent.id} className={cn(
                "p-3 rounded-lg border text-center transition-all hover:scale-105",
                agent.status === "active" ? "bg-cyan-500/5 border-cyan-500/20" :
                agent.status === "error" ? "bg-red-500/5 border-red-500/20" :
                "bg-white/[0.02] border-white/5",
              )}>
                <div className={cn(
                  "w-8 h-8 rounded-full mx-auto mb-2 flex items-center justify-center text-xs font-bold",
                  agent.status === "active" ? "bg-cyan-500/20 text-cyan-400" :
                  agent.status === "error" ? "bg-red-500/20 text-red-400" :
                  "bg-white/5 text-white/30",
                )}>
                  {agent.name?.[0]?.toUpperCase() || "?"}
                </div>
                <div className="text-white/70 text-[10px] truncate">{agent.name}</div>
                <div className="text-white/30 text-[9px]">{agent.status}</div>
              </div>
            ))}
          </div>
          <Button variant="default" className="w-full mt-4" size="sm">
            <Play className="w-3 h-3 mr-1" /> Run Colony Task
          </Button>
        </ChartCard>
      </div>
    </div>
  );
}
