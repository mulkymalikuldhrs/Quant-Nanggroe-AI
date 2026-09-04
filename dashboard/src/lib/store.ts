import { create } from "zustand";
import { apiRequest, agentsApi } from "./api-client";

// ── Types ───────────────────────────────────────────────────────────

interface AgentInfo {
  name: string;
  role: string;
  registered: boolean;
  status: "active" | "idle" | "error" | "offline";
}

interface PositionInfo {
  ticker: string;
  amount: number;
  avg_price: number;
  current_price: number;
  pnl: number;
}

interface PortfolioSummary {
  total_value: number;
  unrealized_pnl: number;
  position_count: number;
  cash_balance?: number | null;
}

interface PortfolioRisk {
  var_95: number;
  max_drawdown: number;
  current_drawdown: number;
  daily_pnl_pct: number;
  risk_status: string;
}

interface KillSwitchStatus {
  is_active: boolean;
  activated_at: string | null;
  activation_reason: string | null;
  message: string;
}

interface Notification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  message: string;
  timestamp: number;
}

interface SystemHealth {
  status: string;
  service: string;
}

// ── Granular loading & error tracking ──────────────────────────────

interface EndpointState {
  loading: boolean;
  error: string | null;
  lastUpdated: number | null;
}

type EndpointName =
  | "agents" | "portfolio" | "risk" | "positions"
  | "health" | "killSwitch";

// ── Real-time data from WebSocket ──────────────────────────────────

interface RealtimePrices {
  [symbol: string]: { price: number; change_24h: number };
}

interface RealtimeRegime {
  market: string;
  confidence: number;
}

interface RealtimeRisk {
  var_95: number;
  drawdown: number;
  kill_switch: boolean;
}

interface RealtimePortfolio {
  total_value: number;
  daily_pnl: number;
  positions: number;
  cash_balance?: number;
}

// ── Store Interface ────────────────────────────────────────────────

interface AppState {
  // UI state
  sidebarOpen: boolean;
  killSwitch: boolean;
  autoTrade: boolean;
  activeAgents: string[];
  selectedSymbol: string;
  selectedExchange: string;
  notifications: Notification[];

  // Data state
  agents: AgentInfo[];
  portfolio: PortfolioSummary | null;
  portfolioRisk: PortfolioRisk | null;
  positions: PositionInfo[];
  systemHealth: SystemHealth | null;
  killSwitchStatus: KillSwitchStatus | null;

  // WebSocket real-time data
  realtimePrices: RealtimePrices;
  realtimeRegime: RealtimeRegime | null;
  realtimeRisk: RealtimeRisk | null;
  realtimePortfolio: RealtimePortfolio | null;
  wsConnected: boolean;

  // Granular loading states
  loadingStates: Record<EndpointName, EndpointState>;

  // Aggregate loading
  globalLoading: boolean;

  // Actions — UI
  toggleSidebar: () => void;
  toggleKillSwitch: () => Promise<void>;
  toggleAutoTrade: () => void;
  setActiveAgents: (agents: string[]) => void;
  setSelectedSymbol: (symbol: string) => void;
  setSelectedExchange: (exchange: string) => void;
  addNotification: (notification: Notification) => void;
  clearNotifications: () => void;

  // Actions — WebSocket real-time updates
  updateRealtimePrices: (prices: RealtimePrices) => void;
  updateRealtimeRegime: (regime: RealtimeRegime) => void;
  updateRealtimeRisk: (risk: RealtimeRisk) => void;
  updateRealtimePortfolio: (portfolio: RealtimePortfolio) => void;
  setWsConnected: (connected: boolean) => void;

  // Actions — API calls
  fetchAgents: () => Promise<void>;
  fetchPortfolio: () => Promise<void>;
  fetchPortfolioRisk: () => Promise<void>;
  fetchPositions: () => Promise<void>;
  fetchHealth: () => Promise<void>;
  fetchKillSwitchStatus: () => Promise<void>;
  refreshAll: () => Promise<void>;
}

// ── Helpers ────────────────────────────────────────────────────────

const defaultEndpointState = (): EndpointState => ({
  loading: false,
  error: null,
  lastUpdated: null,
});

const MAX_NOTIFICATIONS = 50;

// ── Store ──────────────────────────────────────────────────────────

