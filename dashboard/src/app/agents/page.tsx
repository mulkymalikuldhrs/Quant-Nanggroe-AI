"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect, useCallback } from "react";
import { AgentCard } from "@/components/shared/agent-card";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { agentsApi } from "@/lib/api-client";
import type { Agent, AgentRunRequest, AgentRunResponse } from "@/lib/api-client";
import { useAppStore } from "@/lib/store";
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

// Fallback agents when backend is unavailable
const FALLBACK_AGENTS: Agent[] = [
  { id: "research", name: "Research", status: "active", emotion: "curious", action: "Analyzing market trends", lastDecision: "Bullish on tech sector", icon: "🔬" },
  { id: "market_intel", name: "Market Intel", status: "active", emotion: "focused", action: "Scanning news feeds", lastDecision: "Rate hike probability 65%", icon: "📡" },
  { id: "macro", name: "Macro", status: "active", emotion: "analytical", action: "Processing economic data", lastDecision: "GDP growth revised down", icon: "🌍" },
  { id: "strategy", name: "Strategy", status: "active", emotion: "confident", action: "Optimizing parameters", lastDecision: "Momentum factor overweight", icon: "🧠" },
  { id: "portfolio", name: "Portfolio", status: "idle", emotion: "thoughtful", action: "Rebalancing in progress", lastDecision: "Reduce bond exposure", icon: "📊" },
  { id: "risk", name: "Risk", status: "active", emotion: "cautious", action: "Monitoring VaR limits", lastDecision: "VaR within threshold", icon: "🛡️" },
  { id: "crypto", name: "Crypto", status: "active", emotion: "excited", action: "Tracking on-chain data", lastDecision: "BTC accumulation zone", icon: "₿" },
  { id: "forex", name: "Forex", status: "idle", emotion: "patient", action: "Waiting for setup", lastDecision: "EUR/USD range bound", icon: "💱" },
  { id: "prediction", name: "Prediction", status: "active", emotion: "analytical", action: "Running ML models", lastDecision: "NVDA target $180", icon: "🔮" },
  { id: "trader", name: "Trader", status: "active", emotion: "decisive", action: "Executing strategy signals", lastDecision: "BTC long entry $67,200", icon: "⚡" },
  { id: "execution", name: "Execution", status: "idle", emotion: "neutral", action: "Awaiting orders", lastDecision: "No pending executions", icon: "🤖" },
];

// Agent graph visualization
const AGENT_GRAPH = {
  nodes: [
    { id: "research", x: 250, y: 50, label: "Research" },
    { id: "market_intel", x: 450, y: 50, label: "Market Intel" },
    { id: "macro", x: 650, y: 50, label: "Macro" },
    { id: "strategy", x: 450, y: 180, label: "Strategy" },
    { id: "portfolio", x: 250, y: 180, label: "Portfolio" },
    { id: "risk", x: 650, y: 180, label: "Risk" },
    { id: "crypto", x: 150, y: 310, label: "Crypto" },
    { id: "forex", x: 350, y: 310, label: "Forex" },
    { id: "prediction", x: 550, y: 310, label: "Prediction" },
    { id: "trader", x: 450, y: 430, label: "Trader" },
    { id: "execution", x: 250, y: 430, label: "Execution" },
  ],
  edges: [
    ["research", "strategy"],
    ["market_intel", "strategy"],
    ["macro", "strategy"],
    ["strategy", "portfolio"],
    ["strategy", "risk"],
    ["portfolio", "trader"],
    ["risk", "trader"],
    ["crypto", "strategy"],
    ["forex", "strategy"],
    ["prediction", "strategy"],
    ["trader", "execution"],
  ] as [string, string][],
};

