import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAppStore } from "../store";

// Mock api-client globally
vi.mock("../api-client", () => ({
  apiRequest: vi.fn(),
  agentsApi: {
    activateKillSwitch: vi.fn(),
    resetKillSwitch: vi.fn(),
  },
}));

import { apiRequest, agentsApi } from "../api-client";
const mockApiRequest = vi.mocked(apiRequest);
const mockActivate = vi.mocked(agentsApi.activateKillSwitch);
const mockReset = vi.mocked(agentsApi.resetKillSwitch);

// ═════════════════════════════════════════════════════════════════════
//  Store — Initial State
// ═════════════════════════════════════════════════════════════════════

describe("Initial state", () => {
  it("has default UI state", () => {
    const state = useAppStore.getState();
    expect(state.sidebarOpen).toBe(true);
    expect(state.killSwitch).toBe(false);
    expect(state.autoTrade).toBe(false);
    expect(state.activeAgents).toEqual([]);
    expect(state.selectedSymbol).toBe("BTC");
    expect(state.selectedExchange).toBe("binance");
    expect(state.notifications).toEqual([]);
  });

  it("has empty data state", () => {
    const state = useAppStore.getState();
    expect(state.agents).toEqual([]);
    expect(state.portfolio).toBeNull();
    expect(state.portfolioRisk).toBeNull();
    expect(state.positions).toEqual([]);
    expect(state.systemHealth).toBeNull();
    expect(state.killSwitchStatus).toBeNull();
  });

  it("has empty real-time state", () => {
    const state = useAppStore.getState();
    expect(state.realtimePrices).toEqual({});
    expect(state.realtimeRegime).toBeNull();
    expect(state.realtimeRisk).toBeNull();
    expect(state.realtimePortfolio).toBeNull();
    expect(state.wsConnected).toBe(false);
  });

  it("has all loading states as default", () => {
    const state = useAppStore.getState();
    const endpoints = ["agents", "portfolio", "risk", "positions", "health", "killSwitch", "market", "strategies"];
    for (const ep of endpoints) {
      const ls = state.loadingStates[ep as keyof typeof state.loadingStates];
      expect(ls.loading).toBe(false);
      expect(ls.error).toBeNull();
      expect(ls.lastUpdated).toBeNull();
    }
  });
});

// ═════════════════════════════════════════════════════════════════════
//  Store — UI Actions
// ═════════════════════════════════════════════════════════════════════

