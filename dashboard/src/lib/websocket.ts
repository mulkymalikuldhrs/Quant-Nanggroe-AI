"use client";

import { useEffect, useRef, useState } from "react";

interface UseWebSocketOptions {
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const {
    autoReconnect = true,
    reconnectInterval = 3000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const onMessageRef = useRef(options.onMessage);
  const onConnectRef = useRef(options.onConnect);
  const onDisconnectRef = useRef(options.onDisconnect);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown>(null);

  useEffect(() => {
    onMessageRef.current = options.onMessage;
    onConnectRef.current = options.onConnect;
    onDisconnectRef.current = options.onDisconnect;
  });

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      try {
        const ws = new WebSocket(url);

        ws.onopen = () => {
          if (!cancelled) {
            setIsConnected(true);
            onConnectRef.current?.();
          }
        };

        ws.onmessage = (event) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(event.data);
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
            reconnectTimerRef.current = setTimeout(() => {
              connect();
            }, reconnectInterval);
          }
        };

        ws.onerror = () => {
          ws.close();
        };

        wsRef.current = ws;
      } catch (error) {
        console.error("WebSocket connection error:", error);
        if (autoReconnect && !cancelled) {
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
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
  }, [url, autoReconnect, reconnectInterval]);

  const send = (data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  return { isConnected, lastMessage, send };
}

export function useRealtimeData() {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/ws";
  const { isConnected, lastMessage, send } = useWebSocket(wsUrl, {
    autoReconnect: true,
    reconnectInterval: 5000,
  });

  return { isConnected, lastMessage, send };
}
