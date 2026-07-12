"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { RiskGauge } from "@/components/shared/risk-gauge";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAppStore } from "@/lib/store";
import { portfolioApi, type RiskData, type RiskCheck } from "@/lib/api-client";
import { Shield, Skull } from "lucide-react";

const checkVariant = (s: string) => s === "pass" ? "success" : s === "fail" ? "danger" : "warning";

export default function RiskPage() {
  const { killSwitch, toggleKillSwitch } = useAppStore();
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portfolioApi.getRisk()
      .then(setRisk)
      .catch(() => setRisk(null))
      .finally(() => setLoading(false));
  }, []);

  const checks: RiskCheck[] = risk?.checks || [];
  const kelly = risk?.kellyFraction ?? 0;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-400" /> Risk Management
          </h1>
          <p className="text-sm text-white/40 mt-0.5">VaR • CVaR • Kelly Criterion • Risk checks</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/5 border border-red-500/20">
          <Skull className="w-4 h-4 text-red-400" />
          <span className="text-sm text-red-400 font-medium">Kill Switch</span>
          <Switch checked={killSwitch} onCheckedChange={toggleKillSwitch} />
        </div>
      </div>

      {killSwitch && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3">
          <Skull className="w-6 h-6 text-red-400" />
          <p className="text-sm font-medium text-red-400">Kill Switch Active — All trading suspended</p>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <RiskGauge value={risk?.riskScore ?? 58} label="Overall Risk" sublabel="/100" variant="default" />
        <RiskGauge value={Math.abs(risk?.var95 ?? 0)} maxValue={15000} label="VaR (95%)" variant="warning" />
        <RiskGauge value={Math.abs(risk?.cvar95 ?? 0)} maxValue={15000} label="CVaR (95%)" variant="warning" />
        <RiskGauge value={Math.abs(risk?.maxDrawdown ?? 0)} maxValue={25} label="Max DD" variant="danger" />
      </div>

      <Tabs defaultValue="checks">
        <TabsList>
          <TabsTrigger value="checks">Risk Checks</TabsTrigger>
          <TabsTrigger value="kelly">Kelly & Sizing</TabsTrigger>
          <TabsTrigger value="corr">Correlation</TabsTrigger>
        </TabsList>

        <TabsContent value="checks">
          <ChartCard title="Risk Status" subtitle="Live from /api/portfolio/risk" className="mt-3">
            {loading && <p className="text-sm text-white/40 p-3">Loading…</p>}
            <div className="space-y-2">
              {checks.map((c, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <span className="text-sm text-white/80">{c.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-white/50">{c.value} / lim {c.limit}</span>
                    <Badge variant={checkVariant(c.status)} className="text-[10px]">{c.status.toUpperCase()}</Badge>
                  </div>
                </div>
              ))}
              {!loading && checks.length === 0 && <p className="text-white/40 text-sm p-4">No checks returned</p>}
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="kelly">
          <ChartCard title="Kelly Criterion" subtitle="Position sizing" className="mt-3">
            <p className="text-sm text-white/70">Kelly: {(kelly * 100).toFixed(1)}%</p>
            <p className="text-sm text-white/50">Half-Kelly: {(kelly * 50).toFixed(1)}%</p>
            <p className="text-sm text-white/50">Quarter-Kelly: {(kelly * 25).toFixed(1)}%</p>
          </ChartCard>
        </TabsContent>

        <TabsContent value="corr">
          <ChartCard title="Correlation Matrix" subtitle="Portfolio cross-asset" className="mt-3">
            {risk?.correlationMatrix?.length ? (
              <div className="overflow-x-auto">
                <table className="text-xs font-mono">
                  <thead>
                    <tr>
                      <th className="p-1" />
                      {risk.correlationLabels.map((l) => <th key={l} className="p-1 text-white/50">{l}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {risk.correlationMatrix.map((row, i) => (
                      <tr key={i}>
                        <td className="p-1 text-white/50">{risk.correlationLabels[i]}</td>
                        {row.map((v, j) => (
                          <td key={j} className={`p-1 text-center ${v > 0.7 ? "text-red-400" : v < 0.3 ? "text-emerald-400" : "text-white/60"}`}>{v.toFixed(2)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-white/40 text-sm p-4">No correlation data</p>}
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
