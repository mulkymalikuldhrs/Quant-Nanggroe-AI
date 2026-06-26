import { create } from "zustand";
import apiRequest from "./api-client";

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
  cash_balance: number;
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

interface AppState {
  // UI state
  sidebarOpen: boolean;
  killSwitch: boolean;
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
  
  // Loading state
  loading: boolean;
  
  // Actions
  toggleSidebar: () => void;
  toggleKillSwitch: () => void;
  setActiveAgents: (agents: string[]) => void;
  setSelectedSymbol: (symbol: string) => void;
  setSelectedExchange: (exchange: string) => void;
  addNotification: (notification: Notification) => void;
  clearNotifications: () => void;
  
  // API actions
  fetchAgents: () => Promise<void>;
  fetchPortfolio: () => Promise<void>;
  fetchPortfolioRisk: () => Promise<void>;
  fetchPositions: () => Promise<void>;
  fetchHealth: () => Promise<void>;
  fetchKillSwitchStatus: () => Promise<void>;
  refreshAll: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  sidebarOpen: true,
  killSwitch: false,
  activeAgents: [],
  selectedSymbol: "BTC",
  selectedExchange: "binance",
  notifications: [],
  
  agents: [],
  portfolio: null,
  portfolioRisk: null,
  positions: [],
  systemHealth: null,
  killSwitchStatus: null,
  
  loading: false,
  
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleKillSwitch: () => set((s) => ({ killSwitch: !s.killSwitch })),
  setActiveAgents: (agents) => set({ activeAgents: agents }),
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setSelectedExchange: (exchange) => set({ selectedExchange: exchange }),
  addNotification: (notification) =>
    set((s) => ({ notifications: [...s.notifications, notification] })),
  clearNotifications: () => set({ notifications: [] }),
  
  fetchAgents: async () => {
    try {
      const data: any = await apiRequest("/api/agents/status");
      set({ agents: data.agents || [], killSwitch: data.kill_switch_active });
    } catch {}
  },

  fetchPortfolio: async () => {
    try {
      const data: any = await apiRequest("/api/portfolio/summary");
      set({ portfolio: {
        total_value: data.total_value,
        unrealized_pnl: data.unrealized_pnl,
        position_count: data.position_count,
        cash_balance: data.cash_balance,
      }});
    } catch {}
  },

  fetchPortfolioRisk: async () => {
    try {
      const data: any = await apiRequest("/api/portfolio/risk");
      set({ portfolioRisk: {
        var_95: data.var_95,
        max_drawdown: data.max_drawdown,
        current_drawdown: data.current_drawdown,
        daily_pnl_pct: data.daily_pnl_pct,
        risk_status: data.risk_status,
      }});
    } catch {}
  },

  fetchPositions: async () => {
    try {
      const data: any = await apiRequest("/api/trading/positions");
      set({ positions: data.positions || [] });
    } catch {}
  },

  fetchHealth: async () => {
    try {
      const data: any = await apiRequest("/health");
      set({ systemHealth: { status: data.status, service: data.service } });
    } catch {}
  },

  fetchKillSwitchStatus: async () => {
    try {
      const data: any = await apiRequest("/api/agents/kill-switch/status");
      set({ killSwitchStatus: {
        is_active: data.is_active,
        activated_at: data.activated_at,
        activation_reason: data.activation_reason,
        message: data.message,
      }});
    } catch {}
  },
  
  refreshAll: async () => {
    set({ loading: true });
    await Promise.allSettled([
      get().fetchAgents(),
      get().fetchPortfolio(),
      get().fetchPortfolioRisk(),
      get().fetchPositions(),
      get().fetchHealth(),
      get().fetchKillSwitchStatus(),
    ]);
    set({ loading: false });
  },
}));