export const useAppStore = create<AppState>((set, get) => ({
  // ── Initial UI state ──────────────────────────────────────────
  sidebarOpen: true,
  killSwitch: false,
  autoTrade: false,
  activeAgents: [],
  selectedSymbol: "EURUSD",
  selectedExchange: "mt5",
  notifications: [],

  // ── Initial data state ────────────────────────────────────────
  agents: [],
  portfolio: null,
  portfolioRisk: null,
  positions: [],
  systemHealth: null,
  killSwitchStatus: null,

  // ── Initial real-time state ───────────────────────────────────
  realtimePrices: {},
  realtimeRegime: null,
  realtimeRisk: null,
  realtimePortfolio: null,
  wsConnected: false,

  // ── Initial loading states ────────────────────────────────────
  loadingStates: {
    agents: defaultEndpointState(),
    portfolio: defaultEndpointState(),
    risk: defaultEndpointState(),
    positions: defaultEndpointState(),
    health: defaultEndpointState(),
    killSwitch: defaultEndpointState(),
  },

  globalLoading: false,

  // ── UI Actions ────────────────────────────────────────────────
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleKillSwitch: async () => {
    const current = get().killSwitch;
    set((s) => ({
      loadingStates: {
        ...s.loadingStates,
        killSwitch: { ...s.loadingStates.killSwitch, loading: true, error: null },
      },
    }));
    try {
      const data = current
        ? await agentsApi.resetKillSwitch()
        : await agentsApi.activateKillSwitch("MANUAL");
      set((s) => ({
        killSwitch: data.is_active,
        killSwitchStatus: {
          is_active: data.is_active,
          activated_at: data.activated_at ?? null,
          activation_reason: data.activation_reason ?? null,
          message: data.message ?? "",
        },
        loadingStates: {
          ...s.loadingStates,
          killSwitch: { loading: false, error: null, lastUpdated: Date.now() },
        },
      }));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to toggle kill switch";
      set((s) => ({
        loadingStates: {
          ...s.loadingStates,
          killSwitch: {
            loading: false,
            error: message,
            lastUpdated: s.loadingStates.killSwitch.lastUpdated,
          },
        },
      }));
      get().addNotification({
        id: `killswitch-error-${Date.now()}`,
        type: "error",
        message,
        timestamp: Date.now(),
      });
    }
  },
  toggleAutoTrade: () => set((s) => ({ autoTrade: !s.autoTrade })),
  setActiveAgents: (agents) => set({ activeAgents: agents }),
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setSelectedExchange: (exchange) => set({ selectedExchange: exchange }),

  addNotification: (notification) =>
    set((s) => ({
      notifications: [
        ...s.notifications.slice(-(MAX_NOTIFICATIONS - 1)),
        notification,
      ],
    })),

  clearNotifications: () => set({ notifications: [] }),

  // ── WebSocket real-time actions ───────────────────────────────
  updateRealtimePrices: (prices) =>
    set((s) => ({
      realtimePrices: { ...s.realtimePrices, ...prices },
    })),

  updateRealtimeRegime: (regime) =>
    set({ realtimeRegime: regime }),

  updateRealtimeRisk: (risk) =>
    set({
      realtimeRisk: risk,
      // Auto-update kill switch from WS data
      killSwitch: risk.kill_switch,
    }),

  updateRealtimePortfolio: (portfolio) =>
    set({
      realtimePortfolio: portfolio,
      // Auto-derive portfolio summary from WS data. cash_balance only when
      // the backend actually reports it — never fabricate a split.
      portfolio: portfolio
        ? {
            total_value: portfolio.total_value,
            unrealized_pnl: portfolio.daily_pnl,
            position_count: portfolio.positions,
            ...(portfolio.cash_balance !== undefined && {
              cash_balance: portfolio.cash_balance,
            }),
          }
        : get().portfolio,
    }),

  setWsConnected: (connected) => set({ wsConnected: connected }),

  // ── API actions with granular loading/error tracking ──────────
  fetchAgents: async () => {
    set((s) => ({
      loadingStates: {
        ...s.loadingStates,
        agents: { ...s.loadingStates.agents, loading: true, error: null },
      },
    }));
    try {
      const data = await apiRequest<{ agents: AgentInfo[]; kill_switch_active: boolean }>(
        "/api/agents/status",
      );
      set((s) => ({
        agents: data.agents || [],
        killSwitch: data.kill_switch_active,
        loadingStates: {
          ...s.loadingStates,
          agents: { loading: false, error: null, lastUpdated: Date.now() },
        },
      }));
    } catch (err) {
      set((s) => ({
        loadingStates: {
          ...s.loadingStates,
          agents: {
            loading: false,
            error: err instanceof Error ? err.message : "Failed to load agents",
            lastUpdated: s.loadingStates.agents.lastUpdated,
          },
        },
      }));
    }
  },

  fetchPortfolio: async () => {
    set((s) => ({
      loadingStates: {
        ...s.loadingStates,
        portfolio: { ...s.loadingStates.portfolio, loading: true, error: null },
      },
    }));
    try {
      const data = await apiRequest<PortfolioSummary>("/api/portfolio/summary");
      set((s) => ({
        portfolio: {
          total_value: data.total_value || 0,
          unrealized_pnl: data.unrealized_pnl || 0,
          position_count: data.position_count || 0,
          cash_balance: data.cash_balance || 0,
        },
        loadingStates: {
          ...s.loadingStates,
          portfolio: { loading: false, error: null, lastUpdated: Date.now() },
        },
      }));
    } catch (err) {
      set((s) => ({
        loadingStates: {
          ...s.loadingStates,
          portfolio: {
            loading: false,
            error: err instanceof Error ? err.message : "Failed to load portfolio",
            lastUpdated: s.loadingStates.portfolio.lastUpdated,
          },
        },
      }));
    }
  },

  fetchPortfolioRisk: async () => {
    set((s) => ({
      loadingStates: {
        ...s.loadingStates,
        risk: { ...s.loadingStates.risk, loading: true, error: null },
      },
    }));
    try {
      const data = await apiRequest<PortfolioRisk>("/api/portfolio/risk");
      set((s) => ({
        portfolioRisk: {
          var_95: data.var_95 || 0,
          max_drawdown: data.max_drawdown || 0,
          current_drawdown: data.current_drawdown || 0,
          daily_pnl_pct: data.daily_pnl_pct || 0,
          risk_status: data.risk_status || "unknown",
        },
        loadingStates: {
          ...s.loadingStates,
          risk: { loading: false, error: null, lastUpdated: Date.now() },
        },
      }));
    } catch (err) {
      set((s) => ({
        loadingStates: {
          ...s.loadingStates,
          risk: {
            loading: false,
            error: err instanceof Error ? err.message : "Failed to load risk",
            lastUpdated: s.loadingStates.risk.lastUpdated,
          },
        },
      }));
    }
  },

  fetchPositions: async () => {
    set((s) => ({
      loadingStates: {
        ...s.loadingStates,
        positions: { ...s.loadingStates.positions, loading: true, error: null },
      },
    }));
    try {
      const data = await apiRequest<{ positions: PositionInfo[] }>("/api/trading/positions");
      set((s) => ({
        positions: data.positions || [],
        loadingStates: {
          ...s.loadingStates,
          positions: { loading: false, error: null, lastUpdated: Date.now() },
        },
      }));
    } catch (err) {
      set((s) => ({
        loadingStates: {
          ...s.loadingStates,
          positions: {
            loading: false,
            error: err instanceof Error ? err.message : "Failed to load positions",
            lastUpdated: s.loadingStates.positions.lastUpdated,
          },
        },
      }));
    }
  },

  fetchHealth: async () => {
    set((s) => ({
      loadingStates: {
        ...s.loadingStates,
        health: { ...s.loadingStates.health, loading: true, error: null },
      },
    }));
    try {
      const data = await apiRequest<{ status: string; service: string }>("/health");
      set((s) => ({
        systemHealth: { status: data.status, service: data.service },
        loadingStates: {
          ...s.loadingStates,
          health: { loading: false, error: null, lastUpdated: Date.now() },
        },
      }));
    } catch (err) {
      set((s) => ({
        loadingStates: {
          ...s.loadingStates,
          health: {
            loading: false,
            error: err instanceof Error ? err.message : "Failed to load health",
            lastUpdated: s.loadingStates.health.lastUpdated,
          },
        },
      }));
    }
  },

  fetchKillSwitchStatus: async () => {
    set((s) => ({
      loadingStates: {
        ...s.loadingStates,
        killSwitch: { ...s.loadingStates.killSwitch, loading: true, error: null },
      },
    }));
    try {
      const data = await apiRequest<KillSwitchStatus>("/api/agents/kill-switch/status");
      set((s) => ({
        killSwitchStatus: {
          is_active: data.is_active,
          activated_at: data.activated_at,
          activation_reason: data.activation_reason,
          message: data.message,
        },
        killSwitch: data.is_active,
        loadingStates: {
          ...s.loadingStates,
          killSwitch: { loading: false, error: null, lastUpdated: Date.now() },
        },
      }));
    } catch (err) {
      set((s) => ({
        loadingStates: {
          ...s.loadingStates,
          killSwitch: {
            loading: false,
            error: err instanceof Error ? err.message : "Failed to load kill switch",
            lastUpdated: s.loadingStates.killSwitch.lastUpdated,
          },
        },
      }));
    }
  },

  // ── Refresh all with parallel execution ──────────────────────
  refreshAll: async () => {
    set({ globalLoading: true });
    await Promise.allSettled([
      get().fetchAgents(),
      get().fetchPortfolio(),
      get().fetchPortfolioRisk(),
      get().fetchPositions(),
      get().fetchHealth(),
      get().fetchKillSwitchStatus(),
    ]);
    set({ globalLoading: false });
  },
}));
