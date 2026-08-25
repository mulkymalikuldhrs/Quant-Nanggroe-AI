"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAppStore } from "./store";
import { apiRequest } from "./api-client";

// ── Types ───────────────────────────────────────────────────────────

export type WSChannel = "price" | "regime" | "risk" | "portfolio" | "candles";

export interface WSSubscription {
  channels: WSChannel[];
  symbols: string[];
}

export interface CandleCloseEvent {
  id: string;
  type: "trade" | "signal" | "system";
  symbol: string;
  timeframe: string;
  signal: string;
  confidence: number;
  traded: boolean;
  duration_ms?: number;
  error?: string;
  timestamp: string;
}

export interface WSMessage {
  type?: string;
  timestamp?: string;
  price?: Record<string, { price: number; change_24h: number }>;
  regime?: { market: string; confidence: number };
  risk?: { var_95: number; drawdown: number; kill_switch: boolean };
  portfolio?: { total_value: number; daily_pnl: number; positions: number };
  data?: CandleCloseEvent;
  [key: string]: unknown;
}

interface UseWebSocketOptions {
  onMessage?: (data: WSMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  maxReconnectInterval?: number;
}

// ── Reconnect with exponential backoff ────────────────────────────

const BASE_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 30000;
const JITTER_MAX = 1000;

function getReconnectDelay(attempt: number): number {
  const exponential = Math.min(
    BASE_RECONNECT_MS * Math.pow(2, attempt),
    MAX_RECONNECT_MS,
  );
  const jitter = Math.random() * JITTER_MAX;
  return exponential + jitter;
}

// ── WS URL + JWT auth ─────────────────────────────────────────────
// Backend closes with code 4001 unless ?token= carries a valid JWT.

export function getWsBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_WS_URL ||
    (typeof window !== "undefined"
      ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.hostname}:8000/api/ws/stream`
      : "ws://localhost:8000/api/ws/stream")
  );
}

interface WsToken {
  token: string;
  expiresAtMs: number;
}

let wsTokenCache: WsToken | null = null;

export function invalidateWsToken(): void {
  wsTokenCache = null;
}

async function fetchWsToken(): Promise<WsToken> {
  const data = await apiRequest<{ token: string; expires_at: number }>(
    "/api/auth/token",
    { method: "POST", deduplicate: false },
  );
  wsTokenCache = { token: data.token, expiresAtMs: data.expires_at * 1000 };
  return wsTokenCache;
}

// Single URL builder shared by every WS consumer (dashboard, candle-monitor).
export async function buildWsUrl(base?: string): Promise<string> {
  const baseUrl = base ?? getWsBaseUrl();
  if (!wsTokenCache || Date.now() >= wsTokenCache.expiresAtMs - 60_000) {
    await fetchWsToken();
  }
  if (!wsTokenCache) throw new Error("WS auth token unavailable");
  const sep = baseUrl.includes("?") ? "&" : "?";
  return `${baseUrl}${sep}token=${encodeURIComponent(wsTokenCache.token)}`;
}

// ── WebSocket Hook ─────────────────────────────────────────────────

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {},
) {
  const {
    autoReconnect = true,
    maxReconnectInterval = MAX_RECONNECT_MS,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const onMessageRef = useRef(options.onMessage);
  const onConnectRef = useRef(options.onConnect);
  const onDisconnectRef = useRef(options.onDisconnect);

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Keep callback refs current
  useEffect(() => {
    onMessageRef.current = options.onMessage;
    onConnectRef.current = options.onConnect;
    onDisconnectRef.current = options.onDisconnect;
  });

  // Track subscriptions for state recovery on reconnect
  const subscribedChannels = useRef<{ channels: WSChannel[]; symbols: string[] } | null>(null);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      setConnectionError(null);

      try {
        const ws = new WebSocket(url);

        ws.onopen = () => {
          if (cancelled) return;
          setIsConnected(true);
          setConnectionError(null);
          reconnectAttemptRef.current = 0;
          onConnectRef.current?.();

          // State recovery: re-subscribe previous channels on reconnect
          if (subscribedChannels.current) {
            send({
              action: "subscribe",
              channels: subscribedChannels.current.channels,
              symbols: subscribedChannels.current.symbols,
            });
          }
        };

        ws.onmessage = (event) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(event.data) as WSMessage;

            // Respond to server heartbeat pings
            if (data.type === "ping") {
              ws.send(JSON.stringify({ action: "pong" }));
              return;
            }

            setLastMessage(data);
            onMessageRef.current?.(data);
          } catch {
            // Ignore non-JSON messages
          }
        };

        ws.onclose = (event) => {
          if (cancelled) return;
          setIsConnected(false);
          onDisconnectRef.current?.();

          // Auth rejection (missing/expired/invalid JWT) — reconnecting can
          // never succeed with the same token. Stop permanently.
          if (event.code === 4001 || event.code === 4003) {
            invalidateWsToken();
            setConnectionError("WS authentication failed");
            return;
          }

          if (autoReconnect && !cancelled) {
            const delay = getReconnectDelay(reconnectAttemptRef.current);
            reconnectAttemptRef.current += 1;
            setConnectionError(
              `Disconnected (code: ${event.code}). Reconnecting in ${Math.round(delay / 1000)}s...`,
            );
            reconnectTimerRef.current = setTimeout(connect, delay);
          }
        };

        ws.onerror = () => {
          if (cancelled) return;
          setConnectionError("WebSocket connection error");
          ws.close();
        };

        wsRef.current = ws;
      } catch (error) {
        if (cancelled) return;
        const msg = error instanceof Error ? error.message : "Unknown error";
        setConnectionError(`Connection failed: ${msg}`);
        if (autoReconnect && !cancelled) {
          const delay = getReconnectDelay(reconnectAttemptRef.current);
          reconnectAttemptRef.current += 1;
          reconnectTimerRef.current = setTimeout(connect, delay);
        }
      }
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      wsRef.current?.close();
    };
  }, [url, autoReconnect, maxReconnectInterval]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const subscribe = useCallback(
    (channels: WSChannel[], symbols: string[] = ["BTC/USDT"]) => {
      subscribedChannels.current = { channels, symbols };
      send({
        action: "subscribe",
        channels,
        symbols,
      });
    },
    [send],
  );

  const unsubscribe = useCallback(
    (channels: WSChannel[], symbols: string[] = []) => {
      if (subscribedChannels.current) {
        subscribedChannels.current = {
          channels: subscribedChannels.current.channels.filter(c => !channels.includes(c)),
          symbols: subscribedChannels.current.symbols.filter(s => !symbols.includes(s)),
        };
      }
      send({
        action: "unsubscribe",
        channels,
        symbols,
      });
    },
    [send],
  );

  const ping = useCallback(() => {
    send({ action: "ping" });
  }, [send]);

  return {
    isConnected,
    lastMessage,
    connectionError,
    send,
    subscribe,
    unsubscribe,
    ping,
  };
}

// ── Pre-configured Hook for QNA Dashboard ─────────────────────────

export function useRealtimeData() {
  const [wsUrl, setWsUrl] = useState("");

  // Resolve JWT-authenticated WS URL once; retry while backend is down.
  useEffect(() => {
    let cancelled = false;
    let timer: NodeJS.Timeout | null = null;
    const resolve = () => {
      buildWsUrl()
        .then((u) => {
          if (!cancelled) setWsUrl(u);
        })
        .catch(() => {
          if (!cancelled) timer = setTimeout(resolve, 5000);
        });
    };
    resolve();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  const addNotification = useAppStore((s) => s.addNotification);

  const onMessage = useCallback(
    (data: WSMessage) => {
      const store = useAppStore.getState();

      // Update store with real-time data
      if (data.price) {
        store.updateRealtimePrices(data.price);
      }
      if (data.regime) {
        store.updateRealtimeRegime(data.regime);
      }
      if (data.risk) {
        store.updateRealtimeRisk(data.risk);
      }
      if (data.portfolio) {
        store.updateRealtimePortfolio(data.portfolio);
      }

      // Auto-subscribe to channels when connecting
      if (data.type === "pong") {
        // Already subscribed — no action needed
      }
    },
    [addNotification],
  );

  const onConnect = useCallback(() => {
    useAppStore.getState().setWsConnected(true);
    addNotification({
      id: `ws-connect-${Date.now()}`,
      type: "success",
      message: "Real-time connection established",
      timestamp: Date.now(),
    });
  }, [addNotification]);

  const onDisconnect = useCallback(() => {
    useAppStore.getState().setWsConnected(false);
    addNotification({
      id: `ws-disconnect-${Date.now()}`,
      type: "warning",
      message: "Real-time connection lost — reconnecting...",
      timestamp: Date.now(),
    });
  }, [addNotification]);

  const ws = useWebSocket(wsUrl, {
    onMessage,
    onConnect,
    onDisconnect,
    autoReconnect: true,
  });

  // Subscribe to all channels when connected
  const prevConnected = useRef(false);
  useEffect(() => {
    if (ws.isConnected && !prevConnected.current) {
      // Subscribe to all available channels
      ws.subscribe(["price", "regime", "risk", "portfolio"], ["BTC/USDT", "ETH/USDT"]);
    }
    prevConnected.current = ws.isConnected;
  }, [ws.isConnected, ws.subscribe]);

  return {
    isConnected: ws.isConnected,
    lastMessage: ws.lastMessage,
    connectionError: ws.connectionError,
    subscribe: ws.subscribe,
    unsubscribe: ws.unsubscribe,
    ping: ws.ping,
  };
}
