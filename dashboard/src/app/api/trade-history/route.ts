import { NextResponse } from "next/server";
import { execFileSync } from "node:child_process";

export const dynamic = "force-dynamic";

const WORKTREE = process.cwd();
const PYTHON = "C:\\Python314\\python.exe";
const SUBPROCESS_TIMEOUT_MS = 10000;

interface TradeEvent {
  id: number;
  symbol: string;
  timeframe: string;
  signal: string;
  confidence: number;
  traded: boolean;
  notified: boolean;
  regime: string;
  strategy: string;
  entry_price: number;
  sl: number;
  tp: number;
  pnl: number;
  duration_ms: number;
  error: string;
  metadata: string;
  timestamp: string;
}

interface TradeStats {
  total: number;
  trades: number;
  signals: number;
  errors: number;
  last_24h: number;
  by_symbol: Array<{ symbol: string; total: number; trades: number; avg_confidence: number }>;
  by_timeframe: Array<{ timeframe: string; total: number; trades: number; avg_confidence: number }>;
}

// Query params are passed via argv (execFileSync, no shell) and read through
// sys.argv inside Python — never interpolated into the source string.
const QUERY_SCRIPT = `
import sys, json
sys.path.insert(0, sys.argv[1])
symbol = sys.argv[2] or None
timeframe = sys.argv[3] or None
traded_only = sys.argv[4] == "1"
limit = int(sys.argv[5])
page = int(sys.argv[6])
from quant_nanggroe.engine.trade_history import get_trade_history
h = get_trade_history()
events = h.query(symbol=symbol, timeframe=timeframe, traded_only=traded_only, limit=limit, offset=(page - 1) * limit)
total = h.count(symbol=symbol, timeframe=timeframe, traded_only=traded_only)
print(json.dumps({"events": events, "total": total}))
`.trim();

const STATS_SCRIPT = `
import sys, json
sys.path.insert(0, sys.argv[1])
from quant_nanggroe.engine.trade_history import get_trade_history
print(json.dumps(get_trade_history().stats()))
`.trim();

function sanitizeText(value: string | null): string {
  return (value || "").replace(/['"\\`]/g, "").slice(0, 64);
}

function sanitizeInt(value: string | null, fallback: number, max: number): number {
  const parsed = parseInt(value || "", 10);
  if (!Number.isFinite(parsed) || parsed < 1) return fallback;
  return Math.min(parsed, max);
}

function runPython(args: string[]): string {
  return execFileSync(PYTHON, ["-c", ...args], {
    cwd: WORKTREE,
    encoding: "utf8",
    timeout: SUBPROCESS_TIMEOUT_MS,
    windowsHide: true,
    env: { ...process.env, PYTHONPATH: "" },
  });
}

function queryHistory(params: URLSearchParams): { events: TradeEvent[]; total: number; stats: TradeStats } {
  try {
    const symbol = sanitizeText(params.get("symbol"));
    const timeframe = sanitizeText(params.get("timeframe"));
    const traded = params.get("traded") === "1" ? "1" : "0";
    const limit = sanitizeInt(params.get("limit"), 50, 500);
    const page = sanitizeInt(params.get("page"), 1, 100000);

    const result = runPython([QUERY_SCRIPT, WORKTREE, symbol, timeframe, traded, String(limit), String(page)]);
    const parsed = JSON.parse(result.trim());
    const stats = getStats();
    return { events: parsed.events, total: parsed.total, stats };
  } catch {
    return { events: [], total: 0, stats: { total: 0, trades: 0, signals: 0, errors: 0, last_24h: 0, by_symbol: [], by_timeframe: [] } };
  }
}

function getStats(): TradeStats {
  try {
    const result = runPython([STATS_SCRIPT, WORKTREE]);
    return JSON.parse(result.trim());
  } catch {
    return { total: 0, trades: 0, signals: 0, errors: 0, last_24h: 0, by_symbol: [], by_timeframe: [] };
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const { events, total, stats } = queryHistory(searchParams);

  const page = sanitizeInt(searchParams.get("page"), 1, 100000);
  const limit = sanitizeInt(searchParams.get("limit"), 50, 500);

  return NextResponse.json({
    events,
    pagination: { page, limit, total, pages: Math.ceil(total / limit) },
    stats,
  });
}
