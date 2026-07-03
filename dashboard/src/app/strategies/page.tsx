"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Zap } from "lucide-react";

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/backtest/strategies").then(r => r.json()).then(setStrategies).catch(() => null);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <Zap className="w-5 h-5 text-cyan-400" />
        Strategies
      </h1>
      <ChartCard title="Strategy Registry" subtitle="Live from /api/backtest/strategies">
        <ScrollArea className="max-h-96">
          <div className="space-y-2">
            {strategies.map((s: any, i: number) => (
              <div key={i} className="flex justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-xs text-white/80">{s.name}</span>
                <Badge variant={s.status === "active" ? "success" : "default"} className="text-[10px]">
                  {s.status.toUpperCase()}
                </Badge>
              </div>
            ))}
            {strategies.length === 0 && <p className="text-white/40 text-sm p-4">No strategies or API unavailable</p>}
          </div>
        </ScrollArea>
      </ChartCard>
    </div>
  );
}