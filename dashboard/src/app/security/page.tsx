"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ShieldAlert, AlertTriangle, Lock } from "lucide-react";
import { ecosystemApi } from "@/lib/api-client";

interface SecEvent { id?: string; type: string; severity: string; source: string; timestamp: string; detail?: string; }

export default function SecurityPage() {
  const [events, setEvents] = useState<SecEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ecosystemApi.securityEvents()
      .then((r: any) => setEvents(Array.isArray(r) ? r : r.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <ShieldAlert className="w-5 h-5 text-red-400" /> Security
      </h1>

      <div className="grid grid-cols-3 gap-3">
        <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20">
          <Lock className="w-4 h-4 text-red-400 mb-1" />
          <p className="text-xs text-white/50 uppercase">Threat Level</p>
          <p className="text-xl font-bold text-red-400">MONITORED</p>
        </div>
        <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
          <AlertTriangle className="w-4 h-4 text-amber-400 mb-1" />
          <p className="text-xs text-white/50 uppercase">Events</p>
          <p className="text-xl font-bold text-white">{events.length}</p>
        </div>
        <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
          <ShieldAlert className="w-4 h-4 text-emerald-400 mb-1" />
          <p className="text-xs text-white/50 uppercase">Status</p>
          <p className="text-xl font-bold text-emerald-400">ARMED</p>
        </div>
      </div>

      <ChartCard title="Security Events" subtitle="From /api/security/events">
        <ScrollArea className="max-h-96">
          <DataTable<SecEvent>
            data={events}
            emptyMessage={loading ? "Loading…" : "No security events"}
            columns={[
              { key: "timestamp", header: "Time", render: (r) => <span className="font-mono text-xs">{String(r.timestamp).slice(0, 19)}</span> },
              { key: "type", header: "Type", render: (r) => <span className="text-red-400">{r.type}</span> },
              { key: "severity", header: "Severity", render: (r) => <Badge variant={r.severity === "high" ? "danger" : r.severity === "medium" ? "warning" : "default"} className="text-[10px]">{r.severity}</Badge> },
              { key: "source", header: "Source", render: (r) => <span className="text-white/50 text-xs">{r.source}</span> },
            ]}
          />
        </ScrollArea>
      </ChartCard>
    </div>
  );
}
