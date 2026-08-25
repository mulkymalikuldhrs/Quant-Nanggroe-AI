"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { toolsApi } from "@/lib/api-client";
import type { Tool, ExecuteToolResponse } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  Wrench,
  Play,
  Terminal,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
} from "lucide-react";

// ── Fallback data ──────────────────────────────────────────────────

const FALLBACK_TOOLS: Tool[] = [
  { id: "web_search", name: "Web Search", description: "Search the web for real-time information", status: "active", category: "web", executions: 1245, lastUsed: "2m ago" },
  { id: "code_runner", name: "Code Runner", description: "Execute Python code in sandbox", status: "active", category: "dev", executions: 892, lastUsed: "5m ago" },
  { id: "docker_exec", name: "Docker Exec", description: "Run commands in Docker containers", status: "active", category: "infra", executions: 456, lastUsed: "12m ago" },
  { id: "file_system", name: "File System", description: "Read/write files in sandbox", status: "active", category: "system", executions: 2341, lastUsed: "1m ago" },
  { id: "api_client", name: "API Client", description: "Make HTTP requests to external APIs", status: "active", category: "web", executions: 678, lastUsed: "8m ago" },
  { id: "memory_query", name: "Memory Query", description: "Search vector memory store", status: "active", category: "cognitive", executions: 1567, lastUsed: "3m ago" },
  { id: "data_analysis", name: "Data Analysis", description: "Analyze data with pandas/numpy", status: "active", category: "dev", executions: 345, lastUsed: "15m ago" },
  { id: "notify", name: "Notify", description: "Send notifications via channels", status: "active", category: "comms", executions: 892, lastUsed: "4m ago" },
];

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [params, setParams] = useState("{}");
  const [execResult, setExecResult] = useState<ExecuteToolResponse | null>(null);
  const [executing, setExecuting] = useState(false);

  const loadTools = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await toolsApi.list();
      setTools(data);
    } catch {
      // Keep fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTools(); }, []);

  const handleExecute = async () => {
    if (!selectedTool) return;
    setExecuting(true);
    setExecResult(null);
    try {
      let parsed: Record<string, unknown> = {};
      try { parsed = JSON.parse(params); } catch { /* use empty */ }
      const result = await toolsApi.execute(selectedTool, parsed);
      setExecResult(result);
    } catch (err) {
      setExecResult({ success: false, result: err instanceof Error ? err.message : "Execution failed" });
    } finally {
      setExecuting(false);
    }
  };

  if (loading) return (
    <div className="space-y-4 animate-slide-up">
      <div className="h-8 w-48 rounded-lg bg-white/5 animate-pulse" />
      <LoadingSkeleton variant="page" />
    </div>
  );

  const categories = [...new Set(tools.map((t) => t.category))];
  const activeTools = tools.filter((t) => t.status === "active").length;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Wrench className="w-5 h-5 text-purple-400" />
          Tool Registry
        </h1>
        <p className="text-sm text-white/40 mt-0.5">{tools.length} tools &bull; {activeTools} active &bull; {categories.length} categories</p>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <p className="text-sm text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={loadTools}>
            <RefreshCw className="w-3 h-3 mr-1" /> Retry
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Tool Categories */}
        <div className="lg:col-span-2 space-y-4">
          {categories.map((cat) => (
            <ChartCard key={cat} title={cat.toUpperCase()} subtitle={`${tools.filter((t) => t.category === cat).length} tools`}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {tools.filter((t) => t.category === cat).map((tool) => (
                  <div key={tool.id} onClick={() => { setSelectedTool(tool.id); setExecResult(null); }}
                    className={cn(
                      "p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.02]",
                      selectedTool === tool.id
                        ? "bg-purple-500/10 border-purple-500/30"
                        : "bg-white/[0.02] border-white/[0.04] hover:bg-white/[0.06]",
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-white/80">{tool.name}</span>
                      <span className="text-[10px] font-mono text-white/30">{tool.executions} runs</span>
                    </div>
                    <p className="text-xs text-white/40">{tool.description}</p>
                    <div className="flex items-center justify-between mt-1.5">
                      <span className="text-[9px] text-white/20">Last: {tool.lastUsed}</span>
                      <Badge variant={tool.status === "active" ? "success" : "warning"} className="text-[9px]">{tool.status}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>
          ))}
        </div>

        {/* Execution Panel */}
        <ChartCard title="Execute Tool" subtitle={selectedTool ? tools.find((t) => t.id === selectedTool)?.name || "" : "Select a tool"}>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-white/40 mb-1 block">Selected Tool</label>
              <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] text-white/70 text-sm font-mono">
                {selectedTool || "None selected"}
              </div>
            </div>
            <div>
              <label className="text-xs text-white/40 mb-1 block">Parameters (JSON)</label>
              <textarea value={params} onChange={(e) => setParams(e.target.value)}
                className="w-full h-28 bg-white/5 border border-white/10 rounded-lg p-2 text-white/70 text-xs font-mono focus:outline-none focus:border-purple-500/50 resize-none"
              />
            </div>
            <Button variant="glow" className="w-full" onClick={handleExecute} disabled={!selectedTool || executing}>
              {executing ? (
                <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5 mr-1.5" />
              )}
              {executing ? "Executing..." : "Execute"}
            </Button>
            {execResult && (
              <div className={cn("p-3 rounded-lg border", execResult.success ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20")}>
                <div className="flex items-center gap-2 mb-1">
                  {execResult.success ? (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-red-400" />
                  )}
                  <span className={cn("text-xs font-medium", execResult.success ? "text-emerald-400" : "text-red-400")}>
                    {execResult.success ? "Success" : "Failed"}
                  </span>
                </div>
                <p className="text-xs text-white/50 font-mono break-all">{execResult.result}</p>
              </div>
            )}
            {!execResult && (
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 text-center">
                <Terminal className="w-6 h-6 text-white/10 mx-auto mb-1" />
                <p className="text-xs text-white/20 italic">Select a tool and execute to see results</p>
              </div>
            )}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
