"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FlaskConical, Play, Cog, Layers } from "lucide-react";
import { backtestApi, type Strategy, type FactorZoo } from "@/lib/api-client";

export default function BacktestPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [factors, setFactors] = useState<FactorZoo[]>([]);
  const [engines, setEngines] = useState<string[]>([]);
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [strategy, setStrategy] = useState("");
  const [running, setRunning] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [s, f, e] = await Promise.allSettled([
        backtestApi.getStrategies().catch(() => []),
        backtestApi.getFactors().catch(() => []),
        backtestApi.getEngines().catch(() => []),
      ]);
      if (s.status === "fulfilled") setStrategies(s.value);
      if (f.status === "fulfilled") setFactors(f.value);
      if (e.status === "fulfilled") setEngines(e.value);
      setLoading(false);
    })();
  }, []);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const res = await backtestApi.run({ strategy: strategy || undefined, symbol, engine: engines[0] });
      setRunId(res.id);
    } catch (e: any) {
      setError(e?.message || "run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <FlaskConical className="w-5 h-5 text-purple-400" /> Backtest
      </h1>

      {error && <p className="text-xs text-red-400 font-mono">{error}</p>}

      <ChartCard title="Run Backtest" subtitle="POST /api/backtest/run">
        <div className="flex flex-wrap gap-2 items-end p-2">
          <label className="text-xs text-white/60 flex flex-col gap-1">
            Symbol
            <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="w-36" />
          </label>
          <label className="text-xs text-white/60 flex flex-col gap-1">
            Strategy
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1 text-white text-sm">
              <option value="">auto</option>
              {strategies.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <Button onClick={run} disabled={running} className="bg-purple-600 hover:bg-purple-500">
            <Play className="w-4 h-4 mr-1" /> {running ? "Running…" : "RUN"}
          </Button>
          {runId && <Badge variant="success" className="text-[10px]">job: {runId.slice(0, 8)}</Badge>}
        </div>
      </ChartCard>

      <div className="grid md:grid-cols-2 gap-4">
        <ChartCard title="Strategy Registry" subtitle={`${strategies.length} strategies`}>
          <DataTable<Strategy>
            data={strategies}
            emptyMessage={loading ? "Loading…" : "No strategies"}
            columns={[
              { key: "name", header: "Name", render: (r) => <span className="text-cyan-400">{r.name}</span> },
              { key: "type", header: "Type" },
              { key: "sharpe", header: "Sharpe", render: (r) => <span className="font-mono">{r.sharpe}</span> },
              { key: "status", header: "Status", render: (r) => <Badge variant={r.status === "active" ? "success" : "default"} className="text-[10px]">{r.status}</Badge> },
            ]}
          />
        </ChartCard>

        <ChartCard title="Factor Zoo" subtitle="From /api/backtest/factors">
          <DataTable<FactorZoo>
            data={factors}
            emptyMessage={loading ? "Loading…" : "No factors"}
            columns={[
              { key: "name", header: "Factor", render: (r) => <span className="text-purple-400">{r.name}</span> },
              { key: "count", header: "Count", render: (r) => <span className="font-mono">{r.count}</span> },
              { key: "description", header: "Desc", render: (r) => <span className="text-white/50 text-xs">{r.description}</span> },
            ]}
          />
        </ChartCard>
      </div>

      <ChartCard title="Engines" subtitle="Available backtest engines">
        <div className="flex flex-wrap gap-2 p-2">
          {(engines.length ? engines : ["vectorized", "event_driven", "multi_agent"]).map((e) => (
            <Badge key={e} variant="default" className="text-[10px]"><Cog className="w-3 h-3 mr-1" />{e}</Badge>
          ))}
        </div>
      </ChartCard>
    </div>
  );
}
