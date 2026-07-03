"use client";

import { useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FlaskConical } from "lucide-react";

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("BTC");
  const [strategy] = useState("RegimeBased");
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  const runBacktest = async () => {
    setIsRunning(true);
    try {
      const res = await fetch("/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, strategy }),
      });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <FlaskConical className="w-5 h-5 text-blue-400" />
        Backtesting
      </h1>
      <ChartCard title="Configuration" subtitle="Run backtest via API">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-white/40 mb-1 block">Symbol</label>
            <Input value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="e.g. BTC" />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Strategy</label>
            <Input value={strategy} readOnly className="opacity-60" />
          </div>
        </div>
        <Button variant="glow" onClick={runBacktest} disabled={isRunning}>
          {isRunning ? "Running..." : "Run Backtest"}
        </Button>
        {result && (
          <div className="mt-4 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <pre className="text-xs text-white/70">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
      </ChartCard>
    </div>
  );
}