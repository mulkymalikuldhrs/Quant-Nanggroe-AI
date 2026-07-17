"use client";

import React, { useState, useEffect } from "react";
import { Activity, ShieldOff, ShieldCheck, RefreshCw, AlertCircle } from "lucide-react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { cn } from "@/lib/utils";

interface QueueItem {
  id: string;
  title: string;
  sev: string;
  ref: string;
}

interface QnaStatus {
  kill_switch: { active: boolean; file_path: string };
  guard_config: {
    allowed_symbols: string[];
    blocked_symbols: string[];
    cooldown: number;
    max_position_pct: number;
    max_notional: number;
  };
  graph_queue: QueueItem[];
  last_ledger: string;
}

// ponytail: severity → existing badge variant; one map, no switch soup
const sevVariant: Record<string, "success" | "danger" | "warning" | "info" | "default"> = {
  done: "success",
  high: "danger",
  med: "warning",
  medium: "warning",
  low: "info",
};

export default function QnaStatusPage() {
  const [data, setData] = useState<QnaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ponytail: apiRequest points at localhost:8000 (unreachable from browser);
  // the Next dev server proxies /api/* → backend, so fetch same-origin.
  // loading defaults to true; only the footer call-sites toggle it on.
  const load = async () => {
    setError(null);
    try {
      const res = await fetch("/api/qna-status", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch {
      setError("Failed to load QNA status. Backend /api/qna-status unavailable.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading && !data) {
    return (
      <div className="space-y-4 animate-slide-up">
        <div className="h-8 w-64 rounded-lg bg-white/5 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-64 rounded-xl bg-white/5 animate-pulse" />
          ))}
        </div>
        <LoadingSkeleton variant="page" />
      </div>
    );
  }

  const gc = data?.guard_config;
  const ksActive = data?.kill_switch.active ?? false;
  // guard rows: allowed=green limit, blocked=red limit
  const guardRows = [
    ...(gc?.allowed_symbols ?? []).map((s) => ({
      symbol: s,
      status: "allowed" as const,
      limit: `${gc?.max_position_pct ?? 0}% / ${gc?.max_notional ?? 0}`,
    })),
    ...(gc?.blocked_symbols ?? []).map((s) => ({
      symbol: s,
      status: "blocked" as const,
      limit: "—",
    })),
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            QNA Status
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            Kill-switch • Guard config • Graph queue • Ledger
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="h-7 px-2 text-white/30 hover:text-white/50" onClick={() => { setLoading(true); load(); }} disabled={loading}>
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
          </Button>
          <div className={cn("flex items-center gap-2 px-3 py-2 rounded-lg border", ksActive ? "bg-red-500/5 border-red-500/20" : "bg-emerald-500/5 border-emerald-500/20")}>
            {ksActive ? <ShieldOff className="w-4 h-4 text-red-400" /> : <ShieldCheck className="w-4 h-4 text-emerald-400" />}
            <span className={cn("text-sm font-medium", ksActive ? "text-red-400" : "text-emerald-400")}>Kill Switch</span>
            <Badge variant={ksActive ? "danger" : "success"} pulse={ksActive}>{ksActive ? "ACTIVE" : "INACTIVE"}</Badge>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => { setLoading(true); load(); }}>Retry</Button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Guard Config */}
        <ChartCard title="Guard Config" subtitle="Allowed / blocked symbols & limits" glow="emerald">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-white/40 text-[11px] uppercase tracking-wider">
                  <th className="text-left py-2 pr-3 font-medium">Symbol</th>
                  <th className="text-left py-2 pr-3 font-medium">Status</th>
                  <th className="text-left py-2 font-medium">Limit</th>
                </tr>
              </thead>
              <tbody>
                {guardRows.length === 0 && (
                  <tr><td colSpan={3} className="py-3 text-white/30 text-xs">No symbols configured.</td></tr>
                )}
                {guardRows.map((r) => (
                  <tr key={r.symbol} className="border-t border-white/[0.04]">
                    <td className="py-2 pr-3 font-mono text-white/80">{r.symbol}</td>
                    <td className="py-2 pr-3">
                      <Badge variant={r.status === "allowed" ? "success" : "danger"}>{r.status.toUpperCase()}</Badge>
                    </td>
                    <td className="py-2 font-mono text-white/50 text-xs">{r.limit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 pt-3 border-t border-white/[0.04] grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-white/[0.02] border border-white/[0.04] py-2">
              <p className="text-[10px] text-white/40">Cooldown</p>
              <p className="text-sm font-mono text-white/80">{gc?.cooldown ?? "—"}s</p>
            </div>
            <div className="rounded-lg bg-white/[0.02] border border-white/[0.04] py-2">
              <p className="text-[10px] text-white/40">Max Pos %</p>
              <p className="text-sm font-mono text-white/80">{gc?.max_position_pct ?? "—"}%</p>
            </div>
            <div className="rounded-lg bg-white/[0.02] border border-white/[0.04] py-2">
              <p className="text-[10px] text-white/40">Max Notional</p>
              <p className="text-sm font-mono text-white/80">{gc?.max_notional ?? "—"}</p>
            </div>
          </div>
        </ChartCard>

        {/* Graph Queue */}
        <ChartCard title="Graph Queue" subtitle="Backlog items by severity" glow="amber">
          <div className="space-y-2">
            {!data?.graph_queue?.length && <p className="text-xs text-white/30 py-2">Queue empty.</p>}
            {data?.graph_queue?.map((q) => {
              const v = sevVariant[q.sev.toLowerCase()] ?? "default";
              return (
                <div key={q.id} className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <Badge variant={v} className="mt-0.5 flex-shrink-0">{q.sev.toUpperCase()}</Badge>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-white/80 truncate">{q.title}</p>
                    <p className="text-[10px] text-white/30 font-mono">{q.id} · {q.ref}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>

        {/* Last Ledger */}
        <ChartCard title="Last Ledger" subtitle="Latest decision log entry" glow="purple" className="lg:col-span-2">
          <div className="max-h-80 overflow-auto rounded-lg bg-black/30 border border-white/[0.04] p-3">
            <pre className="text-xs text-white/60 whitespace-pre-wrap font-mono leading-relaxed">
              {data?.last_ledger || "No ledger entry."}
            </pre>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
