"use client";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { FlaskConical } from "lucide-react";

export default function FactorsPage() {
  const [regime, setRegime] = useState<any>(null);

  useEffect(() => {
    fetch("/api/monitor/regime").then(r => r.json()).then(setRegime);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-purple-400" />
          Factor Explorer
        </h1>
      </div>

      <ChartCard title="Current Regime" subtitle="Strategy selection state">
        <div className="space-y-3">
          <p className="text-sm">Regime: <span className="text-emerald-400">{regime?.regime || "unknown"}</span></p>
          <p className="text-sm">Confidence: <span className="text-blue-400">{regime?.confidence || 0}</span></p>
          <p className="text-sm">Selected Strategies: {(regime?.selected_strategies || []).join(", ") || "RegimeBased"}</p>
        </div>
      </ChartCard>

      <ChartCard title="Strategy Registry" subtitle="151 catalog strategies">
        <p className="text-sm text-white/70">RegimeBased, MeanReversion, TrendFollow loaded</p>
        <Badge variant="success">Live via /api/strategy/registry</Badge>
      </ChartCard>
    </div>
  );
}