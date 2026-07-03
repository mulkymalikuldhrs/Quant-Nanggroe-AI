"use client";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { RiskGauge } from "@/components/shared/risk-gauge";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { Shield, Skull, Brain, CheckCircle, XCircle, AlertCircle } from "lucide-react";

export default function RiskPage() {
  const { killSwitch, toggleKillSwitch } = useAppStore();
  const [riskData, setRiskData] = useState<any>(null);

  useEffect(() => {
    fetch("/api/monitor/summary").then(r => r.json()).then(setRiskData).catch(() => setRiskData(null));
  }, []);

  const risk = riskData?.risk || {};

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-400" />
            Risk Management
          </h1>
          <p className="text-sm text-white/40 mt-0.5">VaR • CVaR • Kelly Criterion • Monitor API</p>
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
        <RiskGauge value={risk?.risk_score || 58} label="Overall Risk" sublabel="/100" variant="default" />
        <RiskGauge value={Math.abs(risk?.var95 || 0)} maxValue={15000} label="VaR (95%)" variant="warning" />
        <RiskGauge value={Math.abs(risk?.cvar95 || 0)} maxValue={15000} label="CVaR (95%)" variant="warning" />
        <RiskGauge value={Math.abs(risk?.max_drawdown || 0)} maxValue={25} label="Max DD" variant="danger" />
      </div>

      <Tabs defaultValue="checks">
        <TabsList>
          <TabsTrigger value="checks">Risk Checks</TabsTrigger>
          <TabsTrigger value="kelly">Kelly & Sizing</TabsTrigger>
        </TabsList>

        <TabsContent value="checks">
          <ChartCard title="Risk Status" subtitle="Live from monitor API" className="mt-3">
            <div className="space-y-2">
              <div className="p-3 rounded-lg bg-emerald-500/[0.03] border border-emerald-500/10">
                <p className="text-xs font-medium">Kill Switch: {(risk?.kill_switch_active ? "ACTIVE" : "INACTIVE")}</p>
              </div>
              <div className="p-3 rounded-lg bg-amber-500/[0.03] border border-amber-500/10">
                <p className="text-xs font-medium">Status: {risk?.overall_status || "unknown"}</p>
              </div>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="kelly">
          <ChartCard title="Kelly Criterion" subtitle="Position sizing" className="mt-3">
            <p className="text-sm text-white/70">Kelly: {(risk?.kelly_fraction || 0) * 100}%</p>
            <p className="text-sm text-white/50">Half-Kelly: {(risk?.kelly_fraction || 0) * 50}%</p>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}