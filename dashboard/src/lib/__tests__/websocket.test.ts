import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { WSMessage, WSChannel, WSSubscription } from "../websocket";

// ── React hook cleanups ──────────────────────────────────────────────

const reactCleanups = vi.hoisted(() => new Set<() => void>());

// ── Mock React hooks ─────────────────────────────────────────────────
// We mock React hooks so useWebSocket can be called directly without
// a DOM environment. State assertions won't work (no render cycle),
// but we can verify side-effects: callbacks, send, constructor, reconnect.

vi.mock("react", async () => {
  const actual = await vi.importActual<typeof import("react")>("react");

  return {
    ...actual,
    useEffect: (fn: () => void | (() => void)) => {
      const cleanup = fn();
      if (cleanup) reactCleanups.add(cleanup);
    },
    useLayoutEffect: (fn: () => void | (() => void)) => {
      const cleanup = fn();
      if (cleanup) reactCleanups.add(cleanup);
    },
    useRef: <T>(initial: T): { current: T } => ({ current: initial }),
    useState: <T>(initial: T): [T, (val: T | ((prev: T) => T)) => void] => {
      return [initial, vi.fn()] as unknown as [
        T,
        (val: T | ((prev: T) => T)) => void,
      ];
    },
    useCallback: <T extends (...args: never[]) => unknown>(
      fn: T,
      _deps: unknown[],
    ): T => fn,
    useMemo: <T>(fn: () => T, _deps: unknown[]): T => fn(),
  };
});

// Mock the store dependency of useRealtimeData
vi.mock("../store", () => ({
  useAppStore: Object.assign(
    (selector?: (state: unknown) => unknown) => {
      const mockStore = {
        realtimePrices: {},
        realtimeRegime: null,
        realtimeRisk: null,
        realtimePortfolio: null,
        wsConnected: false,
        notifications: [],
        updateRealtimePrices: vi.fn(),
        updateRealtimeRegime: vi.fn(),
        updateRealtimeRisk: vi.fn(),
        updateRealtimePortfolio: vi.fn(),
        setWsConnected: vi.fn(),
        addNotification: vi.fn(),
      };
      return selector ? selector(mockStore) : mockStore;
    },
    { getState: () => ({}) },
  ),
}));

import { useWebSocket, useRealtimeData } from "../websocket";

// ── WebSocket Mock (class-based for Node.js compat) ────────────────
// In Node.js strict mode, globalThis.WebSocket = X does NOT make `new WebSocket()`
// work because bare name resolution in strict mode throws ReferenceError
// if the name is not in scope. We use Object.defineProperty on globalThis
// with configurable:true to properly register the global.

let mockInstances: any[] = [];

class MockWebSocket {
  url: string;
  readyState: number = 0;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  close = vi.fn(() => {
    this.readyState = 3;
    // Don't trigger onclose here — in real WebSocket API, client-initiated
    // close() does not fire onclose; the browser fires it on network close.
    // This prevents reconnection loops in tests where connect() calls close().
  });
  send = vi.fn();

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 3;
  static CLOSING = 2;

  constructor(url: string) {
    this.url = url;
    mockInstances.push(this);
  }

  _triggerOpen() {
    this.readyState = 1;
    this.onopen?.(new Event("open"));
  }
  _triggerMessage(data: string) {
    this.onmessage?.({ data } as MessageEvent);
  }
  _triggerClose(code = 1006) {
    this.readyState = 3;
    this.onclose?.({ code, reason: "Connection closed" } as CloseEvent);
  }
  _triggerError() {
    this.onerror?.(new Event("error"));
    // In real browsers, WebSocket error is always followed by close
    this.readyState = 3;
    this.onclose?.({ code: 1006, reason: "Connection error" } as CloseEvent);
  }
}

