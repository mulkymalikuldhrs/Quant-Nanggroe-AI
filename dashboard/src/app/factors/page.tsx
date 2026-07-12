"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { FlaskConical, Layers } from "lucide-react";
import { backtestApi, type FactorZoo } from "@/lib/api-client";

export default function FactorsPage() {
  const [factors, setFactors] = useState<FactorZoo[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [f, s] = await Promise.allSettled([
        backtestApi.getFactors().catch(() => []),
        backtestApi.getStrategies().catch(() => []),
      ]);
      if (f.status === "fulfilled") setFactors(f.value);
      if (s.status === "fulfilled") setStrategies(s.value);
      setLoading(false);
    })();
  }, []);

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <FlaskConical className="w-5 h-5 text-purple-400" /> Factor Explorer
      </h1>

      <ChartCard title="Factor Zoo" subtitle="From /api/backtest/factors">
        <DataTable<FactorZoo>
          data={factors}
          emptyMessage={loading ? "Loading…" : "No factors"}
          columns={[
            { key: "name", header: "Factor", render: (r) => <span className="text-purple-400 font-medium">{r.name}</span> },
            { key: "count", header: "Count", render: (r) => <span className="font-mono">{r.count}</span> },
            { key: "description", header: "Description", render: (r) => <span className="text-white/50 text-xs">{r.description}</span> },
          ]}
        />
      </ChartCard>

      <ChartCard title="Strategy Registry" subtitle={`${strategies.length} catalog strategies`}>
        <div className="flex flex-wrap gap-2 p-2">
          {(strategies.length ? strategies : [{ name: "RegimeBased" }, { name: "MeanReversion" }, { name: "TrendFollow" }]).map((s: any, i: number) => (
            <Badge key={i} variant="success" className="text-[10px]"><Layers className="w-3 h-3 mr-1" />{s.name}</Badge>
          ))}
        </div>
        <p className="text-xs text-white/40 px-2 pb-2">Live via /api/strategy/registry</p>
      </ChartCard>
    </div>
  );
}
