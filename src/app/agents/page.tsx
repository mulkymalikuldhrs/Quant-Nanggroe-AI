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
import { MetricCard, StatusBadge, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

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
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <Bot className="w-8 h-8 text-purple animate-float" />
            Agent Swarm
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Deploy & Monitor Autonomous Entities
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" onClick={() => fetchAgents()} className="cursor-pointer scale-tap bg-background/50 backdrop-blur-sm border-border/50 hover:border-purple/50 hover:bg-purple/10 hover:text-purple transition-colors">
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button variant="purple" onClick={() => setRunDialogOpen(true)} className="gap-2 cursor-pointer scale-tap">
            <Play className="w-4 h-4" />
            Run Agent Pipeline
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-up stagger-children" style={{ animationDelay: '100ms' }}>
        <MetricCard
          title="Total Agents"
          value={agents.length}
          subtitle="Registered in system"
          icon={<Bot className="w-5 h-5" />}
          color="purple"
          loading={loadingAgents}
        />
        <MetricCard
          title="Active Processing"
          value={activeCount}
          subtitle="Executing logic right now"
          icon={<Activity className="w-5 h-5" />}
          color="cyan"
          loading={loadingAgents}
        />
        <MetricCard
          title="Idle"
          value={idleCount}
          subtitle="Awaiting tasks"
          icon={<Clock className="w-5 h-5" />}
          color="amber"
          loading={loadingAgents}
        />
        <MetricCard
          title="Errors"
          value={errorCount}
          subtitle="Require attention"
          icon={<AlertTriangle className="w-5 h-5" />}
          color="rose"
          loading={loadingAgents}
        />
      </div>

      {/* Error State */}
      {errorAgents && (
        <div className="p-4 rounded-xl border border-rose bg-rose/10 flex items-center gap-3 shadow-[0_0_20px_rgba(244,63,94,0.1)] animate-fade-in">
          <AlertTriangle className="w-5 h-5 text-rose shrink-0" />
          <p className="text-sm font-medium text-rose">{errorAgents}</p>
        </div>
      )}

      {/* Filters & Content */}
      <div className="animate-slide-up" style={{ animationDelay: '200ms' }}>
        <Tabs defaultValue="grid" className="w-full">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
            <TabsList>
              <TabsTrigger value="grid">Grid View</TabsTrigger>
              <TabsTrigger value="list">List View</TabsTrigger>
            </TabsList>

            <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search agents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 bg-background/50"
                />
              </div>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-[140px] bg-background/50">
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
          </div>

          <TabsContent value="grid">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 mt-2 stagger-children">
              {loadingAgents
                ? Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="glass-card p-5 space-y-4">
                      <div className="flex items-center gap-3 mb-2">
                        <Skeleton className="w-10 h-10 rounded-full" />
                        <div className="space-y-2">
                          <Skeleton className="h-4 w-24" />
                          <Skeleton className="h-3 w-16" />
                        </div>
                      </div>
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-4/5" />
                    </div>
                  ))
                : filteredAgents.map((agent) => {
                    const typeInfo = AGENT_TYPES.find((t) =>
                      agent.name.toLowerCase().includes(t.name.toLowerCase())
                    ) || AGENT_TYPES[0];
                    return (
                      <div
                        key={agent.name}
                        className="glass-card p-5 hover-lift hover:shadow-[0_0_20px_rgba(139,92,246,0.1)] group relative overflow-hidden"
                      >
                        <div className="absolute top-0 right-0 w-20 h-20 bg-purple/5 rounded-bl-full translate-x-10 -translate-y-10 group-hover:bg-purple/10 transition-colors" />
                        
                        <div className="flex items-start justify-between mb-4 relative z-10">
                          <div className="flex items-center gap-3">
                            <div className={cn("w-10 h-10 rounded-full flex items-center justify-center text-xl bg-secondary/30 border border-border/50",
                              agent.status === 'active' ? "border-emerald/40 bg-emerald/10 shadow-[0_0_15px_rgba(16,185,129,0.2)]" :
                              agent.status === 'error' ? "border-rose/40 bg-rose/10 shadow-[0_0_15px_rgba(244,63,94,0.2)]" : ""
                            )}>
                              {typeInfo.icon}
                            </div>
                            <div>
                              <h3 className="text-base font-bold text-foreground tracking-tight">
                                {agent.name}
                              </h3>
                              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{agent.role}</p>
                            </div>
                          </div>
                          <StatusBadge status={agent.status} />
                        </div>
                        <p className="text-xs text-muted-foreground mb-4 leading-relaxed relative z-10">{typeInfo.desc}</p>
                        <div className="flex items-center justify-between pt-3 border-t border-border/30 relative z-10">
                          <Badge
                            variant={typeInfo.color as "cyan" | "purple" | "emerald" | "amber" | "rose"}
                            className="text-[10px] font-bold"
                          >
                            {agent.registered ? "Verified" : "Unregistered"}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground font-mono">v4.0.0</span>
                        </div>
                      </div>
                    );
                  })}
            </div>
          </TabsContent>

          <TabsContent value="list">
            <div className="mt-2 space-y-3 stagger-children">
              {filteredAgents.map((agent) => {
                const typeInfo = AGENT_TYPES.find((t) =>
                  agent.name.toLowerCase().includes(t.name.toLowerCase())
                ) || AGENT_TYPES[0];
                return (
                  <div
                    key={agent.name}
                    className="glass-card p-4 flex items-center gap-4 hover-lift group"
                  >
                    <div className={cn("w-10 h-10 rounded-full flex items-center justify-center text-xl bg-secondary/30 border border-border/50 shrink-0",
                      agent.status === 'active' ? "border-emerald/40 bg-emerald/10 shadow-[0_0_15px_rgba(16,185,129,0.2)]" :
                      agent.status === 'error' ? "border-rose/40 bg-rose/10 shadow-[0_0_15px_rgba(244,63,94,0.2)]" : ""
                    )}>
                      {typeInfo.icon}
                    </div>
                    <div className="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-4 gap-4 items-center">
                      <div className="sm:col-span-1">
                        <span className="text-sm font-bold text-foreground block">{agent.name}</span>
                        <span className="text-xs text-muted-foreground">{agent.role}</span>
                      </div>
                      <div className="sm:col-span-2 hidden sm:block">
                        <p className="text-xs text-muted-foreground truncate">{typeInfo.desc}</p>
                      </div>
                      <div className="sm:col-span-1 flex items-center justify-end gap-3">
                        <StatusBadge status={agent.status} />
                        <Badge variant="outline" className="text-[10px] hidden lg:inline-flex">
                          {typeInfo.color}
                        </Badge>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Agent Types Overview */}
      <div className="animate-slide-up" style={{ animationDelay: '300ms' }}>
        <SectionHeader
          title="Agent Taxonomy"
          description="Specialized intelligence nodes in the swarm"
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mt-5 stagger-children">
          {AGENT_TYPES.map((type) => (
            <div
              key={type.name}
              className="glass-card p-4 text-center hover-lift hover:border-purple/30 group transition-all cursor-pointer"
            >
              <div className="w-12 h-12 mx-auto rounded-full bg-secondary/30 border border-border/50 flex items-center justify-center text-2xl mb-3 group-hover:scale-110 transition-transform shadow-[inset_0_0_10px_rgba(255,255,255,0.05)]">
                {type.icon}
              </div>
              <p className="text-sm font-bold text-foreground mt-1">{type.name}</p>
              <p className="text-[10px] font-medium text-muted-foreground mt-1 uppercase tracking-widest">{type.color} tier</p>
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
              <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                Symbol *
              </label>
              <Input
                placeholder="e.g., AAPL, BTC-USD, EURUSD"
                value={taskSymbol}
                onChange={(e) => setTaskSymbol(e.target.value.toUpperCase())}
                className="font-mono text-base"
              />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                Context / Query (Optional)
              </label>
              <Textarea
                placeholder="Describe what you want the agents to analyze..."
                value={taskQuery}
                onChange={(e) => setTaskQuery(e.target.value)}
                rows={3}
                className="bg-secondary/20 border-border/50 focus:border-cyan/50 focus-glow transition-all"
              />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                Timeframe
              </label>
              <Select value={taskTimeframe} onValueChange={setTaskTimeframe}>
                <SelectTrigger className="bg-secondary/20 border-border/50">
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
              <div className="p-4 rounded-xl bg-secondary/30 border border-border/50 space-y-3 animate-fade-in mt-2 shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]">
                <div className="flex items-center gap-2 border-b border-border/30 pb-2">
                  {runResult.status === "completed" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber drop-shadow-[0_0_5px_rgba(245,158,11,0.5)]" />
                  )}
                  <span className="text-sm font-bold text-foreground tracking-wide">
                    Pipeline {runResult.status.toUpperCase()}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  {runResult.decision_action && (
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block mb-1">Decision</span>
                      <span className={cn("text-sm font-bold px-2 py-1 rounded bg-secondary/50", 
                        runResult.decision_action === 'BUY' ? 'text-emerald' : 
                        runResult.decision_action === 'SELL' ? 'text-rose' : 'text-amber'
                      )}>
                        {runResult.decision_action}
                      </span>
                    </div>
                  )}
                  {runResult.risk_verdict && (
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block mb-1">Risk</span>
                      <span className={cn("text-sm font-bold", 
                        runResult.risk_verdict === 'APPROVED' ? 'text-emerald' : 
                        runResult.risk_verdict === 'REJECTED' ? 'text-rose' : 'text-amber'
                      )}>
                        {runResult.risk_verdict}
                      </span>
                    </div>
                  )}
                </div>

                {runResult.agent_trace && runResult.agent_trace.length > 0 && (
                  <div className="pt-2 border-t border-border/30">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Agent Trace</p>
                    <div className="space-y-1.5">
                      {runResult.agent_trace.map((trace, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-3 text-xs p-2 rounded-lg bg-background/50 border border-border/30 hover:border-cyan/30 transition-colors"
                        >
                          <Zap className="w-3.5 h-3.5 text-cyan shrink-0" />
                          <span className="text-foreground font-bold shrink-0">{trace.agent}</span>
                          <span className="text-muted-foreground truncate flex-1 font-mono text-[10px]">
                            {trace.content}
                          </span>
                          <span
                            className={cn("font-bold tabular-nums shrink-0",
                              trace.confidence > 0.7 ? "text-emerald" : "text-amber"
                            )}
                          >
                            {(trace.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
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
              variant="purple"
              onClick={handleRunAgent}
              disabled={!taskSymbol || isRunning}
              className="cursor-pointer font-bold"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Execute Pipeline
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