describe("UI actions", () => {
  beforeEach(() => {
    useAppStore.setState({
      sidebarOpen: true,
      killSwitch: false,
      autoTrade: false,
      activeAgents: [],
      selectedSymbol: "BTC",
      selectedExchange: "binance",
      notifications: [],
      loadingStates: {
        agents: { loading: false, error: null, lastUpdated: null },
        portfolio: { loading: false, error: null, lastUpdated: null },
        risk: { loading: false, error: null, lastUpdated: null },
        positions: { loading: false, error: null, lastUpdated: null },
        health: { loading: false, error: null, lastUpdated: null },
        killSwitch: { loading: false, error: null, lastUpdated: null },
        market: { loading: false, error: null, lastUpdated: null },
        strategies: { loading: false, error: null, lastUpdated: null },
      },
    });
    vi.clearAllMocks();
  });

  it("toggleSidebar flips sidebarOpen", () => {
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(false);

    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(true);
  });

  it("toggleKillSwitch calls activate API and flips killSwitch", async () => {
    mockActivate.mockResolvedValueOnce({
      is_active: true,
      activated_at: "2025-01-01T00:00:00Z",
      activation_reason: "MANUAL",
      message: "Kill switch activated. All trading halted.",
    });

    await useAppStore.getState().toggleKillSwitch();
    expect(useAppStore.getState().killSwitch).toBe(true);
    expect(mockActivate).toHaveBeenCalledWith("MANUAL");
  });

  it("toggleKillSwitch calls reset API and flips killSwitch back", async () => {
    useAppStore.setState({ killSwitch: true });

    mockReset.mockResolvedValueOnce({
      is_active: false,
      activated_at: null,
      activation_reason: null,
      message: "Kill switch reset. Trading resumed.",
    });

    await useAppStore.getState().toggleKillSwitch();
    expect(useAppStore.getState().killSwitch).toBe(false);
    expect(mockReset).toHaveBeenCalled();
  });

  it("toggleKillSwitch reverts state on API failure", async () => {
    mockActivate.mockRejectedValueOnce(new Error("Network error"));

    await useAppStore.getState().toggleKillSwitch();
    expect(useAppStore.getState().killSwitch).toBe(false);
    expect(useAppStore.getState().loadingStates.killSwitch.error).toBe("Network error");
  });

  it("toggleAutoTrade flips autoTrade", () => {
    useAppStore.getState().toggleAutoTrade();
    expect(useAppStore.getState().autoTrade).toBe(true);

    useAppStore.getState().toggleAutoTrade();
    expect(useAppStore.getState().autoTrade).toBe(false);
  });

  it("setActiveAgents updates the list", () => {
    useAppStore.getState().setActiveAgents(["trader", "risk"]);
    expect(useAppStore.getState().activeAgents).toEqual(["trader", "risk"]);
  });

  it("setSelectedSymbol updates symbol", () => {
    useAppStore.getState().setSelectedSymbol("ETH");
    expect(useAppStore.getState().selectedSymbol).toBe("ETH");
  });

  it("setSelectedExchange updates exchange", () => {
    useAppStore.getState().setSelectedExchange("ftx");
    expect(useAppStore.getState().selectedExchange).toBe("ftx");
  });
});

// ═════════════════════════════════════════════════════════════════════
//  Store — Notifications
// ═════════════════════════════════════════════════════════════════════

describe("Notifications", () => {
  it("addNotification appends to list", () => {
    useAppStore.getState().addNotification({
      id: "n1",
      type: "info",
      message: "hello",
      timestamp: 100,
    });

    expect(useAppStore.getState().notifications).toHaveLength(1);
    expect(useAppStore.getState().notifications[0].message).toBe("hello");
  });

  it("clearNotifications empties list", () => {
    useAppStore.getState().addNotification({
      id: "n1",
      type: "info",
      message: "test",
      timestamp: 100,
    });
    useAppStore.getState().clearNotifications();
    expect(useAppStore.getState().notifications).toEqual([]);
  });

  it("caps notifications at MAX_NOTIFICATIONS (50)", () => {
    for (let i = 0; i < 60; i++) {
      useAppStore.getState().addNotification({
        id: `n${i}`,
        type: "info",
        message: `msg ${i}`,
        timestamp: i,
      });
    }
    expect(useAppStore.getState().notifications.length).toBeLessThanOrEqual(50);
    // Oldest notification should be removed (first ones start at index 10-11)
    const msgs = useAppStore.getState().notifications.map((n) => n.message);
    expect(msgs).not.toContain("msg 0");
    expect(msgs).toContain("msg 59");
  });
});

// ═════════════════════════════════════════════════════════════════════
//  Store — WebSocket Real-Time Updates
// ═════════════════════════════════════════════════════════════════════

