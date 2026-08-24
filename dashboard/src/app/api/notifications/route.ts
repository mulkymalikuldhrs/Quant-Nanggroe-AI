import { NextResponse } from "next/server";
import { readFileSync } from "node:fs";

export const dynamic = "force-dynamic";

const WORKTREE = process.cwd();

function read(path: string): string | null {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return null;
  }
}

interface Notification {
  id: string;
  type: "trade" | "signal" | "alert" | "system";
  symbol?: string;
  timeframe?: string;
  message: string;
  signal?: string;
  confidence?: number;
  traded?: boolean;
  timestamp: string;
}

function getNotifications(): Notification[] {
  const stateFile = `${WORKTREE}/data/notifications.json`;
  const raw = read(stateFile);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : parsed.notifications || [];
    } catch {
      return [];
    }
  }
  return [];
}

function getNotificationStats(notifications: Notification[]) {
  const stats = {
    total: notifications.length,
    trades: 0,
    signals: 0,
    alerts: 0,
    system: 0,
    last_hour: 0,
    last_24h: 0,
  };

  const now = Date.now();
  const hourAgo = now - 3600000;
  const dayAgo = now - 86400000;

  for (const n of notifications) {
    if (n.type === "trade") stats.trades++;
    else if (n.type === "signal") stats.signals++;
    else if (n.type === "alert") stats.alerts++;
    else if (n.type === "system") stats.system++;

    const ts = new Date(n.timestamp).getTime();
    if (ts > hourAgo) stats.last_hour++;
    if (ts > dayAgo) stats.last_24h++;
  }

  return stats;
}

export async function GET() {
  const notifications = getNotifications();
  return NextResponse.json({
    notifications: notifications.slice(-200),
    stats: getNotificationStats(notifications),
  });
}
