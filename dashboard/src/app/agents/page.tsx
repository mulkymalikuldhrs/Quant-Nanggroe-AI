"use client";

import React, { useEffect, useState } from "react";
import { AgentCard } from "@/components/shared/agent-card";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useAppStore } from "@/lib/store";
import { agentsApi } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  Bot,
  Play,
  Search,
  Network,
  AlertTriangle,
  Skull,
  RefreshCw,
} from "lucide-react";

const iconMap: Record<string, string> = {
  researcher: "🔍", strategist: "🎯", risk: "🛡️", trader: "📈",
  portfolio: "💼", execution: "⚡", macro: "🌍", crypto: "₿", forex: "💱",
};

const iconMap: Record<string, string> = {
  researcher: "🔍", strategist: "🎯", risk: "🛡️", trader: "📈",
  portfolio: "💼", execution: "⚡", macro: "🌍", crypto: "₿", forex: "💱",
};

export default function AgentsPage() {
  const { agentsData, killSwitch, toggleKillSwitch, fetchAgents } = useAppStore();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [runSymbol, setRunSymbol] = useState("AAPL");
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => { fetchAgents(); }, []);

  const displayAgents = agentsData?.agents?.map((a) => ({
    id: a.name,
    name: a.name.charAt(0).toUpperCase() + a.name.slice(1),
    status: a.status === "ready" ? "active" : a.status,
    icon: iconMap[a.name] || "🤖",
  })) || [];

  const filteredAgents = displayAgents.filter(
    (a) => a.name.toLowerCase().includes(searchTerm.toLowerCase()) || a.id.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const activeCount = displayAgents.filter((a) => a.status === "active").length;

  const handleRunPipeline = async () => {
    setIsRunning(true);
    try {
      await agentsApi.run(runSymbol);
    } catch { /* silent */ }
    setIsRunning(false);
  };

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Bot className="w-5 h-5 text-emerald-400" />
            Agent Council
          </h1>
          <p className="text-sm text-white/40 mt-0.5">{activeCount} of {displayAgents.length} agents active</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            <Skull className="w-3.5 h-3.5 text-red-400" />
            <span className="text-xs text-white/50">Kill Switch</span>
            <Switch checked={killSwitch} onCheckedChange={toggleKillSwitch} />
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 flex-1">
          <Input placeholder="Search agents..." icon={<Search className="w-3.5 h-3.5" />} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
        </div>
        <div className="flex items-center gap-2">
          <Input placeholder="Symbol" value={runSymbol} onChange={(e) => setRunSymbol(e.target.value)} className="w-28" />
          <Button variant="glow" onClick={handleRunPipeline} disabled={isRunning || killSwitch}>
            {isRunning ? <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1.5" />}
            {isRunning ? "Running..." : "Run Pipeline"}
          </Button>
        </div>
      </div>

      {killSwitch && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2 animate-slide-up">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">Kill switch is active. All agent operations are suspended.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {filteredAgents.map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
            className={cn(selectedAgent === agent.id && "ring-1 ring-emerald-500/30")}
          />
        ))}
      </div>

        <ChartCard title="Agent Graph" subtitle={`${displayAgents.length} agents registered`} action={<Badge variant="info"><Network className="w-3 h-3 mr-1" />Live</Badge>}>
        <div className="relative w-full overflow-x-auto">
          <svg viewBox="0 0 800 500" className="w-full min-w-[600px] h-auto" style={{ maxHeight: "400px" }}>
            {displayAgents.map((agent, i) => {
              const cols = Math.min(displayAgents.length, 6);
              const cx = 100 + (i % cols) * 120 + 60;
              const cy = 60 + Math.floor(i / cols) * 120;
              const isActive = agent.status === "active";
              const isSelected = selectedAgent === agent.id;
              return (
                <g key={agent.id} onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)} className="cursor-pointer">
                  <circle cx={cx} cy={cy} r={isSelected ? 32 : 28} fill={isActive ? "rgba(16,185,129,0.1)" : "rgba(255,255,255,0.03)"} stroke={isSelected ? "#10b981" : isActive ? "rgba(16,185,129,0.3)" : "rgba(255,255,255,0.08)"} strokeWidth={isSelected ? 2 : 1} />
                  {isActive && <circle cx={cx} cy={cy} r={28} fill="none" stroke="rgba(16,185,129,0.15)" strokeWidth={4} className="animate-pulse" />}
                  <text x={cx} y={cy - 4} textAnchor="middle" fill="white" fontSize="16" className="pointer-events-none">{agent.icon || "🤖"}</text>
                  <text x={cx} y={cy + 12} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="8" className="pointer-events-none">{agent.name}</text>
                </g>
              );
            })}
          </svg>
        </div>
      </ChartCard>
    </div>
  );
}