describe("WebSocket real-time actions", () => {
  beforeEach(() => {
    useAppStore.setState({
      realtimePrices: {},
      realtimeRegime: null,
      realtimeRisk: null,
      realtimePortfolio: null,
      wsConnected: false,
      portfolio: null,
      killSwitch: false,
    });
  });

  it("updateRealtimePrices merges new prices", () => {
    useAppStore.getState().updateRealtimePrices({ BTC: { price: 65000, change_24h: 2.5 } });
    expect(useAppStore.getState().realtimePrices.BTC?.price).toBe(65000);

    useAppStore.getState().updateRealtimePrices({ ETH: { price: 3400, change_24h: -1.2 } });
    expect(useAppStore.getState().realtimePrices.BTC?.price).toBe(65000);
    expect(useAppStore.getState().realtimePrices.ETH?.price).toBe(3400);

    // Overwrite existing
    useAppStore.getState().updateRealtimePrices({ BTC: { price: 65500, change_24h: 3.0 } });
    expect(useAppStore.getState().realtimePrices.BTC?.price).toBe(65500);
  });

  it("updateRealtimeRegime sets regime", () => {
    useAppStore.getState().updateRealtimeRegime({ market: "bullish", confidence: 0.85 });
    expect(useAppStore.getState().realtimeRegime?.market).toBe("bullish");
    expect(useAppStore.getState().realtimeRegime?.confidence).toBe(0.85);
  });

  it("updateRealtimeRisk sets risk and auto-updates killSwitch", () => {
    useAppStore.getState().updateRealtimeRisk({ var_95: -5000, drawdown: -2.1, kill_switch: true });
    expect(useAppStore.getState().realtimeRisk?.var_95).toBe(-5000);
    expect(useAppStore.getState().killSwitch).toBe(true);

    useAppStore.getState().updateRealtimeRisk({ var_95: -3000, drawdown: -1.0, kill_switch: false });
    expect(useAppStore.getState().killSwitch).toBe(false);
  });

  it("updateRealtimePortfolio sets portfolio and derived summary", () => {
    useAppStore.getState().updateRealtimePortfolio({
      total_value: 1000000,
      daily_pnl: 15000,
      positions: 7,
    });

    expect(useAppStore.getState().realtimePortfolio?.total_value).toBe(1000000);
    expect(useAppStore.getState().realtimePortfolio?.daily_pnl).toBe(15000);
    expect(useAppStore.getState().realtimePortfolio?.positions).toBe(7);

    // Derived portfolio summary — no fabricated cash split
    expect(useAppStore.getState().portfolio?.total_value).toBe(1000000);
    expect(useAppStore.getState().portfolio?.unrealized_pnl).toBe(15000);
    expect(useAppStore.getState().portfolio?.position_count).toBe(7);
    expect(useAppStore.getState().portfolio?.cash_balance).toBeUndefined();
  });

  it("setWsConnected updates connection status", () => {
    useAppStore.getState().setWsConnected(true);
    expect(useAppStore.getState().wsConnected).toBe(true);

    useAppStore.getState().setWsConnected(false);
    expect(useAppStore.getState().wsConnected).toBe(false);
  });
});

// ═════════════════════════════════════════════════════════════════════
//  Store — API Fetch Actions
// ═════════════════════════════════════════════════════════════════════

