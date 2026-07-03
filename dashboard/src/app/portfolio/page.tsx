"use client";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { TrendingUp, DollarSign } from "lucide-react";

export default function PortfolioPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("/api/monitor/summary").then(r => r.json()).then(setData);
  }, []);

  const pnl = data?.pnl || {};
  const allocation = data?.health?.state?.allocation || [
    { name: "Crypto", value: 35 },
    { name: "Equities", value: 30 },
    { name: "Cash", value: 35 },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <ChartCard title="Total P&L" subtitle="Real-time from monitor">
          <p className="text-2xl font-mono font-bold text-emerald-400">{formatCurrency(pnl?.total_pnl || 0)}</p>
          <p className="text-xs text-white/40">24h: {formatCurrency(pnl?.last_24h || 0)}</p>
        </ChartCard>
        <ChartCard title="Total Cycles" subtitle="Engine runs">
          <p className="text-2xl font-mono font-bold">{pnl?.total_cycles || 0}</p>
        </ChartCard>
        <ChartCard title="Status" subtitle="Paper run">
          <Badge variant="success">ACTIVE</Badge>
        </ChartCard>
      </div>

      <ChartCard title="Allocation" subtitle="Asset distribution">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={allocation} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100}>
                {allocation.map((entry: any, i: number) => (
                  <Cell key={i} fill={["#10b981", "#3b82f6", "#f59e0b"][i % 3]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}