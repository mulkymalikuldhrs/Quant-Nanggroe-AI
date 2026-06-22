"use client";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn, formatPercent } from "@/lib/utils";
import apiRequest from "@/lib/api-client";
import { Zap, Play, Pause, Plus, Code, Upload, Settings, Loader2 } from "lucide-react";

interface Strategy {
  id: string; name: string; type: string; performance: number; sharpe: number; status: string;
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiRequest<Strategy[]>("/api/v1/strategies");
        setStrategies(data);
      } catch {
        setStrategies([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const strategyColumns = [
    { key: "name", header: "Strategy", render: (row: Record<string, unknown>) => (<div><p className="font-medium text-white">{row.name as string}</p><p className="text-xs text-white/30">{row.type as string}</p></div>) },
    { key: "performance", header: "Return", render: (row: Record<string, unknown>) => (<span className={cn("font-mono font-medium", (row.performance as number) >= 0 ? "text-emerald-400" : "text-red-400")}>{formatPercent(row.performance as number)}</span>) },
    { key: "sharpe", header: "Sharpe", render: (row: Record<string, unknown>) => (<span className="font-mono text-blue-400">{(row.sharpe as number).toFixed(2)}</span>) },
    { key: "status", header: "Status", render: (row: Record<string, unknown>) => (<Badge variant={(row.status as string) === "active" ? "success" : "warning"} className="text-[10px]">{(row.status as string).toUpperCase()}</Badge>) },
    { key: "actions", header: "Actions", render: (row: Record<string, unknown>) => (<div className="flex items-center gap-1"><Button variant="ghost" size="sm" className="h-7 px-2">{(row.status as string) === "active" ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}</Button><Button variant="ghost" size="sm" className="h-7 px-2"><Settings className="w-3 h-3" /></Button></div>) },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div><h1 className="text-xl font-bold text-white flex items-center gap-2"><Zap className="w-5 h-5 text-amber-400" />Strategy Management</h1><p className="text-sm text-white/40 mt-0.5">Strategy lifecycle, schema & backtest adapters</p></div>
        <Button variant="glow"><Plus className="w-3.5 h-3.5 mr-1.5" />New Strategy</Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatusCard title="Active Strategies" value={String(strategies.filter(s => s.status === "active").length)} variant="success" />
        <StatusCard title="Paused" value={String(strategies.filter(s => s.status === "paused").length)} variant="warning" />
        <StatusCard title="Avg Return" value={strategies.length > 0 ? formatPercent(strategies.reduce((a, s) => a + s.performance, 0) / strategies.length) : "0%"} variant="success" />
        <StatusCard title="Avg Sharpe" value={strategies.length > 0 ? (strategies.reduce((a, s) => a + s.sharpe, 0) / strategies.length).toFixed(2) : "0"} />
      </div>

      <Tabs defaultValue="list">
        <TabsList><TabsTrigger value="list">Strategy List</TabsTrigger><TabsTrigger value="schema">Schema Editor</TabsTrigger><TabsTrigger value="loader">Loader/Parser</TabsTrigger><TabsTrigger value="adapter">Backtest Adapter</TabsTrigger></TabsList>
        <TabsContent value="list">
          <ChartCard title="Strategies" subtitle="All trading strategies" className="mt-3">
            {strategies.length > 0 ? (
              <DataTable columns={strategyColumns} data={strategies as unknown as Record<string, unknown>[]} onRowClick={(row) => setSelectedStrategy(row.id as string)} />
            ) : <p className="text-sm text-white/30 text-center py-8">No strategies available</p>}
          </ChartCard>
          {selectedStrategy && (() => {
            const strat = strategies.find((s) => s.id === selectedStrategy);
            if (!strat) return null;
            return (<ChartCard title="Strategy Detail" subtitle={strat.name} className="mt-3" glow="emerald"><div className="grid grid-cols-1 lg:grid-cols-2 gap-4"><div className="space-y-3"><div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"><p className="text-xs text-white/40 mb-2">Configuration</p><div className="space-y-1.5"><div className="flex justify-between"><span className="text-xs text-white/30">Type</span><span className="text-xs text-white/70">{strat.type}</span></div><div className="flex justify-between"><span className="text-xs text-white/30">Status</span><Badge variant={strat.status === "active" ? "success" : "warning"} className="text-[10px]">{strat.status}</Badge></div><div className="flex justify-between"><span className="text-xs text-white/30">Total Return</span><span className={cn("text-xs font-mono", strat.performance >= 0 ? "text-emerald-400" : "text-red-400")}>{formatPercent(strat.performance)}</span></div><div className="flex justify-between"><span className="text-xs text-white/30">Sharpe Ratio</span><span className="text-xs font-mono text-blue-400">{strat.sharpe.toFixed(2)}</span></div></div></div><div className="flex gap-2"><Button variant="default" className="flex-1"><Play className="w-3 h-3 mr-1" />Backtest</Button><Button variant="ghost" className="flex-1"><Code className="w-3 h-3 mr-1" />Edit</Button></div></div><div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"><p className="text-xs text-white/40 mb-2">Performance History</p><div className="h-32 flex items-end gap-1">{Array.from({ length: 12 }, (_, i) => { const val = Math.random() * 5 + (strat.performance > 0 ? 1 : -1); return (<div key={i} className="flex-1 flex flex-col items-center gap-1"><div className={cn("w-full rounded-t", val >= 0 ? "bg-emerald-500/30" : "bg-red-500/30")} style={{ height: `${Math.abs(val) * 20}px` }} /><span className="text-[8px] text-white/20">{["J","F","M","A","M","J","J","A","S","O","N","D"][i]}</span></div>); })}</div></div></div></ChartCard>);
          })()}
        </TabsContent>
        <TabsContent value="schema">
          <ChartCard title="Strategy Schema Editor" subtitle="Define strategy structure" className="mt-3">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div><p className="text-xs text-white/40 mb-2">Strategy Schema (JSON)</p><div className="p-3 rounded-lg bg-black/30 border border-white/[0.06] font-mono text-xs text-emerald-300/80 overflow-x-auto"><pre>{JSON.stringify({name:"momentum_alpha",version:"2.1.0",type:"momentum",parameters:{lookback_period:20,momentum_threshold:0.05,position_size:0.1,stop_loss:0.02,take_profit:0.05},signals:["price_momentum","volume_surge","trend_strength"],risk:{max_position:0.10,max_drawdown:-0.05,kelly_fraction:0.5},execution:{order_type:"limit",time_in_force:"GTC",slippage_model:"percentage"}},null,2)}</pre></div></div>
              <div className="space-y-3"><p className="text-xs text-white/40 mb-2">Schema Validation</p><div className="p-3 rounded-lg bg-emerald-500/[0.05] border border-emerald-500/15"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-400" /><span className="text-xs text-emerald-400">Schema valid</span></div></div><Button variant="glow" className="w-full"><Code className="w-3.5 h-3.5 mr-1.5" />Save Schema</Button></div>
            </div>
          </ChartCard>
        </TabsContent>
        <TabsContent value="loader">
          <ChartCard title="Strategy Loader/Parser" subtitle="Load strategies from files" className="mt-3">
            <div className="space-y-4">
              <div className="border-2 border-dashed border-white/[0.08] rounded-xl p-8 text-center hover:border-white/[0.15] transition-colors cursor-pointer"><Upload className="w-8 h-8 text-white/20 mx-auto mb-3" /><p className="text-sm text-white/40">Drop strategy files here</p></div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{[{name:"momentum_alpha_v2.py",type:"Python",size:"4.2 KB",status:"loaded"},{name:"value_quality.json",type:"JSON",size:"1.8 KB",status:"loaded"},{name:"mean_reversion.yaml",type:"YAML",size:"2.1 KB",status:"error"}].map((file) => (<div key={file.name} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"><div className="flex items-center gap-2"><Code className="w-3.5 h-3.5 text-white/30" /><div><p className="text-xs font-mono text-white/70">{file.name}</p><p className="text-[10px] text-white/30">{file.type} • {file.size}</p></div></div><Badge variant={file.status === "loaded" ? "success" : "danger"} className="text-[10px]">{file.status}</Badge></div>))}</div>
            </div>
          </ChartCard>
        </TabsContent>
        <TabsContent value="adapter">
          <ChartCard title="Backtest Adapter Configuration" subtitle="Connect strategies to backtest engines" className="mt-3">
            {strategies.length > 0 ? (
              <div className="space-y-3">{strategies.map((strat) => (<div key={strat.id} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"><div className="flex items-center justify-between mb-2"><span className="text-sm font-medium text-white/80">{strat.name}</span><Badge variant={strat.status === "active" ? "success" : "warning"} className="text-[10px]">{strat.status}</Badge></div><div className="grid grid-cols-2 gap-3"><div><p className="text-[10px] text-white/30 mb-1">Engine</p><p className="text-xs text-white/60">{strat.type === "Crypto" ? "Crypto Engine" : strat.type === "Forex" ? "Forex Engine" : "Equity Engine"}</p></div><div><p className="text-[10px] text-white/30 mb-1">Data Loader</p><p className="text-xs text-white/60">{strat.type === "Crypto" ? "CCXT Loader" : "YFinance Loader"}</p></div></div></div>))}</div>
            ) : <p className="text-sm text-white/30 text-center py-8">No strategies to configure</p>}
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
