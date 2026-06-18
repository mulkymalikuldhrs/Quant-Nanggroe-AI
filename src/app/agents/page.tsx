"use client";

import React, { useEffect, useState } from "react";
import {
  Bot,
  Play,
  Search,
  Activity,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MetricCard, StatusBadge, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";

const AGENT_TYPES = [
  { name: "Researcher", icon: "🔍", color: "cyan" as const, desc: "Market research and data analysis" },
  { name: "Trader", icon: "📈", color: "emerald" as const, desc: "Trade execution and management" },
  { name: "Strategist", icon: "📋", color: "purple" as const, desc: "Strategy development and optimization" },
  { name: "Risk", icon: "🛡️", color: "rose" as const, desc: "Risk assessment and management" },
  { name: "Portfolio", icon: "💼", color: "sky" as const, desc: "Portfolio optimization and allocation" },
  { name: "Execution", icon: "⚡", color: "amber" as const, desc: "Order execution and routing" },
  { name: "Macro", icon: "🌍", color: "cyan" as const, desc: "Macroeconomic analysis" },
  { name: "Crypto", icon: "₿", color: "amber" as const, desc: "Cryptocurrency markets" },
  { name: "Forex", icon: "💱", color: "emerald" as const, desc: "Foreign exchange markets" },
];

export default function AgentsPage() {
  const { agents, loadingAgents, errorAgents, fetchAgents, runAgent } = useAppStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [taskSymbol, setTaskSymbol] = useState("");
  const [taskQuery, setTaskQuery] = useState("");
  const [taskTimeframe, setTaskTimeframe] = useState("1d");
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<{
    status: string;
    decision_action: string;
    risk_verdict: string;
    strategy_signal: string;
    agent_trace: Array<{ agent: string; content: string; confidence: number; success: boolean }>;
  } | null>(null);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const filteredAgents = agents.filter((agent) => {
    const matchesSearch =
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.role.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === "all" || agent.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const activeCount = agents.filter((a) => a.status === "active").length;
  const idleCount = agents.filter((a) => a.status === "idle").length;
  const errorCount = agents.filter((a) => a.status === "error").length;

  const handleRunAgent = async () => {
    if (!taskSymbol) return;
    setIsRunning(true);
    setRunResult(null);
    try {
      const result = await runAgent({
        symbol: taskSymbol,
        query: taskQuery,
        timeframe: taskTimeframe,
      });
      if (result) {
        setRunResult(result as typeof runResult);
      }
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Bot className="w-6 h-6 text-purple" />
            Agent Management
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Deploy, monitor, and manage AI trading agents
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => fetchAgents()} className="cursor-pointer">
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button variant="cyan" onClick={() => setRunDialogOpen(true)} className="gap-2 cursor-pointer">
            <Play className="w-4 h-4" />
            Run Agent
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Agents"
          value={agents.length}
          subtitle="Registered in system"
          icon={<Bot className="w-4 h-4" />}
          color="purple"
          loading={loadingAgents}
        />
        <MetricCard
          title="Active"
          value={activeCount}
          subtitle="Currently processing"
          icon={<Activity className="w-4 h-4" />}
          color="emerald"
          loading={loadingAgents}
        />
        <MetricCard
          title="Idle"
          value={idleCount}
          subtitle="Awaiting tasks"
          icon={<Clock className="w-4 h-4" />}
          color="amber"
          loading={loadingAgents}
        />
        <MetricCard
          title="Errors"
          value={errorCount}
          subtitle="Require attention"
          icon={<AlertTriangle className="w-4 h-4" />}
          color="rose"
          loading={loadingAgents}
        />
      </div>

      {/* Error State */}
      {errorAgents && (
        <div className="p-3 rounded-lg border border-rose/30 bg-rose/5 text-sm text-rose flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {errorAgents}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="idle">Idle</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="offline">Offline</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Agent Cards */}
      <Tabs defaultValue="grid">
        <TabsList>
          <TabsTrigger value="grid">Grid View</TabsTrigger>
          <TabsTrigger value="list">List View</TabsTrigger>
        </TabsList>

        <TabsContent value="grid">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
            {loadingAgents
              ? Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="glass-card p-4 space-y-3">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-32" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                ))
              : filteredAgents.map((agent) => {
                  const typeInfo = AGENT_TYPES.find((t) =>
                    agent.name.toLowerCase().includes(t.name.toLowerCase())
                  ) || AGENT_TYPES[0];
                  return (
                    <div
                      key={agent.name}
                      className="glass-card p-4 hover:border-primary/30 transition-all"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{typeInfo.icon}</span>
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">
                              {agent.name}
                            </h3>
                            <p className="text-xs text-muted-foreground">{agent.role}</p>
                          </div>
                        </div>
                        <StatusBadge status={agent.status} />
                      </div>
                      <p className="text-xs text-muted-foreground mb-3">{typeInfo.desc}</p>
                      <div className="flex items-center justify-between pt-3 border-t border-border/50">
                        <Badge
                          variant={typeInfo.color as "cyan" | "purple" | "emerald" | "amber" | "rose"}
                          className="text-[10px]"
                        >
                          {agent.registered ? "Registered" : "Unregistered"}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
          </div>
        </TabsContent>

        <TabsContent value="list">
          <div className="mt-4 space-y-2">
            {filteredAgents.map((agent) => (
              <div
                key={agent.name}
                className="glass-card p-3 flex items-center gap-4 hover:border-primary/30 transition-all"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{agent.name}</span>
                    <Badge variant="outline" className="text-[10px]">
                      {agent.role}
                    </Badge>
                    <StatusBadge status={agent.status} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Agent Types Overview */}
      <div>
        <SectionHeader
          title="Agent Types"
          description="9 specialized trading agents"
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mt-4">
          {AGENT_TYPES.map((type) => (
            <div
              key={type.name}
              className="glass-card p-3 text-center hover:border-primary/30 transition-all cursor-pointer"
            >
              <span className="text-2xl">{type.icon}</span>
              <p className="text-sm font-medium text-foreground mt-1">{type.name}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">{type.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Run Agent Dialog */}
      <Dialog open={runDialogOpen} onOpenChange={setRunDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Run Agent Pipeline</DialogTitle>
            <DialogDescription>
              Execute the full AI agent pipeline for a symbol. The system will
              run research, strategy, risk, and execution agents.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">
                Symbol *
              </label>
              <Input
                placeholder="e.g., AAPL, BTC-USD, EURUSD"
                value={taskSymbol}
                onChange={(e) => setTaskSymbol(e.target.value.toUpperCase())}
                className="font-mono"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">
                Query (Optional)
              </label>
              <Textarea
                placeholder="Describe what you want the agents to analyze..."
                value={taskQuery}
                onChange={(e) => setTaskQuery(e.target.value)}
                rows={3}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">
                Timeframe
              </label>
              <Select value={taskTimeframe} onValueChange={setTaskTimeframe}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1m">1 Minute</SelectItem>
                  <SelectItem value="5m">5 Minutes</SelectItem>
                  <SelectItem value="15m">15 Minutes</SelectItem>
                  <SelectItem value="1h">1 Hour</SelectItem>
                  <SelectItem value="4h">4 Hours</SelectItem>
                  <SelectItem value="1d">1 Day</SelectItem>
                  <SelectItem value="1w">1 Week</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Run Result Display */}
            {runResult && (
              <div className="p-3 rounded-lg bg-secondary/20 border border-border/30 space-y-2">
                <div className="flex items-center gap-2">
                  {runResult.status === "completed" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-amber" />
                  )}
                  <span className="text-sm font-medium text-foreground">
                    Pipeline {runResult.status}
                  </span>
                </div>
                {runResult.decision_action && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">Decision: </span>
                    <span className="text-foreground font-medium">
                      {runResult.decision_action}
                    </span>
                  </div>
                )}
                {runResult.risk_verdict && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">Risk: </span>
                    <span className="text-foreground">{runResult.risk_verdict}</span>
                  </div>
                )}
                {runResult.agent_trace && runResult.agent_trace.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-muted-foreground font-medium">Agent Trace:</p>
                    {runResult.agent_trace.map((trace, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 text-xs p-1.5 rounded bg-secondary/20"
                      >
                        <Zap className="w-3 h-3 text-cyan" />
                        <span className="text-foreground font-medium">{trace.agent}</span>
                        <span className="text-muted-foreground truncate flex-1">
                          {trace.content.slice(0, 60)}
                        </span>
                        <span
                          className={
                            trace.confidence > 0.7 ? "text-emerald" : "text-amber"
                          }
                        >
                          {(trace.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRunDialogOpen(false)} className="cursor-pointer">
              Close
            </Button>
            <Button
              variant="cyan"
              onClick={handleRunAgent}
              disabled={!taskSymbol || isRunning}
              className="cursor-pointer"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Pipeline
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