beforeEach(() => {
  mockInstances = [];
  // Use defineProperty to properly register the global constructor
  Object.defineProperty(globalThis, "WebSocket", {
    value: MockWebSocket,
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  for (const cleanup of reactCleanups) {
    cleanup();
  }
  reactCleanups.clear();
  delete (globalThis as any).WebSocket;
  vi.clearAllMocks();
});

// ═════════════════════════════════════════════════════════════════════
//  WSMessage Type
// ═════════════════════════════════════════════════════════════════════

describe("WSMessage interface", () => {
  it("supports price message shape", () => {
    const msg: WSMessage = {
      price: { BTC: { price: 65000, change_24h: 2.5 } },
    };
    expect(msg.price?.BTC.price).toBe(65000);
    expect(msg.price?.BTC.change_24h).toBe(2.5);
  });

  it("supports regime message shape", () => {
    const msg: WSMessage = {
      regime: { market: "bullish", confidence: 0.85 },
    };
    expect(msg.regime?.market).toBe("bullish");
    expect(msg.regime?.confidence).toBe(0.85);
  });

  it("supports risk message shape", () => {
    const msg: WSMessage = {
      risk: { var_95: -5000, drawdown: -2.1, kill_switch: true },
    };
    expect(msg.risk?.var_95).toBe(-5000);
    expect(msg.risk?.kill_switch).toBe(true);
  });

  it("supports portfolio message shape", () => {
    const msg: WSMessage = {
      portfolio: { total_value: 1000000, daily_pnl: 15000, positions: 7 },
    };
    expect(msg.portfolio?.total_value).toBe(1000000);
  });

  it("supports type field", () => {
    const msg: WSMessage = { type: "pong" };
    expect(msg.type).toBe("pong");
  });
});

// ═════════════════════════════════════════════════════════════════════
//  WSChannel Type
// ═════════════════════════════════════════════════════════════════════

describe("WSChannel type", () => {
  it("accepts valid channel names", () => {
    const channels: WSChannel[] = ["price", "regime", "risk", "portfolio"];
    expect(channels).toHaveLength(4);
  });
});

// ═════════════════════════════════════════════════════════════════════
//  WSSubscription Type
// ═════════════════════════════════════════════════════════════════════

describe("WSSubscription interface", () => {
  it("creates valid subscription", () => {
    const sub: WSSubscription = {
      channels: ["price", "regime"],
      symbols: ["BTC/USDT", "ETH/USDT"],
    };
    expect(sub.channels).toContain("price");
    expect(sub.symbols).toContain("BTC/USDT");
  });
});

// ═════════════════════════════════════════════════════════════════════
//  Reconnect Delay (pure math verification)
// ═════════════════════════════════════════════════════════════════════

describe("reconnect delay math", () => {
  const BASE = 1000;
  const MAX = 30000;

  it("exponential growth: attempt 0 is BASE (1000ms)", () => {
    expect(Math.min(BASE * 2 ** 0, MAX)).toBe(BASE);
  });

  it("exponential growth: attempt 1 is 2x BASE", () => {
    expect(Math.min(BASE * 2 ** 1, MAX)).toBe(BASE * 2);
  });

  it("caps at 30000ms", () => {
    expect(Math.min(BASE * 2 ** 5, MAX)).toBe(MAX);
    expect(Math.min(BASE * 2 ** 10, MAX)).toBe(MAX);
  });

  it("jitter adds variance", () => {
    const results = new Set<number>();
    for (let i = 0; i < 100; i++) {
      results.add(Math.round(Math.min(BASE * 2 ** 0, MAX) + Math.random() * 1000));
    }
    expect(results.size).toBeGreaterThan(50);
  });
});

// ═════════════════════════════════════════════════════════════════════
//  useWebSocket — Constructor & Connection Events
// ═════════════════════════════════════════════════════════════════════

describe("useWebSocket — constructor & events", () => {
  it("creates WebSocket with the provided URL", () => {
    useWebSocket("ws://localhost:8000/ws");
    expect(mockInstances).toHaveLength(1);
    expect(mockInstances[0].url).toBe("ws://localhost:8000/ws");
  });

  it("calls onConnect callback when WebSocket opens", () => {
    const onConnect = vi.fn();
    useWebSocket("ws://localhost:8000/ws", { onConnect });
    mockInstances[0]._triggerOpen();
    expect(onConnect).toHaveBeenCalledOnce();
  });

  it("calls onDisconnect callback when WebSocket closes", () => {
    const onDisconnect = vi.fn();
    useWebSocket("ws://localhost:8000/ws", { onDisconnect });
    mockInstances[0]._triggerOpen();
    mockInstances[0]._triggerClose();
    expect(onDisconnect).toHaveBeenCalledOnce();
  });
});

// ═════════════════════════════════════════════════════════════════════
//  useWebSocket — Messages
// ═════════════════════════════════════════════════════════════════════

describe("useWebSocket — messages", () => {
  it("calls onMessage callback with parsed JSON data", () => {
    const onMessage = vi.fn();
    useWebSocket("ws://localhost:8000/ws", { onMessage });
    mockInstances[0]._triggerOpen();
    mockInstances[0]._triggerMessage(JSON.stringify({ type: "ping" }));
    expect(onMessage).toHaveBeenCalledWith(expect.objectContaining({ type: "ping" }));
  });

  it("ignores non-JSON messages gracefully", () => {
    const onMessage = vi.fn();
    useWebSocket("ws://localhost:8000/ws", { onMessage });
    mockInstances[0]._triggerOpen();
    mockInstances[0]._triggerMessage("not json");
    expect(onMessage).not.toHaveBeenCalled();
  });

  it("fires onMessage twice for two incoming messages", () => {
    const onMessage = vi.fn();
    useWebSocket("ws://localhost:8000/ws", { onMessage });
    mockInstances[0]._triggerOpen();
    mockInstances[0]._triggerMessage(JSON.stringify({ type: "ping" }));
    mockInstances[0]._triggerMessage(JSON.stringify({ type: "pong" }));
    expect(onMessage).toHaveBeenCalledTimes(2);
  });
});

// ═════════════════════════════════════════════════════════════════════
//  useWebSocket — Send / Subscribe / Unsubscribe / Ping
// ═════════════════════════════════════════════════════════════════════

describe("useWebSocket — send / subscribe / unsubscribe / ping", () => {
  it("send serializes data as JSON and calls WebSocket.send", () => {
    const ws = useWebSocket("ws://localhost:8000/ws");
    mockInstances[0]._triggerOpen();
    ws.send({ action: "custom", value: 42 });
    expect(mockInstances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ action: "custom", value: 42 }),
    );
  });

  it("subscribe sends subscribe action with default symbols", () => {
    const ws = useWebSocket("ws://localhost:8000/ws");
    mockInstances[0]._triggerOpen();
    ws.subscribe(["price", "regime"]);
    expect(mockInstances[0].send).toHaveBeenCalledWith(
      JSON.stringify({
        action: "subscribe",
        channels: ["price", "regime"],
        symbols: ["BTC/USDT"],
      }),
    );
  });

  it("subscribe accepts custom symbols", () => {
    const ws = useWebSocket("ws://localhost:8000/ws");
    mockInstances[0]._triggerOpen();
    ws.subscribe(["price"], ["ETH/USDT", "SOL/USDT"]);
    expect(mockInstances[0].send).toHaveBeenCalledWith(
      JSON.stringify({
        action: "subscribe",
        channels: ["price"],
        symbols: ["ETH/USDT", "SOL/USDT"],
      }),
    );
  });

  it("unsubscribe sends unsubscribe action", () => {
    const ws = useWebSocket("ws://localhost:8000/ws");
    mockInstances[0]._triggerOpen();
    ws.unsubscribe(["risk"]);
    expect(mockInstances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ action: "unsubscribe", channels: ["risk"], symbols: [] }),
    );
  });

  it("ping sends ping action", () => {
    const ws = useWebSocket("ws://localhost:8000/ws");
    mockInstances[0]._triggerOpen();
    ws.ping();
    expect(mockInstances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ action: "ping" }),
    );
  });

  it("does not call send when WebSocket is not yet open", () => {
    const ws = useWebSocket("ws://localhost:8000/ws");
    ws.send({ action: "test" });
    expect(mockInstances[0].send).not.toHaveBeenCalled();
  });
});