describe("fetch actions", () => {
  beforeEach(() => {
    mockApiRequest.mockReset();
    useAppStore.setState({
      agents: [],
      portfolio: null,
      portfolioRisk: null,
      positions: [],
      systemHealth: null,
      loadingStates: {
        agents: { loading: false, error: null, lastUpdated: null },
        portfolio: { loading: false, error: null, lastUpdated: null },
        risk: { loading: false, error: null, lastUpdated: null },
        positions: { loading: false, error: null, lastUpdated: null },
        health: { loading: false, error: null, lastUpdated: null },
        killSwitch: { loading: false, error: null, lastUpdated: null },
        market: { loading: false, error: null, lastUpdated: null },
        strategies: { loading: false, error: null, lastUpdated: null },
      },
      globalLoading: false,
    });
  });

  it("fetchAgents — success updates agents and clears loading", async () => {
    const agentData = {
      agents: [{ name: "Trader", role: "execution", registered: true, status: "active" as const }],
      kill_switch_active: false,
    };
    mockApiRequest.mockResolvedValueOnce(agentData);

    const promise = useAppStore.getState().fetchAgents();
    // Should be loading during fetch
    expect(useAppStore.getState().loadingStates.agents.loading).toBe(true);
    await promise;

    expect(useAppStore.getState().agents).toEqual(agentData.agents);
    expect(useAppStore.getState().killSwitch).toBe(false);
    expect(useAppStore.getState().loadingStates.agents.loading).toBe(false);
    expect(useAppStore.getState().loadingStates.agents.error).toBeNull();
    expect(useAppStore.getState().loadingStates.agents.lastUpdated).not.toBeNull();
  });

  it("fetchAgents — failure sets error state", async () => {
    mockApiRequest.mockRejectedValueOnce(new Error("Connection refused"));

    await useAppStore.getState().fetchAgents();

    expect(useAppStore.getState().agents).toEqual([]);
    expect(useAppStore.getState().loadingStates.agents.loading).toBe(false);
    expect(useAppStore.getState().loadingStates.agents.error).toBe("Connection refused");
  });

  it("fetchPortfolio — success updates portfolio", async () => {
    const portfolioData = {
      total_value: 500000,
      unrealized_pnl: 25000,
      position_count: 5,
      cash_balance: 100000,
    };
    mockApiRequest.mockResolvedValueOnce(portfolioData);

    await useAppStore.getState().fetchPortfolio();

    expect(useAppStore.getState().portfolio?.total_value).toBe(500000);
    expect(useAppStore.getState().portfolio?.unrealized_pnl).toBe(25000);
    expect(useAppStore.getState().loadingStates.portfolio.loading).toBe(false);
  });

  it("fetchPortfolioRisk — success updates risk", async () => {
    const riskData = {
      var_95: -5000,
      max_drawdown: -10,
      current_drawdown: -2.1,
      daily_pnl_pct: 0.5,
      risk_status: "low",
    };
    mockApiRequest.mockResolvedValueOnce(riskData);

    await useAppStore.getState().fetchPortfolioRisk();

    expect(useAppStore.getState().portfolioRisk?.var_95).toBe(-5000);
    expect(useAppStore.getState().portfolioRisk?.risk_status).toBe("low");
  });

  it("fetchPositions — success updates positions", async () => {
    const position = { ticker: "BTC", amount: 2.5, avg_price: 65000, current_price: 67000, pnl: 5000 };
    mockApiRequest.mockResolvedValueOnce({ positions: [position] });

    await useAppStore.getState().fetchPositions();

    expect(useAppStore.getState().positions).toHaveLength(1);
    expect(useAppStore.getState().positions[0].ticker).toBe("BTC");
  });

  it("fetchHealth — success updates system health", async () => {
    mockApiRequest.mockResolvedValueOnce({ status: "ok", service: "api" });

    await useAppStore.getState().fetchHealth();

    expect(useAppStore.getState().systemHealth?.status).toBe("ok");
    expect(useAppStore.getState().systemHealth?.service).toBe("api");
  });

  it("fetchKillSwitchStatus — success updates kill switch", async () => {
    mockApiRequest.mockResolvedValueOnce({
      is_active: true,
      activated_at: "2026-07-13T00:00:00Z",
      activation_reason: "drawdown limit",
      message: "Auto-halt",
    });

    await useAppStore.getState().fetchKillSwitchStatus();

    expect(useAppStore.getState().killSwitch).toBe(true);
    expect(useAppStore.getState().killSwitchStatus?.is_active).toBe(true);
    expect(useAppStore.getState().killSwitchStatus?.activation_reason).toBe("drawdown limit");
  });

  it("refreshAll — runs all fetches in parallel and clears global loading", async () => {
    mockApiRequest
      .mockResolvedValueOnce({ agents: [], kill_switch_active: false })
      .mockResolvedValueOnce({ total_value: 0, unrealized_pnl: 0, position_count: 0, cash_balance: 0 })
      .mockResolvedValueOnce({ var_95: 0, max_drawdown: 0, current_drawdown: 0, daily_pnl_pct: 0, risk_status: "unknown" })
      .mockResolvedValueOnce({ positions: [] })
      .mockResolvedValueOnce({ status: "ok", service: "api" })
      .mockResolvedValueOnce({ is_active: false, activated_at: null, activation_reason: null, message: "ok" });

    await useAppStore.getState().refreshAll();

    expect(useAppStore.getState().globalLoading).toBe(false);
    expect(mockApiRequest).toHaveBeenCalledTimes(6);
  });
});
