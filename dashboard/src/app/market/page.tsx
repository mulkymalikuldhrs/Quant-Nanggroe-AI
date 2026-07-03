"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { BarChart3, ArrowUpRight, ArrowDownRight } from "lucide-react";

export default function MarketPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("/api/market/signals").then(r => r.json()).then(setData).catch(() => setData(null));
  }, []);

  const symbols = data?.symbols || [];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-blue-400" />
        Market
      </h1>
      <ChartCard title="Market Signals" subtitle="Live from /api/market/signals">
        <div className="space-y-2">
          {symbols.map((s: any) => (
            <div key={s.symbol} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm font-mono text-white/80">{s.symbol}</span>
              <span className="text-xs text-white/50 ml-2">{s.price}</span>
              <Badge variant={s.change >= 0 ? "success" : "danger"} className="ml-2 text-[10px]">
                {s.change >= 0 ? "+" : ""}{s.change}%
              </Badge>
            </div>
          ))}
          {symbols.length === 0 && <p className="text-white/40 text-sm p-4">Connect to /api/market/signals</p>}
        </div>
      </ChartCard>
    </div>
  );
}