import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const WORKTREE = process.cwd();

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

function queryHistory(params: URLSearchParams): { events: TradeEvent[]; total: number; stats: TradeStats } {
  // Read from SQLite via Python subprocess
  try {
    const { execSync } = require("child_process");
    const page = params.get("page") || "1";
    const limit = params.get("limit") || "50";
    const symbol = params.get("symbol") || "";
    const timeframe = params.get("timeframe") || "";
    const traded = params.get("traded") || "";

    const pyCmd = `
import sys; sys.path.insert(0, '${WORKTREE.replace(/\\/g, "\\\\")}')
from quant_nanggroe.engine.trade_history import get_trade_history
h = get_trade_history()
events = h.query(symbol="${symbol}" or None, timeframe="${timeframe}" or None, traded_only=${traded === "1"}, limit=${limit}, offset=(${page} - 1) * ${limit})
total = h.count(symbol="${symbol}" or None, timeframe="${timeframe}" or None, traded_only=${traded === "1"})
import json
print(json.dumps({"events": events, "total": total}))
`.trim();

    const result = execSync(`set "PYTHONPATH=" && C:\\Python314\\python.exe -c "${pyCmd.replace(/"/g, '\\"')}"`, {
      cwd: WORKTREE,
      encoding: "utf8",
      timeout: 10000,
    });

    const parsed = JSON.parse(result.trim());
    const stats = getStats();
    return { events: parsed.events, total: parsed.total, stats };
  } catch {
    return { events: [], total: 0, stats: { total: 0, trades: 0, signals: 0, errors: 0, last_24h: 0, by_symbol: [], by_timeframe: [] } };
  }
}

function getStats(): TradeStats {
  try {
    const { execSync } = require("child_process");
    const pyCmd = `
import sys; sys.path.insert(0, '${WORKTREE.replace(/\\/g, "\\\\")}')
from quant_nanggroe.engine.trade_history import get_trade_history
import json
print(json.dumps(get_trade_history().stats()))
`.trim();

    const result = execSync(`set "PYTHONPATH=" && C:\\Python314\\python.exe -c "${pyCmd.replace(/"/g, '\\"')}"`, {
      cwd: WORKTREE,
      encoding: "utf8",
      timeout: 10000,
    });

    return JSON.parse(result.trim());
  } catch {
    return { total: 0, trades: 0, signals: 0, errors: 0, last_24h: 0, by_symbol: [], by_timeframe: [] };
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const { events, total, stats } = queryHistory(searchParams);

  const page = parseInt(searchParams.get("page") || "1", 10);
  const limit = parseInt(searchParams.get("limit") || "50", 10);

  return NextResponse.json({
    events,
    pagination: { page, limit, total, pages: Math.ceil(total / limit) },
    stats,
  });
}
