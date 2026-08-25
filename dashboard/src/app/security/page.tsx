"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { securityApi } from "@/lib/api-client";
import type { SecurityEvent, SecurityStatus } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  Shield,
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  RefreshCw,
} from "lucide-react";

// ── Fallback data ──────────────────────────────────────────────────

const FALLBACK_EVENTS: SecurityEvent[] = [
  { id: "e1", type: "api_access", severity: "info", message: "API access from 192.168.1.1", timestamp: new Date().toISOString(), detail: "Authorized API request", agent: "trader" },
  { id: "e2", type: "login", severity: "info", message: "User authenticated", timestamp: new Date(Date.now() - 3600000).toISOString(), detail: "Password auth successful", agent: "system" },
  { id: "e3", type: "kill_switch", severity: "warning", message: "Kill switch triggered", timestamp: new Date(Date.now() - 7200000).toISOString(), detail: "Drawdown limit reached", agent: "risk" },
  { id: "e4", type: "unauthorized", severity: "critical", message: "Unauthorized access attempt", timestamp: new Date(Date.now() - 10800000).toISOString(), detail: "Blocked IP 10.0.0.99", agent: "security" },
  { id: "e5", type: "config_change", severity: "info", message: "Risk limits updated", timestamp: new Date(Date.now() - 14400000).toISOString(), detail: "Max drawdown changed to -5%", agent: "admin" },
];

function SecurityContent() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [evts, st] = await Promise.all([
        securityApi.getEvents(),
        securityApi.getStatus(),
      ]);
      setEvents(evts);
      setStatus(st);
    } catch {
      // Keep fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return (
    <div className="space-y-4 animate-slide-up">
      <div className="h-8 w-48 rounded-lg bg-white/5 animate-pulse" />
      <LoadingSkeleton variant="dashboard" />
      <LoadingSkeleton variant="page" />
    </div>
  );

  const severityStyles: Record<string, string> = {
    info: "border-cyan-500/20 bg-cyan-500/5",
    warning: "border-amber-500/20 bg-amber-500/5",
    critical: "border-red-500/20 bg-red-500/5",
  };
  const severityDots: Record<string, string> = {
    info: "bg-cyan-500", warning: "bg-amber-500", critical: "bg-red-500",
  };
  const severityIcons: Record<string, React.ReactNode> = {
    info: <CheckCircle className="w-3.5 h-3.5 text-cyan-400" />,
    warning: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
    critical: <AlertCircle className="w-3.5 h-3.5 text-red-400" />,
  };

  const infoCount = events.filter((e) => e.severity === "info").length;
  const warningCount = events.filter((e) => e.severity === "warning").length;
  const criticalCount = events.filter((e) => e.severity === "critical").length;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" />
          Security & Audit
        </h1>
        <p className="text-sm text-white/40 mt-0.5">
          {status?.activeRules || 0} active rules &bull; Sandbox: {status?.sandboxRunning ? "Running" : "Stopped"}
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3">
        <StatusCard title="Info Events" value={infoCount} variant="info" />
        <StatusCard title="Warnings" value={warningCount} variant={warningCount > 0 ? "warning" : "success"} />
        <StatusCard title="Critical" value={criticalCount} variant={criticalCount > 0 ? "danger" : "success"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Audit Log */}
        <ChartCard title="Audit Log" subtitle="Security event history" className="lg:col-span-2">
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {events.length === 0 ? (
              <div className="text-center py-8 text-white/30">
                <ShieldCheck className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No security events</p>
              </div>
            ) : (
              events.map((event) => (
                <div key={event.id} className={cn("p-3 rounded-lg border", severityStyles[event.severity] || "border-white/5")}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      {severityIcons[event.severity]}
                      <span className="text-white/70 text-xs font-medium">{event.type.replace(/_/g, " ").toUpperCase()}</span>
                    </div>
                    <span className="text-white/20 text-[10px]">{new Date(event.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-white/50 text-xs ml-5">{event.detail || event.message}</p>
                  <div className="text-white/20 text-[10px] ml-5 mt-1">Agent: {event.agent}</div>
                </div>
              ))
            )}
          </div>
        </ChartCard>

        {/* Sandbox & Permissions */}
        <div className="space-y-4">
          <ChartCard title="Sandbox Status" subtitle="Isolated execution environments">
            <div className="space-y-3">
              {[
                { name: "Docker Sandbox", status: "running", cpu: 34, memory: 52 },
                { name: "WASM Sandbox", status: "idle", cpu: 0, memory: 8 },
              ].map((sb) => (
                <div key={sb.name} className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-white/70 text-xs font-medium">{sb.name}</span>
                    <Badge variant={sb.status === "running" ? "success" : "info"} className="text-[10px]">{sb.status}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <span className="text-[10px] text-white/30">CPU: <span className="text-xs text-cyan-400">{sb.cpu}%</span></span>
                    <span className="text-[10px] text-white/30">Memory: <span className="text-xs text-purple-400">{sb.memory}%</span></span>
                  </div>
                </div>
              ))}
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 flex items-center justify-between">
                <span className="text-xs text-white/50">Permissions</span>
                <span className="text-xs font-mono text-white/70">{status?.permissions || 12}</span>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 flex items-center justify-between">
                <span className="text-xs text-white/50">Active Rules</span>
                <span className="text-xs font-mono text-white/70">{status?.activeRules || 4}</span>
              </div>
            </div>
          </ChartCard>

          <ChartCard title="Permission Rules" subtitle="Sandbox permissions">
            <div className="space-y-2">
              {[
                { rule: "shell_execution", scope: "executor", action: "grant" },
                { rule: "file_write_etc", scope: "all", action: "deny" },
                { rule: "docker_management", scope: "colony", action: "grant" },
                { rule: "network_access", scope: "browser", action: "grant" },
              ].map((p) => (
                <div key={p.rule} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                  <div>
                    <span className="text-white/50 text-xs font-mono">{p.rule}</span>
                    <span className="text-[9px] text-white/20 ml-2">({p.scope})</span>
                  </div>
                  {p.action === "grant" ? (
                    <Badge variant="success" className="text-[9px]">GRANT</Badge>
                  ) : (
                    <Badge variant="danger" className="text-[9px]">DENY</Badge>
                  )}
                </div>
              ))}
            </div>
          </ChartCard>
        </div>
      </div>
    </div>
  );
}

export default function SecurityPage() {
  return (
    <ErrorBoundary>
      <SecurityContent />
    </ErrorBoundary>
  );
}
