"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Brain, Search, Plus } from "lucide-react";
import { memoryApi, type MemoryEntry, type MemoryEntryType } from "@/lib/api-client";

export default function MemoryPage() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [q, setQ] = useState("");
  const [key, setKey] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  async function search() {
    setLoading(true);
    try {
      const r = q
        ? await memoryApi.search(q)
        : await memoryApi.search("*");
      setEntries(r.entries || []);
    } catch {
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { search(); }, []);

  async function store() {
    if (!key || !content) return;
    try {
      await memoryApi.store({ key, type: "knowledge", content });
      setMsg("✓ stored");
      setKey(""); setContent("");
      search();
    } catch (e: any) { setMsg(`✗ ${e?.message || "store failed"}`); }
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <Brain className="w-5 h-5 text-purple-400" /> Memory
      </h1>

      <ChartCard title="Store Entry" subtitle="POST /api/memory/store">
        <div className="flex flex-wrap gap-2 p-2">
          <Input value={key} onChange={(e) => setKey(e.target.value)} placeholder="key" className="w-32" />
          <Input value={content} onChange={(e) => setContent(e.target.value)} placeholder="content" className="flex-1" />
          <Button onClick={store} className="bg-purple-600 hover:bg-purple-500"><Plus className="w-4 h-4 mr-1" />STORE</Button>
        </div>
        {msg && <p className="text-xs font-mono px-2 pb-2 text-white/60">{msg}</p>}
      </ChartCard>

      <ChartCard title="Search" subtitle="From /api/memory/search">
        <div className="flex gap-2 p-2">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="query" className="flex-1" />
          <Button onClick={search}><Search className="w-4 h-4 mr-1" />SEARCH</Button>
        </div>
        <DataTable<MemoryEntry>
          data={entries}
          emptyMessage={loading ? "Loading…" : "No entries"}
          columns={[
            { key: "type", header: "Type", render: (r) => <Badge variant="default" className="text-[10px]">{(r.type as MemoryEntryType) || "—"}</Badge> },
            { key: "key", header: "Key", render: (r) => <span className="text-purple-400 font-mono text-xs">{r.key}</span> },
            { key: "content", header: "Content", render: (r) => <span className="text-white/60 text-xs">{String(r.content).slice(0, 80)}</span> },
            { key: "relevance", header: "Rel", render: (r) => <span className="font-mono text-xs">{r.relevance}</span> },
          ]}
        />
      </ChartCard>
    </div>
  );
}
