"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Boxes, Plus, Play } from "lucide-react";
import { colonyApi, type Colony, type ColonyDetail } from "@/lib/api-client";

export default function ColonyPage() {
  const [colonies, setColonies] = useState<Colony[]>([]);
  const [detail, setDetail] = useState<ColonyDetail | null>(null);
  const [name, setName] = useState("");
  const [task, setTask] = useState("");
  const [taskOut, setTaskOut] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      setColonies(await colonyApi.list());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); }, []);

  async function create() {
    if (!name) return;
    try {
      await colonyApi.create({ name });
      setName("");
      refresh();
    } catch { /* ignore */ }
  }

  async function open(id: string) {
    try { setDetail(await colonyApi.getDetail(id)); } catch { /* ignore */ }
  }

  async function runTask(id: string) {
    if (!task) return;
    try {
      const r = await colonyApi.runTask(id, task);
      setTaskOut(r.result);
    } catch (e: any) { setTaskOut(e?.message || "error"); }
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <Boxes className="w-5 h-5 text-purple-400" /> Agent Colonies
      </h1>

      <ChartCard title="Create Colony" subtitle="POST /api/colony/create">
        <div className="flex gap-2 p-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="colony name" className="w-48" />
          <Button onClick={create} className="bg-purple-600 hover:bg-purple-500"><Plus className="w-4 h-4 mr-1" />CREATE</Button>
        </div>
      </ChartCard>

      <ChartCard title="Colonies" subtitle="From /api/colony/list">
        <DataTable<Colony>
          data={colonies}
          emptyMessage={loading ? "Loading…" : "No colonies"}
          onRowClick={(c) => open(c.id)}
          columns={[
            { key: "name", header: "Name", render: (r) => <span className="text-purple-400">{r.name}</span> },
            { key: "status", header: "Status", render: (r) => <Badge variant={r.status === "active" ? "success" : "warning"} className="text-[10px]">{r.status}</Badge> },
            { key: "health", header: "Health", render: (r) => <span className="font-mono">{r.health}%</span> },
            { key: "agents", header: "Agents", render: (r) => <span className="font-mono">{r.agents}/{r.capacity}</span> },
            { key: "schedule", header: "Schedule", render: (r) => <span className="text-white/50 text-xs">{r.schedule}</span> },
          ]}
        />
      </ChartCard>

      {detail && (
        <ChartCard title={`${detail.name} — Detail`} subtitle="Member agents">
          <DataTable
            data={detail.memberAgents || []}
            emptyMessage="No member agents"
            columns={[
              { key: "name", header: "Agent", render: (r: any) => <span className="text-cyan-400">{r.name}</span> },
              { key: "role", header: "Role", render: (r: any) => <span className="text-white/60 text-xs">{r.role}</span> },
              { key: "status", header: "Status", render: (r: any) => <Badge variant={r.status === "active" ? "success" : "default"} className="text-[10px]">{r.status}</Badge> },
            ]}
          />
          <div className="flex gap-2 mt-3">
            <Input value={task} onChange={(e) => setTask(e.target.value)} placeholder="task for colony" className="flex-1" />
            <Button onClick={() => runTask(detail.id)} className="bg-purple-600 hover:bg-purple-500"><Play className="w-4 h-4 mr-1" />RUN</Button>
          </div>
          {taskOut && <pre className="text-xs text-white/60 font-mono mt-2 p-2 rounded bg-black/30 whitespace-pre-wrap">{taskOut}</pre>}
        </ChartCard>
      )}
    </div>
  );
}
