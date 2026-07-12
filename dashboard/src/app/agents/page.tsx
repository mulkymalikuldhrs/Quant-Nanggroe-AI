"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, Skull, ShieldCheck } from "lucide-react";
import { agentsApi, type Agent, type Decision } from "@/lib/api-client";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [ksActive, setKsActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const [st, dec] = await Promise.all([
        agentsApi.getStatus(),
        agentsApi.getDecisions().catch(() => []),
      ]);
      setAgents(st.agents || []);
      setKsActive(st.kill_switch_active);
      setDecisions(Array.isArray(dec) ? dec : []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "failed to load agents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 8000);
    return () => clearInterval(t);
  }, []);

  async function toggleKill() {
    try {
      const res = ksActive
        ? await agentsApi.resetKillSwitch()
        : await agentsApi.activateKillSwitch("manual from dashboard");
      setKsActive(res.active);
    } catch (e: any) {
      setError(e?.message || "kill-switch error");
    }
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Bot className="w-5 h-5 text-cyan-400" /> Agents
        </h1>
        <Button
          onClick={toggleKill}
          className={ksActive ? "bg-red-600 hover:bg-red-500" : "bg-emerald-600 hover:bg-emerald-500"}
        >
          {ksActive ? <Skull className="w-4 h-4 mr-1" /> : <ShieldCheck className="w-4 h-4 mr-1" />}
          {ksActive ? "RESUME" : "HALT ALL"}
        </Button>
      </div>

      {error && <p className="text-xs text-red-400 font-mono">{error}</p>}

      <ChartCard title="Agent Status" subtitle="11-agent autonomous system">
        <ScrollArea className="max-h-96">
          <div className="space-y-2">
            {loading && <p className="text-sm text-white/40 p-3">Loading…</p>}
            {!loading && agents.map((a, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div>
                  <span className="text-sm text-white/80">{a.name}</span>
                  <span className="text-xs text-white/40 ml-2">{a.action || a.lastDecision || ""}</span>
                </div>
                <Badge variant={a.status === "active" ? "success" : a.status === "error" ? "danger" : "default"} className="text-[10px]">
                  {a.status}
                </Badge>
              </div>
            ))}
            {!loading && agents.length === 0 && <p className="text-white/40 text-sm p-4">No agents or API unavailable</p>}
          </div>
        </ScrollArea>
      </ChartCard>

      <ChartCard title="Recent Decisions" subtitle="From /api/agents/decisions">
        <DataTable<Decision>
          data={decisions}
          emptyMessage="No decisions yet"
          columns={[
            { key: "time", header: "Time", render: (r) => <span className="font-mono text-xs">{String(r.time).slice(0, 19)}</span> },
            { key: "agent", header: "Agent", render: (r) => <span className="text-cyan-400">{r.agent}</span> },
            { key: "decision", header: "Decision" },
            { key: "impact", header: "Impact", render: (r) => <Badge variant={r.impact === "high" ? "danger" : "default"} className="text-[10px]">{r.impact}</Badge> },
          ]}
        />
      </ChartCard>
    </div>
  );
}
