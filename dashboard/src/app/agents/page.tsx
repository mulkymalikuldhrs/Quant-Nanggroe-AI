"use client";
export const dynamic = "force-dynamic";

import React, { useState } from "react";
import { AgentCard } from "@/components/shared/agent-card";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { mockAgents } from "@/lib/mock-data";
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

// Agent graph visualization - nodes and edges
const agentGraph = {
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
  ],
};

export default function AgentsPage() {
  const { killSwitch, toggleKillSwitch } = useAppStore();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [runSymbol, setRunSymbol] = useState("AAPL");
  const [isRunning, setIsRunning] = useState(false);

  const filteredAgents = mockAgents.filter(
    (a) =>
      a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.id.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const activeCount = mockAgents.filter((a) => a.status === "active").length;

  const handleRunPipeline = async () => {
    setIsRunning(true);
    setTimeout(() => setIsRunning(false), 3000);
  };

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
            {activeCount} of 11 agents active • LangGraph orchestration
          </p>
        </div>
        <div className="flex items-center gap-3">
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

      {/* Kill Switch Warning */}
      {killSwitch && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2 animate-slide-up">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">
            Kill switch is active. All agent operations are suspended. Trading and pipeline execution disabled.
          </p>
        </div>
      )}

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {filteredAgents.map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
            className={cn(
              selectedAgent === agent.id && "ring-1 ring-emerald-500/30",
            )}
          />
        ))}
      </div>

      {/* Agent Graph Visualization */}
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
            {agentGraph.edges.map(([from, to], i) => {
              const fromNode = agentGraph.nodes.find((n) => n.id === from)!;
              const toNode = agentGraph.nodes.find((n) => n.id === to)!;
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
            {agentGraph.nodes.map((node) => {
              const agent = mockAgents.find((a) => a.id === node.id);
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
    </div>
  );
}
