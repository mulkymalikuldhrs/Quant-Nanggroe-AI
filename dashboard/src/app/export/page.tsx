"use client";
export const dynamic = "force-dynamic";

import React, { useCallback, useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/api-client";
import {
  Download,
  FileSpreadsheet,
  FileText,
  FileType,
  Database,
  RefreshCw,
  Calendar,
} from "lucide-react";

type SummaryRow = {
  strategy: string; n_trades: number; total_pnl: number;
  win_rate: number; avg_pnl: number; best_trade: number; worst_trade: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

function downloadUrl(params: Record<string, string>): string {
  const q = new URLSearchParams(params).toString();
  const url = `${API_BASE}/api/export/trades?${q}`;
  // fetch with auth then trigger browser save (fetch keeps Authorization header)
  return url;
}

async function authedDownload(params: Record<string, string>) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/api/export/trades?${q}`, {
    headers: API_KEY ? { Authorization: `ApiKey ${API_KEY}` } : {},
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => "")}`);
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const name = m?.[1] || `qna_export.${params.format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name; a.click();
  URL.revokeObjectURL(url);
}

export default function ExportCenterPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [strategy, setStrategy] = useState("");
  const [symbol, setSymbol] = useState("");
  const [rows, setRows] = useState<SummaryRow[]>([]);
  const [totalTrades, setTotalTrades] = useState(0);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const p = new URLSearchParams();
      if (dateFrom) p.set("date_from", dateFrom);
      if (dateTo) p.set("date_to", dateTo);
      const d = await apiRequest<{ rows: SummaryRow[]; total_trades: number }>(
        `/api/export/summary?${p.toString()}`);
      setRows(d.rows); setTotalTrades(d.total_trades);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Summary unavailable");
    } finally { setLoading(false); }
  }, [dateFrom, dateTo]);

  useEffect(() => { loadSummary(); }, [loadSummary]);

  const doExport = async (format: string) => {
    setDownloading(format); setError(null);
    try {
      const params: Record<string, string> = { format };
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (strategy) params.strategy = strategy;
      if (symbol) params.symbol = symbol;
      await authedDownload(params);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally { setDownloading(null); }
  };

  return (
    <div className="space-y-4 animate-slide-up">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Download className="w-5 h-5 text-cyan-400" />
          Export Center
        </h1>
        <p className="text-sm text-white/40 mt-0.5">
          Trades &amp; strategy stats — custom date range, multiple formats.
        </p>
      </div>

      <ChartCard title="Filters" subtitle="Empty fields = all time">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="text-[10px] text-white/30 mb-1 block">From</label>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <label className="text-[10px] text-white/30 mb-1 block">To</label>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div>
            <label className="text-[10px] text-white/30 mb-1 block">Strategy</label>
            <Input placeholder="all strategies" value={strategy}
              onChange={(e) => setStrategy(e.target.value)} />
          </div>
          <div>
            <label className="text-[10px] text-white/30 mb-1 block">Symbol contains</label>
            <Input placeholder="XAUUSD" value={symbol}
              onChange={(e) => setSymbol(e.target.value)} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" size="sm" onClick={loadSummary} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh stats
          </Button>
          {[
            { f: "xlsx", label: "Excel", icon: FileSpreadsheet },
            { f: "csv", label: "CSV", icon: Database },
            { f: "md", label: "Markdown", icon: FileText },
            { f: "json", label: "JSON", icon: FileType },
            { f: "pdf", label: "PDF", icon: FileType },
          ].map(({ f, label, icon: Icon }) => (
            <Button key={f} variant="glow" size="sm"
              onClick={() => doExport(f)}
              disabled={downloading !== null}>
              {downloading === f
                ? <RefreshCw className="w-3.5 h-3.5 mr-1 animate-spin" />
                : <Download className="w-3.5 h-3.5 mr-1" />}
              {label}
            </Button>
          ))}
        </div>
        {error && (
          <p className="mt-3 text-xs text-red-400/80">{error}</p>
        )}
      </ChartCard>

      <ChartCard title="Strategy Summary"
        subtitle={`${totalTrades} trades in range`}>
        {rows.length === 0 ? (
          <p className="text-sm text-white/30 py-6 text-center">
            No closed trades in this range.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-[#0A0A0E]">
                <tr className="text-left text-[10px] uppercase tracking-wider text-white/30">
                  <th className="px-3 py-2">Strategy</th>
                  <th className="px-3 py-2">Trades</th>
                  <th className="px-3 py-2">Total PnL</th>
                  <th className="px-3 py-2">Win Rate</th>
                  <th className="px-3 py-2">Avg PnL</th>
                  <th className="px-3 py-2">Best</th>
                  <th className="px-3 py-2">Worst</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.strategy} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                    <td className="px-3 py-2 font-medium text-white/70">{r.strategy}</td>
                    <td className="px-3 py-2 font-mono tabular-nums text-white/60">{r.n_trades}</td>
                    <td className={`px-3 py-2 font-mono tabular-nums ${r.total_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {r.total_pnl >= 0 ? "+" : ""}{r.total_pnl.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums text-white/60">{(r.win_rate * 100).toFixed(1)}%</td>
                    <td className="px-3 py-2 font-mono tabular-nums text-white/60">{r.avg_pnl.toFixed(2)}</td>
                    <td className="px-3 py-2 font-mono tabular-nums text-emerald-400/70">+{r.best_trade.toFixed(2)}</td>
                    <td className="px-3 py-2 font-mono tabular-nums text-red-400/70">{r.worst_trade.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-[10px] text-white/20 flex items-center gap-1.5">
          <Calendar className="w-3 h-3" />
          PDF requires reportlab on the backend — other formats always available.
        </p>
      </ChartCard>
    </div>
  );
}