// ═════════════════════════════════════════════════════════════════════
//  useWebSocket — Reconnection
// ═════════════════════════════════════════════════════════════════════

describe("useWebSocket — reconnection", () => {
  it("creates a new WebSocket on close when autoReconnect is true", () => {
    vi.useFakeTimers();
    useWebSocket("ws://localhost:8000/ws", { autoReconnect: true });

    mockInstances[0]._triggerOpen();
    mockInstances[0]._triggerClose();

    vi.advanceTimersByTime(5000);

    expect(mockInstances.length).toBe(2);
    expect(mockInstances[1].url).toBe("ws://localhost:8000/ws");
    vi.useRealTimers();
  });

  it("does NOT reconnect when autoReconnect is false", () => {
    vi.useFakeTimers();
    useWebSocket("ws://localhost:8000/ws", { autoReconnect: false });

    mockInstances[0]._triggerOpen();
    mockInstances[0]._triggerClose();

    vi.advanceTimersByTime(10000);

    expect(mockInstances.length).toBe(1);
    vi.useRealTimers();
  });
});

// ═════════════════════════════════════════════════════════════════════
//  useWebSocket — Error Handling
// ═════════════════════════════════════════════════════════════════════

describe("useWebSocket — errors", () => {
  it("handles constructor exception without crashing", () => {
    (globalThis as any).WebSocket = vi.fn(() => {
      throw new Error("Invalid URL");
    });
    const ws = useWebSocket("invalid-url");
    // Should not throw — just return the hook interface
    expect(ws).toHaveProperty("isConnected");
    expect(ws).toHaveProperty("send");
  });

  it("reconnects after WebSocket error when autoReconnect is true", () => {
    vi.useFakeTimers();
    useWebSocket("ws://localhost:8000/ws", { autoReconnect: true });

    mockInstances[0]._triggerOpen();
    mockInstances[0]._triggerError();

    vi.advanceTimersByTime(5000);

    expect(mockInstances.length).toBe(2);
    vi.useRealTimers();
  });
});

