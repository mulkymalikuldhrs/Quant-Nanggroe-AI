import { create } from "zustand";
import {
  agentsApi,
  portfolioApi,
  backtestApi,
  riskApi,
  type AgentListResponse,
  type PortfolioResponse,
  type BacktestResponse,
  type RiskCheckResponse,
} from "./api-client";

interface Notification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  message: string;
  timestamp: number;
}

interface LoadingState {
  agents: boolean;
  portfolio: boolean;
  backtest: boolean;
  risk: boolean;
}

interface ErrorState {
  agents: string | null;
  portfolio: string | null;
  backtest: string | null;
  risk: string | null;
}

interface AppState {
  sidebarOpen: boolean;
  killSwitch: boolean;
  activeAgents: string[];
  selectedSymbol: string;
  selectedExchange: string;
  notifications: Notification[];
  toggleSidebar: () => void;
  toggleKillSwitch: () => void;
  setActiveAgents: (agents: string[]) => void;
  setSelectedSymbol: (symbol: string) => void;
  setSelectedExchange: (exchange: string) => void;
  addNotification: (notification: Notification) => void;
  clearNotifications: () => void;
  agentsData: AgentListResponse | null;
  portfolioData: PortfolioResponse | null;
  backtestResult: BacktestResponse | null;
  riskData: Record<string, RiskCheckResponse>;
  loading: LoadingState;
  errors: ErrorState;
  fetchAgents: () => Promise<void>;
  fetchPortfolio: () => Promise<void>;
  runBacktest: (config: { strategy: string; symbols?: string[]; period?: string }) => Promise<void>;
  fetchRisk: (symbol: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  sidebarOpen: true,
  killSwitch: false,
  activeAgents: [],
  selectedSymbol: "BTC",
  selectedExchange: "binance",
  notifications: [],
  agentsData: null,
  portfolioData: null,
  backtestResult: null,
  riskData: {},
  loading: { agents: false, portfolio: false, backtest: false, risk: false },
  errors: { agents: null, portfolio: null, backtest: null, risk: null },
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleKillSwitch: () => set((state) => ({ killSwitch: !state.killSwitch })),
  setActiveAgents: (agents) => set({ activeAgents: agents }),
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setSelectedExchange: (exchange) => set({ selectedExchange: exchange }),
  addNotification: (notification) =>
    set((state) => ({
      notifications: [...state.notifications, notification],
    })),
  clearNotifications: () => set({ notifications: [] }),
  fetchAgents: async () => {
    set((state) => ({ loading: { ...state.loading, agents: true }, errors: { ...state.errors, agents: null } }));
    try {
      const data = await agentsApi.getStatus();
      set({ agentsData: data, loading: { ...get().loading, agents: false } });
    } catch (err) {
      set({ errors: { ...get().errors, agents: (err as Error).message }, loading: { ...get().loading, agents: false } });
    }
  },
  fetchPortfolio: async () => {
    set((state) => ({ loading: { ...state.loading, portfolio: true }, errors: { ...state.errors, portfolio: null } }));
    try {
      const data = await portfolioApi.getSummary();
      set({ portfolioData: data, loading: { ...get().loading, portfolio: false } });
    } catch (err) {
      set({ errors: { ...get().errors, portfolio: (err as Error).message }, loading: { ...get().loading, portfolio: false } });
    }
  },
  runBacktest: async (config) => {
    set((state) => ({ loading: { ...state.loading, backtest: true }, errors: { ...state.errors, backtest: null } }));
    try {
      const data = await backtestApi.run(config);
      set({ backtestResult: data, loading: { ...get().loading, backtest: false } });
    } catch (err) {
      set({ errors: { ...get().errors, backtest: (err as Error).message }, loading: { ...get().loading, backtest: false } });
    }
  },
  fetchRisk: async (symbol) => {
    set((state) => ({ loading: { ...state.loading, risk: true }, errors: { ...state.errors, risk: null } }));
    try {
      const data = await riskApi.getAssessment(symbol);
      set({ riskData: { ...get().riskData, [symbol]: data }, loading: { ...get().loading, risk: false } });
    } catch (err) {
      set({ errors: { ...get().errors, risk: (err as Error).message }, loading: { ...get().loading, risk: false } });
    }
  },
}));
