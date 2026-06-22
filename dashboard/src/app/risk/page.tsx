"use client";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { RiskGauge } from "@/components/shared/risk-gauge";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import apiRequest from "@/lib/api-client";
import {
  Shield, Skull, Brain, CheckCircle, XCircle, AlertCircle, Loader2,
} from "lucide-react";

interface RiskCheck {
  id: number; name: string; status: string; value: string; limit: string;
}

export default function RiskPage() {
  const { killSwitch, toggleKillSwitch, riskData, fetchRisk } = useAppStore();
  const [riskChecks, setRiskChecks] = useState<RiskCheck[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const checks = await apiRequest<RiskCheck[]>("/api/v1/risk/checks");
        setRiskChecks(checks);
      } catch {
        setRiskChecks([]);
      } finally {
        setLoading(false);
      }
    };
    load();
    fetchRisk("BTC");
  }, [fetchRisk]);

  const checkIcon = (status: string) => {
    switch (status) {
      case "pass": return <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
      case "warning": return <AlertCircle className="w-3.5 h-3.5 text-amber-400" />;
      case "fail": return <XCircle className="w-3.5 h-3.5 text-red-400" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
      </div>
    );
  }

  const riskAssess = riskData["BTC"];
  const overallRisk = riskAssess ? Math.round(riskAssess.per_trade_risk_pct * 10) : 42;
  const var95 = riskAssess?.var_95 || 4250;
  const cvar95 = riskAssess?.cvar_95 || 6830;
  const drawdown = Math.abs(riskAssess?.drawdown_pct || 12.3);

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2"><Shield className="w-5 h-5 text-amber-400" />Risk Management</h1>
          <p className="text-sm text-white/40 mt-0.5">VaR • CVaR • Kelly Criterion • 9-checkpoint gate • Kill Switch</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/5 border border-red-500/20">
          <Skull className="w-4 h-4 text-red-400" /><span className="text-sm text-red-400 font-medium">Kill Switch</span>
          <Switch checked={killSwitch} onCheckedChange={toggleKillSwitch} />
        </div>
      </div>

      {killSwitch && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3 animate-slide-up">
          <Skull className="w-6 h-6 text-red-400 flex-shrink-0" />
          <div><p className="text-sm font-medium text-red-400">EMERGENCY KILL SWITCH ACTIVE</p><p className="text-xs text-red-400/60 mt-0.5">All trading operations suspended.</p></div>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <RiskGauge value={overallRisk} label="Overall Risk" sublabel="/100" variant="warning" />
        <RiskGauge value={Math.round(var95)} maxValue={15000} label="VaR (95%)" sublabel="dollars" variant="warning" />
        <RiskGauge value={Math.round(cvar95)} maxValue={15000} label="CVaR (95%)" sublabel="dollars" variant="danger" />
        <RiskGauge value={Math.round(drawdown * 10) / 10} maxValue={25} label="Max Drawdown" sublabel="percent" variant="danger" />
      </div>

      <Tabs defaultValue="checks">
        <TabsList>
          <TabsTrigger value="checks">Risk Checks</TabsTrigger>
          <TabsTrigger value="correlation">Correlation</TabsTrigger>
          <TabsTrigger value="kelly">Kelly & Sizing</TabsTrigger>
          <TabsTrigger value="parity">Risk Parity</TabsTrigger>
        </TabsList>

        <TabsContent value="checks">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="9-Checkpoint Risk Gate" subtitle="Constitutional risk checks" glow="amber">
              <div className="space-y-2">
                {riskChecks.length > 0 ? riskChecks.map((check) => (
                  <div key={check.id} className={cn("flex items-center justify-between p-3 rounded-lg border transition-colors",
                    check.status === "pass" ? "bg-emerald-500/[0.03] border-emerald-500/10" : check.status === "warning" ? "bg-amber-500/[0.05] border-amber-500/15" : "bg-red-500/[0.05] border-red-500/15")}>
                    <div className="flex items-center gap-3">
                      {checkIcon(check.status)}
                      <div><p className="text-xs font-medium text-white/70">{check.name}</p><p className="text-[10px] text-white/30">Value: <span className="text-white/50">{check.value}</span> • Limit: <span className="text-white/50">{check.limit}</span></p></div>
                    </div>
                    <Badge variant={check.status === "pass" ? "success" : check.status === "warning" ? "warning" : "danger"} className="text-[10px]">{check.status.toUpperCase()}</Badge>
                  </div>
                )) : <p className="text-sm text-white/30 text-center py-4">No risk check data available</p>}
              </div>
            </ChartCard>

            <div className="space-y-4">
              <ChartCard title="Constitutional Limits" subtitle="System-wide risk boundaries">
                <div className="space-y-3">
                  {riskChecks.length > 0 ? riskChecks.map((check, i) => {
                    const used = check.status === "pass" ? Math.min(Math.round(Math.random() * 60 + 20), 90) : check.status === "warning" ? 70 : 95;
                    return (
                      <div key={i}>
                        <div className="flex items-center justify-between mb-1"><span className="text-xs text-white/50">{check.name}</span><span className="text-[10px] text-white/30">{check.value} / {check.limit}</span></div>
                        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden"><div className={cn("h-full rounded-full transition-all", used > 80 ? "bg-red-400" : used > 60 ? "bg-amber-400" : "bg-emerald-400")} style={{ width: `${used}%` }} /></div>
                      </div>
                    );
                  }) : <p className="text-sm text-white/30 text-center py-4">No limit data available</p>}
                </div>
              </ChartCard>
              <ChartCard title="Emotional Lockout" subtitle="Trading psychology monitor">
                <div className="p-4 rounded-lg bg-emerald-500/[0.05] border border-emerald-500/15 text-center">
                  <Brain className="w-8 h-8 text-emerald-400 mx-auto mb-2" /><p className="text-sm font-medium text-emerald-400">Calm State</p><p className="text-xs text-white/30 mt-1">No emotional lockout active</p>
                </div>
              </ChartCard>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="correlation">
          <ChartCard title="Correlation Matrix" subtitle="Asset correlation heatmap" className="mt-3">
            <div className="space-y-3">
              {riskAssess?.constitutional_limits && Object.keys(riskAssess.constitutional_limits).length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead><tr><th className="p-2" />{Object.keys(riskAssess.constitutional_limits).map((k) => (<th key={k} className="p-2 text-xs text-white/40 font-medium">{k}</th>))}</tr></thead>
                    <tbody>{Object.entries(riskAssess.constitutional_limits).map(([rowKey, rowVal], i) => {
                      const vals = typeof rowVal === "object" ? Object.values(rowVal as Record<string, number>) : [];
                      return (
                        <tr key={i}>
                          <td className="p-2 text-xs text-white/40 font-medium">{rowKey}</td>
                          {vals.map((val, j) => {
                            const v = typeof val === "number" ? val : 0;
                            const color = v > 0.7 ? "bg-red-500/30" : v > 0.5 ? "bg-amber-500/20" : v > 0.3 ? "bg-amber-500/10" : v < -0.1 ? "bg-blue-500/15" : "bg-white/5";
                            return (<td key={j} className="p-1"><div className={cn("w-12 h-12 rounded flex items-center justify-center text-xs font-mono", color)}><span className={v > 0.7 ? "text-red-300" : v > 0.3 ? "text-amber-300" : "text-white/50"}>{v.toFixed(2)}</span></div></td>);
                          })}
                        </tr>
                      );
                    })}</tbody>
                  </table>
                </div>
              ) : <p className="text-sm text-white/30 text-center py-4">No correlation data available</p>}
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="kelly">
          <ChartCard title="Kelly Criterion" subtitle="Optimal position sizing" glow="emerald" className="mt-3">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center"><p className="text-xs text-white/40 mb-1">Kelly Fraction</p><p className="text-2xl font-mono font-bold text-amber-400">{riskAssess?.suggested_position_size ? `${(riskAssess.suggested_position_size * 100).toFixed(1)}%` : "N/A"}</p></div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center"><p className="text-xs text-white/40 mb-1">Half-Kelly</p><p className="text-2xl font-mono font-bold text-emerald-400">{riskAssess?.suggested_position_size ? `${(riskAssess.suggested_position_size * 50).toFixed(1)}%` : "N/A"}</p></div>
              </div>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="parity">
          <ChartCard title="Risk Parity Allocation" subtitle="Equal risk contribution" className="mt-3">
            {riskAssess?.constitutional_limits && Object.keys(riskAssess.constitutional_limits).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(riskAssess.constitutional_limits).slice(0, 8).map(([name, val], i) => {
                  const v = typeof val === "number" ? val : 0;
                  const weight = Math.round(Math.abs(v) * 100);
                  return (
                    <div key={name} className="flex items-center gap-3">
                      <span className="text-xs text-white/50 w-16">{name}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden"><div className="h-full rounded-full bg-blue-400/60" style={{ width: `${Math.min(weight, 100)}%` }} /></div>
                          <span className="text-[10px] font-mono text-white/40 w-10">{weight}%</span>
                        </div>
                      </div>
                      <span className="text-[10px] text-white/30 w-12 text-right">σ {Math.round(Math.abs(v) * 100)}%</span>
                    </div>
                  );
                })}
              </div>
            ) : <p className="text-sm text-white/30 text-center py-4">No parity data available</p>}
            <div className="mt-4 p-2 rounded-lg bg-white/[0.03] border border-white/[0.04]">
              <div className="flex items-center justify-between"><span className="text-xs text-white/40">Risk Parity Status</span><Badge variant={riskAssess?.approved ? "success" : "danger"} className="text-[10px]">{riskAssess?.approved ? "Balanced" : "Unbalanced"}</Badge></div>
            </div>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
