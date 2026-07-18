"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { backtestApi } from "@/lib/api-client";
import type { FactorZoo } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Sigma, Search, FlaskConical, Plus, Minus, ChevronRight } from "lucide-react";

// Full factor data for each zoo — deterministic values (no Math.random)
const factorDetails: Record<string, { name: string; category: string; ic: number; returns: number }[]> = {
  Alpha101: Array.from({ length: 20 }, (_, i) => ({
    name: `Alpha#${i + 1}`,
    category: i < 7 ? "Momentum" : i < 14 ? "Reversal" : "Volume",
    ic: 0.05 + (i % 4) * 0.015,
    returns: 8.0 + (i % 5) * 2.5,
  })),
  GTJA191: Array.from({ length: 20 }, (_, i) => ({
    name: `GTJA_${String.fromCharCode(65 + (i % 26))}${Math.floor(i / 26) || ""}`,
    category: i < 5 ? "Value" : i < 10 ? "Growth" : i < 15 ? "Quality" : "Volatility",
    ic: 0.03 + (i % 5) * 0.012,
    returns: 4.0 + (i % 6) * 2.0,
  })),
  Qlib158: Array.from({ length: 20 }, (_, i) => ({
    name: `Qlib_F${i + 1}`,
    category: i < 6 ? "Technical" : i < 12 ? "Fundamental" : "Alternative",
    ic: 0.04 + (i % 4) * 0.02,
    returns: 6.0 + (i % 7) * 1.8,
  })),
  Barra: Array.from({ length: 10 }, (_, i) => ({
    name: ["MKT", "SMB", "HML", "RMW", "CMA", "MOM", "VOL", "LIQ", "SIZE", "BETA"][i],
    category: "Risk Factor",
    ic: 0.02 + i * 0.004,
    returns: 3.0 + i * 0.8,
  })),
  Technical: [
    { name: "RSI_14", category: "Momentum", ic: 0.045, returns: 8.2 },
    { name: "MACD", category: "Trend", ic: 0.052, returns: 10.5 },
    { name: "BB_WIDTH", category: "Volatility", ic: 0.038, returns: 5.7 },
    { name: "ATR_14", category: "Volatility", ic: 0.029, returns: 3.8 },
    { name: "OBV", category: "Volume", ic: 0.041, returns: 7.1 },
  ],
  Fundamental: [
    { name: "PE_RATIO", category: "Value", ic: 0.067, returns: 12.3 },
    { name: "ROE", category: "Quality", ic: 0.078, returns: 15.1 },
    { name: "DEBT_EQ", category: "Quality", ic: -0.034, returns: -2.1 },
  ],
  Academic: [
    { name: "FAMA_FRENCH_3F", category: "Factor Model", ic: 0.089, returns: 18.5 },
  ],
};

