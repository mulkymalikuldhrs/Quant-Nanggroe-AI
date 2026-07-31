// Shared hooks + Card wrapper for terminal panels.
// Extracted from page.tsx so new panels can import without duplicating.

import React, { useState, useEffect, useCallback, useRef } from "react";
import { apiRequest } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { RefreshCw, AlertCircle } from "lucide-react";

export { cn } from "@/lib/utils";

export const REFRESH_MS = 30000;
const API = (ep: string) => `/api/terminal/${ep}`;

/* ─── helpers ─────────────────────────────────────────────────────── */
export function clsPct(v: number | null | undefined) {
  if (v == null) return "text-white/30";
  if (v > 0) return "text-profit";
  if (v < 0) return "text-loss";
  return "text-white/70";
}

export function fmtPct(v: number | null | undefined) {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function fmtNum(n: number | null | undefined, d = 2) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
}

export function flowColor(lbl: string) {
  if (lbl === "SURGE") return "text-profit";
  if (lbl === "HIGH") return "text-emerald-400";
  if (lbl === "NORMAL") return "text-white/60";
  return "text-white/30";
}

export function badgeColor(bias: string) {
  if (bias?.includes("CROWDED")) return "text-orange-400 bg-orange-400/10";
  if (bias?.includes("LONG")) return "text-profit bg-profit/10";
  if (bias?.includes("SHORT")) return "text-loss bg-loss/10";
  return "text-white/40 bg-white/5";
}

export function green(v: number) {
  return v > 0;
}

/* ─── fetch hook ───────────────────────────────────────────────────── */
export function useTerminalData<T>(endpoint: string, fallback: T): {
  data: T;
  loading: boolean;
  error: string | null;
  refresh: () => void;
} {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const res = await apiRequest<T>(API(endpoint), { deduplicate: false });
      if (mounted.current) {
        setData(res);
        setError(null);
      }
    } catch (e: any) {
      if (mounted.current) setError(e?.message || "fetch failed");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => {
      mounted.current = false;
      clearInterval(id);
    };
  }, [refresh]);

  return { data, loading, error, refresh };
}

/* ─── Card wrapper ─────────────────────────────────────────────────── */
export function Card({
  title,
  col,
  loading,
  error,
  children,
  onRefresh,
}: {
  title: string;
  col: string;
  loading?: boolean;
  error?: string | null;
  children: React.ReactNode;
  onRefresh?: () => void;
}) {
  return (
    <div
      className={cn("bbg-cell p-0 flex flex-col", col)}
      style={{ minHeight: 140 }}
    >
      <div className="flex items-center justify-between px-2.5 py-1.5 border-b border-white/[0.04] bg-black/20">
        <span className="text-[9px] font-bold uppercase tracking-[1.2px] text-amber-400/90 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-amber-400/70 inline-block rounded-sm" />
          {title}
        </span>
        <div className="flex items-center gap-1">
          {loading && (
            <span className="w-2 h-2 rounded-full bg-amber-400/50 animate-pulse" />
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-0.5 hover:bg-white/5 rounded"
            >
              <RefreshCw className="w-2.5 h-2.5 text-white/30" />
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 p-2.5 text-[11px] font-mono overflow-auto">
        {error ? (
          <div className="flex items-center gap-1.5 text-loss/80 text-[10px] h-full">
            <AlertCircle className="w-3 h-3 shrink-0" />
            <span>{error}</span>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