export default function AgentsPage() {
  const { killSwitch, toggleKillSwitch, agents: storeAgents, loadingStates, fetchAgents } = useAppStore();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [runSymbol, setRunSymbol] = useState("AAPL");
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load agents from API on mount
  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  // Use store agents if available, fall back to mock
  const agents = storeAgents.length > 0
    ? storeAgents.map(a => ({
        id: a.name?.toLowerCase().replace(/\s+/g, "_") || a.name,
        name: a.name,
        status: a.status === "active" ? "active" : a.status === "error" ? "error" : "idle" as Agent["status"],
        emotion: "neutral" as const,
        action: a.role || "Processing...",
        lastDecision: a.status === "active" ? "Active and monitoring" : "Waiting",
        icon: "🤖",
      } as Agent))
    : FALLBACK_AGENTS;

  const filteredAgents = agents.filter(
    (a) =>
      a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.id.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const activeCount = agents.filter((a) => a.status === "active").length;

  const handleRunPipeline = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    try {
      await agentsApi.run({ symbol: runSymbol } as AgentRunRequest);
    } catch {
      // Simulate if API unavailable
      await new Promise((r) => setTimeout(r, 3000));
    } finally {
      setIsRunning(false);
    }
  }, [runSymbol]);

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Bot className="w-5 h-5 text-emerald-400" />
            Agent Council
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            {activeCount} of {agents.length} agents active • LangGraph orchestration
            {loadingStates.agents.loading && " • Refreshing..."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-white/30 hover:text-white/50"
            onClick={fetchAgents}
            disabled={loadingStates.agents.loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingStates.agents.loading ? "animate-spin" : ""}`} />
          </Button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            <Skull className="w-3.5 h-3.5 text-red-400" />
            <span className="text-xs text-white/50">Kill Switch</span>
            <Switch checked={killSwitch} onCheckedChange={toggleKillSwitch} />
          </div>
        </div>
      </div>

      {/* Pipeline Runner + Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 flex-1">
          <Input
            placeholder="Search agents..."
            icon={<Search className="w-3.5 h-3.5" />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Symbol"
            value={runSymbol}
            onChange={(e) => setRunSymbol(e.target.value)}
            className="w-28"
          />
          <Button
            variant="glow"
            onClick={handleRunPipeline}
            disabled={isRunning || killSwitch}
          >
            {isRunning ? (
              <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 mr-1.5" />
            )}
            {isRunning ? "Running..." : "Run Pipeline"}
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2 animate-slide-up">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={fetchAgents}>
            <RefreshCw className="w-3 h-3 mr-1" /> Retry
          </Button>
        </div>
      )}

      {/* Kill Switch Warning */}
      {killSwitch && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2 animate-slide-up">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">
            Kill switch is active. All agent operations are suspended. Trading and pipeline execution disabled.
          </p>
        </div>
      )}

      {/* Loading State */}
      {loadingStates.agents.loading && agents.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-white/5 animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          {/* Agent Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filteredAgents.length === 0 ? (
              <div className="col-span-full p-8 text-center text-white/30">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No agents found matching &quot;{searchTerm}&quot;</p>
              </div>
            ) : (
              filteredAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  {...agent}
                  onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
                  className={cn(
                    selectedAgent === agent.id && "ring-1 ring-emerald-500/30",
                  )}
                />
              ))
            )}
          </div>

          {/* Agent Graph Visualization */}
          {agents.length > 0 && (
            <ChartCard
              title="Agent Graph"
              subtitle="LangGraph node orchestration"
              action={
                <Badge variant="info">
                  <Network className="w-3 h-3 mr-1" />
                  Live
                </Badge>
              }
            >
              <div className="relative w-full overflow-x-auto">
                <svg
                  viewBox="0 0 800 500"
                  className="w-full min-w-[600px] h-auto"
                  style={{ maxHeight: "400px" }}
                >
                  {/* Edges */}
                  {AGENT_GRAPH.edges.map(([from, to], i) => {
                    const fromNode = AGENT_GRAPH.nodes.find((n) => n.id === from)!;
                    const toNode = AGENT_GRAPH.nodes.find((n) => n.id === to)!;
                    return (
                      <line
                        key={i}
                        x1={fromNode.x}
                        y1={fromNode.y}
                        x2={toNode.x}
                        y2={toNode.y}
                        stroke="rgba(255,255,255,0.08)"
                        strokeWidth={1.5}
                        strokeDasharray="4,4"
                      />
                    );
                  })}
                  {/* Nodes */}
                  {AGENT_GRAPH.nodes.map((node) => {
                    const agent = agents.find((a) => a.id === node.id);
                    const isActive = agent?.status === "active";
                    const isSelected = selectedAgent === node.id;
                    return (
                      <g key={node.id}>
                        <circle
                          cx={node.x}
                          cy={node.y}
                          r={isSelected ? 32 : 28}
                          fill={isActive ? "rgba(16,185,129,0.1)" : "rgba(255,255,255,0.03)"}
                          stroke={isSelected ? "#10b981" : isActive ? "rgba(16,185,129,0.3)" : "rgba(255,255,255,0.08)"}
                          strokeWidth={isSelected ? 2 : 1}
                          className="cursor-pointer transition-all"
                          onClick={() => setSelectedAgent(selectedAgent === node.id ? null : node.id)}
                        />
                        {isActive && (
                          <circle
                            cx={node.x}
                            cy={node.y}
                            r={28}
                            fill="none"
                            stroke="rgba(16,185,129,0.15)"
                            strokeWidth={4}
                            className="animate-pulse"
                          />
                        )}
                        <text
                          x={node.x}
                          y={node.y - 4}
                          textAnchor="middle"
                          fill="white"
                          fontSize="16"
                          className="pointer-events-none"
                        >
                          {agent?.icon || "🤖"}
                        </text>
                        <text
                          x={node.x}
                          y={node.y + 12}
                          textAnchor="middle"
                          fill="rgba(255,255,255,0.5)"
                          fontSize="8"
                          className="pointer-events-none"
                        >
                          {node.label}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            </ChartCard>
          )}
        </>
      )}
    </div>
  );
}