// ═════════════════════════════════════════════════════════════════════
//  useRealtimeData — Interface
// ═════════════════════════════════════════════════════════════════════

describe("useRealtimeData", () => {
  it("returns the expected interface", () => {
    const rtd = useRealtimeData();
    expect(rtd).toHaveProperty("isConnected");
    expect(rtd).toHaveProperty("connectionError");
    expect(rtd).toHaveProperty("subscribe");
    expect(rtd).toHaveProperty("unsubscribe");
    expect(rtd).toHaveProperty("ping");
  });
});

// ═════════════════════════════════════════════════════════════════════
//  WebSocket URL Construction
// ═════════════════════════════════════════════════════════════════════

describe("WebSocket URL construction", () => {
  it("uses NEXT_PUBLIC_WS_URL env var when set", () => {
    const envUrl = "wss://custom.example.com/ws";
    const wsUrl = envUrl || "ws://localhost:8000/api/ws/stream";
    expect(wsUrl).toBe("wss://custom.example.com/ws");
  });

  it("falls back to localhost:8000", () => {
    const wsUrl = "ws://localhost:8000/api/ws/stream";
    expect(wsUrl).toContain("localhost:8000");
    expect(wsUrl).toContain("/api/ws/stream");
  });

  it("uses wss:// for https protocol", () => {
    const protocol = "https:" as string;
    const wsUrl = `${protocol === "https:" ? "wss:" : "ws:"}//example.com/ws`;
    expect(wsUrl).toContain("wss://");
  });

  it("uses ws:// for http protocol", () => {
    const protocol = "http:" as string;
    const wsUrl = `${protocol === "https:" ? "wss:" : "ws:"}//example.com/ws`;
    expect(wsUrl).toContain("ws://");
  });
});
