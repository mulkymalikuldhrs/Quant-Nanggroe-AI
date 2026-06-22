"use client";

import { useEffect, useRef, useState } from "react";
import { useAppStore } from "./store";

interface UseWebSocketOptions {
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const {
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 20,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const onMessageRef = useRef(options.onMessage);
  const onConnectRef = useRef(options.onConnect);
  const onDisconnectRef = useRef(options.onDisconnect);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const reconnectAttemptsRef = useRef(0);

  useEffect(() => {
    onMessageRef.current = options.onMessage;
    onConnectRef.current = options.onConnect;
    onDisconnectRef.current = options.onDisconnect;
  });

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      if (reconnectAttemptsRef.current >= maxReconnectAttempts) return;
      try {
        const ws = new WebSocket(url);

        ws.onopen = () => {
          if (!cancelled) {
            setIsConnected(true);
            reconnectAttemptsRef.current = 0;
            onConnectRef.current?.();
          }
        };

        ws.onmessage = (event) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === "trade_update" || data.type === "risk_alert" || data.type === "position_change") {
              const addNotification = useAppStore.getState().addNotification;
              addNotification({
                id: `${data.type}-${Date.now()}`,
                type: data.type === "risk_alert" ? "warning" : "info",
                message: `${data.type}: ${JSON.stringify(data.data)}`,
                timestamp: Date.now(),
              });
            }
            setLastMessage(data);
            onMessageRef.current?.(data);
          } catch {
            setLastMessage(event.data);
            onMessageRef.current?.(event.data);
          }
        };

        ws.onclose = () => {
          if (cancelled) return;
          setIsConnected(false);
          onDisconnectRef.current?.();
          if (autoReconnect) {
            reconnectAttemptsRef.current += 1;
            const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1), 30000);
            reconnectTimerRef.current = setTimeout(() => {
              connect();
            }, delay);
          }
        };

        ws.onerror = () => {
          ws.close();
        };

        wsRef.current = ws;
      } catch (error) {
        console.error("WebSocket connection error:", error);
        if (autoReconnect && !cancelled) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1), 30000);
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, delay);
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
  }, [url, autoReconnect, reconnectInterval, maxReconnectAttempts]);

  const send = (data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  return { isConnected, lastMessage, send };
}

export function useRealtimeData() {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/trading";
  const { isConnected, lastMessage, send } = useWebSocket(wsUrl, {
    autoReconnect: true,
    reconnectInterval: 5000,
    maxReconnectAttempts: 20,
  });

  return { isConnected, lastMessage, send };
}
