"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Target as StratIcon } from "lucide-react";
import { backtestApi, type Strategy } from "@/lib/api-client";

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    backtestApi.getStrategies()
      .then(setStrategies)
      .catch(() => setStrategies([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <StratIcon className="w-5 h-5 text-cyan-400" /> Strategies
      </h1>

      <ChartCard title="Strategy Catalog" subtitle="From /api/backtest/strategies">
        <DataTable<Strategy>
          data={strategies}
          emptyMessage={loading ? "Loading…" : "No strategies available"}
          columns={[
            { key: "name", header: "Name", render: (r) => <span className="text-cyan-400 font-medium">{r.name}</span> },
            { key: "type", header: "Type", render: (r) => <Badge variant="default" className="text-[10px]">{r.type}</Badge> },
            { key: "performance", header: "Perf%", render: (r) => <span className="font-mono">{r.performance}</span> },
            { key: "sharpe", header: "Sharpe", render: (r) => <span className="font-mono">{r.sharpe}</span> },
            { key: "status", header: "Status", render: (r) => <Badge variant={r.status === "active" ? "success" : "default"} className="text-[10px]">{r.status}</Badge> },
          ]}
        />
      </ChartCard>
    </div>
  );
}