export default function FactorsPage() {
  const [factorZoos, setFactorZoos] = useState<FactorZoo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedZoo, setSelectedZoo] = useState<string | null>(null);
  const [pipelineFactors, setPipelineFactors] = useState<string[]>([]);

  useEffect(() => {
    backtestApi.getFactors()
      .then(d => { setFactorZoos(d); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  const filteredFactors = selectedZoo && factorDetails[selectedZoo]
    ? factorDetails[selectedZoo].filter((f) =>
        f.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        f.category.toLowerCase().includes(searchTerm.toLowerCase()),
      )
    : Object.values(factorDetails)
        .flat()
        .filter((f) =>
          f.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          f.category.toLowerCase().includes(searchTerm.toLowerCase()),
        );

  const togglePipelineFactor = (factorName: string) => {
    setPipelineFactors((prev) =>
      prev.includes(factorName) ? prev.filter((f) => f !== factorName) : [...prev, factorName],
    );
  };

  if (loading) return <div className="space-y-4 animate-slide-up"><p className="text-white/40">Loading factor zoo data...</p></div>;
  if (error) return <div className="space-y-4 animate-slide-up"><p className="text-red-400">Error: {error}</p></div>;

  const totalFactors = factorZoos.reduce((sum, z) => sum + z.count, 0);

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Sigma className="w-5 h-5 text-purple-400" />
          Alpha Factor Explorer
        </h1>
        <p className="text-sm text-white/40 mt-0.5">{factorZoos.length} factor zoos • {totalFactors} alpha factors • Custom pipelines</p>
      </div>

      {/* Coming Soon banner — module is illustrative only */}
      <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 flex items-center gap-3">
        <Badge variant="info" className="text-xs">Coming Soon</Badge>
        <p className="text-sm text-white/50">The Alpha Factor Explorer is under development — factor statistics shown are illustrative samples, not live computed factors.</p>
      </div>

      {/* Factor Zoo Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {factorZoos.map((zoo) => (
          <button
            key={zoo.name}
            onClick={() => setSelectedZoo(selectedZoo === zoo.name ? null : zoo.name)}
            className={cn(
              "p-3 rounded-xl border text-center transition-all hover:scale-[1.03]",
              selectedZoo === zoo.name
                ? "bg-purple-500/15 border-purple-500/30 shadow-[0_0_20px_rgba(168,85,247,0.1)]"
                : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]",
            )}
          >
            <p className="text-lg font-bold text-white font-mono">{zoo.count}</p>
            <p className="text-xs font-medium text-white/60 mt-0.5">{zoo.name}</p>
            <p className="text-[10px] text-white/30 mt-0.5">{zoo.description}</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Factor List */}
        <ChartCard
          title={selectedZoo ? `${selectedZoo} Factors` : "All Factors"}
          subtitle={`${filteredFactors.length} factors`}
          className="lg:col-span-2"
          action={
            <Input
              placeholder="Search factors..."
              icon={<Search className="w-3 h-3" />}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-48"
            />
          }
        >
          <ScrollArea className="max-h-96">
            <div className="space-y-1.5">
              {filteredFactors.slice(0, 50).map((factor, i) => (
                <div
                  key={`${factor.name}-${i}`}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors cursor-pointer"
                  onClick={() => togglePipelineFactor(factor.name)}
                >
                  <div className="flex items-center gap-3">
                    <button className="w-6 h-6 rounded flex items-center justify-center bg-white/[0.03] hover:bg-white/[0.06] transition-colors">
                      {pipelineFactors.includes(factor.name) ? (
                        <Minus className="w-3 h-3 text-red-400" />
                      ) : (
                        <Plus className="w-3 h-3 text-emerald-400" />
                      )}
                    </button>
                    <div>
                      <p className="text-sm font-mono font-medium text-white/80">{factor.name}</p>
                      <Badge variant="default" className="text-[9px] mt-0.5">{factor.category}</Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-[10px] text-white/30">IC</p>
                      <p className={cn("text-xs font-mono", Number(factor.ic) > 0 ? "text-emerald-400" : "text-red-400")}>
                        {Number(factor.ic).toFixed(3)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-white/30">Returns</p>
                      <p className={cn("text-xs font-mono", Number(factor.returns) > 0 ? "text-emerald-400" : "text-red-400")}>
                        {Number(factor.returns).toFixed(2)}%
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>

        {/* Pipeline Builder */}
        <ChartCard title="Factor Pipeline" subtitle="Build custom pipeline" glow="purple">
          <div className="space-y-3">
            {pipelineFactors.length === 0 ? (
              <div className="text-center py-8">
                <FlaskConical className="w-8 h-8 text-white/10 mx-auto mb-2" />
                <p className="text-sm text-white/30">Click factors to add to pipeline</p>
                <p className="text-xs text-white/20 mt-1">Build your custom factor pipeline</p>
              </div>
            ) : (
              <>
                {pipelineFactors.map((factor, i) => (
                  <div key={factor} className="flex items-center gap-2">
                    <span className="text-xs text-white/30 w-4">{i + 1}.</span>
                    <div className="flex-1 p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
                      <p className="text-xs font-mono text-purple-300">{factor}</p>
                    </div>
                    {i < pipelineFactors.length - 1 && (
                      <ChevronRight className="w-3 h-3 text-white/20" />
                    )}
                  </div>
                ))}
                <Button
                  variant="glow"
                  className="w-full mt-3"
                  onClick={() => console.log("Running pipeline:", pipelineFactors)}
                >
                  <FlaskConical className="w-3.5 h-3.5 mr-1.5" />
                  Run Pipeline ({pipelineFactors.length} factors)
                </Button>
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() => setPipelineFactors([])}
                >
                  Clear Pipeline
                </Button>
              </>
            )}
          </div>
        </ChartCard>
      </div>

      {/* Factor Correlation Heatmap */}
      <ChartCard title="Factor Correlation Heatmap" subtitle="Top factor correlations">
        <div className="overflow-x-auto">
          {(() => {
            const topFactors = filteredFactors.slice(0, 8);
            return (
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="p-2" />
                    {topFactors.map((f, i) => (
                      <th key={i} className="p-1 text-[10px] text-white/40 font-mono">
                        {f.name.slice(0, 8)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {topFactors.map((rowFactor, i) => (
                    <tr key={i}>
                      <td className="p-1 text-[10px] text-white/40 font-mono text-right pr-2">
                        {rowFactor.name.slice(0, 8)}
                      </td>
                      {topFactors.map((_, j) => {
                        // Deterministic correlation: stronger for similar-index factors
                        const val = i === j ? 1 : 0.4 / (Math.abs(i - j) + 0.5) - 0.1;
                        const clamped = Math.max(-1, Math.min(1, val));
                        const absVal = Math.abs(clamped);
                        const color =
                          clamped > 0.6
                            ? "bg-red-500/30"
                            : clamped > 0.3
                              ? "bg-amber-500/15"
                              : clamped < -0.3
                                ? "bg-blue-500/20"
                                : "bg-white/5";
                        return (
                          <td key={j} className="p-0.5">
                            <div
                              className={cn(
                                "w-10 h-10 rounded flex items-center justify-center text-[9px] font-mono",
                                color,
                              )}
                            >
                              <span className={absVal > 0.6 ? "text-white/70" : "text-white/30"}>
                                {clamped.toFixed(1)}
                              </span>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })()}
        </div>
      </ChartCard>
    </div>
  );
}
