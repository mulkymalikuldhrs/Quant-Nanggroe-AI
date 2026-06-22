"use client";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import apiRequest from "@/lib/api-client";
import { Sigma, Search, FlaskConical, Plus, Minus, ChevronRight, Loader2 } from "lucide-react";

interface FactorZoo {
  name: string; count: number; description: string;
}

interface FactorDetail {
  name: string; category: string; ic: number; returns: number;
}

export default function FactorsPage() {
  const [factorZoos, setFactorZoos] = useState<FactorZoo[]>([]);
  const [factorDetails, setFactorDetails] = useState<Record<string, FactorDetail[]>>({});
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedZoo, setSelectedZoo] = useState<string | null>(null);
  const [pipelineFactors, setPipelineFactors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [zoos, details] = await Promise.all([
          apiRequest<FactorZoo[]>("/api/v1/factors/zoos").catch(() => []),
          apiRequest<Record<string, FactorDetail[]>>("/api/v1/factors/details").catch(() => ({})),
        ]);
        setFactorZoos(zoos);
        setFactorDetails(details);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredFactors = selectedZoo && factorDetails[selectedZoo]
    ? factorDetails[selectedZoo].filter((f) => f.name.toLowerCase().includes(searchTerm.toLowerCase()) || f.category.toLowerCase().includes(searchTerm.toLowerCase()))
    : Object.values(factorDetails).flat().filter((f) => f.name.toLowerCase().includes(searchTerm.toLowerCase()) || f.category.toLowerCase().includes(searchTerm.toLowerCase()));

  const togglePipelineFactor = (factorName: string) => {
    setPipelineFactors((prev) => prev.includes(factorName) ? prev.filter((f) => f !== factorName) : [...prev, factorName]);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div><h1 className="text-xl font-bold text-white flex items-center gap-2"><Sigma className="w-5 h-5 text-purple-400" />Alpha Factor Explorer</h1><p className="text-sm text-white/40 mt-0.5">{factorZoos.length} factor zoos • {Object.values(factorDetails).flat().length} alpha factors • Custom pipelines</p></div>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {factorZoos.map((zoo) => (
          <button key={zoo.name} onClick={() => setSelectedZoo(selectedZoo === zoo.name ? null : zoo.name)}
            className={cn("p-3 rounded-xl border text-center transition-all hover:scale-[1.03]", selectedZoo === zoo.name ? "bg-purple-500/15 border-purple-500/30 shadow-[0_0_20px_rgba(168,85,247,0.1)]" : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]")}>
            <p className="text-lg font-bold text-white font-mono">{zoo.count}</p><p className="text-xs font-medium text-white/60 mt-0.5">{zoo.name}</p><p className="text-[10px] text-white/30 mt-0.5">{zoo.description}</p>
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title={selectedZoo ? `${selectedZoo} Factors` : "All Factors"} subtitle={`${filteredFactors.length} factors`} className="lg:col-span-2" action={<Input placeholder="Search factors..." icon={<Search className="w-3 h-3" />} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-48" />}>
          <ScrollArea className="max-h-96"><div className="space-y-1.5">{filteredFactors.slice(0, 50).map((factor, i) => (
            <div key={`${factor.name}-${i}`} className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors cursor-pointer" onClick={() => togglePipelineFactor(factor.name)}>
              <div className="flex items-center gap-3"><button className="w-6 h-6 rounded flex items-center justify-center bg-white/[0.03] hover:bg-white/[0.06]">{pipelineFactors.includes(factor.name) ? <Minus className="w-3 h-3 text-red-400" /> : <Plus className="w-3 h-3 text-emerald-400" />}</button><div><p className="text-sm font-mono font-medium text-white/80">{factor.name}</p><Badge variant="default" className="text-[9px] mt-0.5">{factor.category}</Badge></div></div>
              <div className="flex items-center gap-4"><div className="text-right"><p className="text-[10px] text-white/30">IC</p><p className={cn("text-xs font-mono", factor.ic > 0 ? "text-emerald-400" : "text-red-400")}>{factor.ic.toFixed(3)}</p></div><div className="text-right"><p className="text-[10px] text-white/30">Returns</p><p className={cn("text-xs font-mono", factor.returns > 0 ? "text-emerald-400" : "text-red-400")}>{factor.returns.toFixed(2)}%</p></div></div>
            </div>
          ))}</div></ScrollArea>
        </ChartCard>
        <ChartCard title="Factor Pipeline" subtitle="Build custom pipeline" glow="purple">
          <div className="space-y-3">{pipelineFactors.length === 0 ? (<div className="text-center py-8"><FlaskConical className="w-8 h-8 text-white/10 mx-auto mb-2" /><p className="text-sm text-white/30">Click factors to add to pipeline</p></div>) : (<>{pipelineFactors.map((factor, i) => (<div key={factor} className="flex items-center gap-2"><span className="text-xs text-white/30 w-4">{i + 1}.</span><div className="flex-1 p-2 rounded-lg bg-purple-500/10 border border-purple-500/20"><p className="text-xs font-mono text-purple-300">{factor}</p></div>{i < pipelineFactors.length - 1 && <ChevronRight className="w-3 h-3 text-white/20" />}</div>))}<Button variant="glow" className="w-full mt-3" onClick={() => {}}><FlaskConical className="w-3.5 h-3.5 mr-1.5" />Run Pipeline ({pipelineFactors.length} factors)</Button><Button variant="ghost" className="w-full" onClick={() => setPipelineFactors([])}>Clear Pipeline</Button></>)}</div>
        </ChartCard>
      </div>
    </div>
  );
}
