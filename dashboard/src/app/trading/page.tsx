"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowLeftRight } from "lucide-react";

export default function TradingPage() {
  const [positions, setPositions] = useState<any>(null);

  useEffect(() => {
    fetch("/api/trading/positions").then(r => r.json()).then(setPositions).catch(() => setPositions(null));
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <ArrowLeftRight className="w-5 h-5 text-cyan-400" />
        Trading
      </h1>
      <ChartCard title="Positions" subtitle="Live from /api/trading/positions">
        <ScrollArea className="max-h-96">
          <div className="space-y-2">
            {positions?.positions?.map((p: any) => (
              <div key={p.ticker} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-sm font-mono text-white/80">{p.ticker}</span>
                <span className="text-xs text-white/50 ml-2">Qty: {p.amount}</span>
                <Badge variant={p.pnl >= 0 ? "success" : "danger"} className="ml-2 text-[10px]">
                  PnL: {p.pnl}
                </Badge>
              </div>
            ))}
            {(!positions?.positions || positions.positions.length === 0) && <p className="text-white/40 text-sm p-4">No positions or API unavailable</p>}
          </div>
        </ScrollArea>
      </ChartCard>
    </div>
  );
}