"use client";
export const dynamic = "force-dynamic";
import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api-client";
import { Activity, Box, Grid3x3 } from "lucide-react";

export default function VectorPage() {
  const [data, setData] = useState<{ manifold: Record<string, number[]>; mispricing: Record<string, { d: number; threshold: number; is_trigger: boolean }> } | null>(null);
  useEffect(() => {
    apiRequest("/api/vector/status").then(setData).catch(() => {});
  }, []);
  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2"><Box className="w-5 h-5 text-purple-400" /> Vector Manifold 3D</h1>
      <p className="text-sm text-white/40">P=xî+yĵ+zk • PointYEN/CHF/CAD • d=||P-P0|| • CADJPY/√2 • grid 0.05σ eigenvector hedged</p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Manifold Points" subtitle="3D projection (x USD, y EUR, z EURUSD)">
          {data ? Object.entries(data.manifold).map(([k, v]) => (
            <div key={k} className="flex justify-between py-1 text-xs font-mono"><span className="text-white/50">{k}</span><span className="text-white/70">{v.map(x=>x.toFixed(4)).join(", ")}</span></div>
          )) : <p className="text-white/30 text-sm">No data — backend /api/vector/status unavailable.</p>}
        </ChartCard>
        <ChartCard title="Euclidean Mispricing" subtitle="d > threshold (box merah)">
          {data ? Object.entries(data.mispricing).map(([k, v]) => (
            <div key={k} className="flex justify-between py-1 text-xs"><span className="text-white/50">{k}</span><span className={v.is_trigger?"text-red-400":"text-emerald-400"}>d={v.d.toFixed(4)} thr={v.threshold.toFixed(4)} {v.is_trigger?"TRIGGER":"OK"}</span></div>
          )) : <p className="text-white/30 text-sm">No mispricing — waiting.</p>}
        </ChartCard>
      </div>
      <ChartCard title="Grid Executor" subtitle="0.05σ limit mesh eigenvector hedged">
        <div className="flex items-center gap-2 text-xs text-white/40"><Grid3x3 className="w-4 h-4" /> Grid 0.05 pip • eigenvector diagonal merah-hijau • hedged</div>
      </ChartCard>
    </div>
  );
}
