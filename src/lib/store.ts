import { create } from "zustand";
import { apiClient } from "./api-client";

// ══════════════════════════════════════════════════════════════════════
// Types
// ══════════════════════════════════════════════════════════════════════

export interface AgentInfo {
  name: string;
  role: string;
  registered: boolean;
  status: "active" | "idle" | "error" | "offline";
}

export interface PositionInfo {
  ticker: string;
  amount: number;
  avg_price: number;
  current_price: number;
  pnl: number;
  last_updated?: string;
}

export interface TradeInfo {
  id: string;
  timestamp: string;
  ticker: string;
  action: string;
  amount: number;
  price: number;
  total_value: number;
  fees: number;
  realized_pnl: number | null;
}

export interface BacktestSummary {
  id: string;
  status: string;
  symbol: string;
  strategy: string;
}

export interface BacktestResult {
  backtest_id: string;
  status: string;
  symbol: string;
  strategy: string;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  avg_trade_pnl: number;
  avg_win: number;
  avg_loss: number;
  equity_curve: number[];
  error: string | null;
}

export interface PortfolioSummary {
  total_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  positions: PositionInfo[];
  position_count: number;
  cash_balance: number;
  timestamp: string;
}

export interface PortfolioRisk {
  var_95: number;
  cvar_95: number;
  max_drawdown: number;
  current_drawdown: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  daily_pnl_pct: number;
  weekly_pnl_pct: number;
  daily_trades: number;
  risk_status: string;
  timestamp: string;
}

export interface SystemHealth {
  status: string;
  service: string;
  database?: string;
  redis?: string;
}

export interface OHLCVCandle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PressureData {
  symbol: string;
  buy_pressure: number;
  sell_pressure: number;
  bid_volume: number;
  ask_volume: number;
  spread: number;
  mid_price: number;
  verdict: string;
  timestamp: string;
}

export interface KillSwitchStatus {
  is_active: boolean;
  activated_at: string | null;
  activation_reason: string | null;
  auto_triggers: number;
  manual_triggers: number;
  total_resets: number;
  message: string;
}

export interface StressTestResult {
  scenarios: Record<
    string,
    {
      description: string;
      portfolio_value_pre: number;
      estimated_loss: number;
      loss_pct: number;
      portfolio_value_post: number;
      p95_loss: number;
      p99_loss: number;
    }
  >;
  summary: {
    portfolio_value: number;
    worst_scenario: string;
    worst_case_loss_pct: number;
    total_scenarios: number;
  };
  timestamp: string;
}

// ══════════════════════════════════════════════════════════════════════
// Store State & Actions
// ══════════════════════════════════════════════════════════════════════

interface AppState {
  // UI State
  sidebarOpen: boolean;
  activePage: string;
  wsConnected: boolean;

  // Data State
  agents: AgentInfo[];
  portfolio: PortfolioSummary | null;
  portfolioRisk: PortfolioRisk | null;
  positions: PositionInfo[];
  trades: TradeInfo[];
  backtests: BacktestSummary[];
  backtestResult: BacktestResult | null;
  systemHealth: SystemHealth | null;
  killSwitch: KillSwitchStatus | null;
  stressTest: StressTestResult | null;
  ohlcvData: OHLCVCandle[];
  pressureData: PressureData | null;

  // Loading States
  loadingAgents: boolean;
  loadingPortfolio: boolean;
  loadingPortfolioRisk: boolean;
  loadingPositions: boolean;
  loadingTrades: boolean;
  loadingBacktests: boolean;
  loadingBacktestResult: boolean;
  loadingHealth: boolean;
  loadingKillSwitch: boolean;
  loadingStressTest: boolean;
  loadingOHLCV: boolean;
  loadingPressure: boolean;

  // Error States
  errorAgents: string | null;
  errorPortfolio: string | null;
  errorPortfolioRisk: string | null;
  errorPositions: string | null;
  errorTrades: string | null;
  errorBacktests: string | null;
  errorBacktestResult: string | null;
  errorHealth: string | null;
  errorKillSwitch: string | null;
  errorStressTest: string | null;
  errorOHLCV: string | null;
  errorPressure: string | null;

  // Event feed
  eventFeed: Array<{
    id: string;
    type: string;
    message: string;
    timestamp: string;
    severity: string;
  }>;

  // Actions — UI
  toggleSidebar: () => void;
  setActivePage: (page: string) => void;
  setWsConnected: (connected: boolean) => void;
  addEvent: (event: {
    id: string;
    type: string;
    message: string;
    timestamp: string;
    severity: string;
  }) => void;
  clearEvents: () => void;

  // Actions — Data Fetching
  fetchAgents: () => Promise<void>;
  fetchPortfolio: () => Promise<void>;
  fetchPortfolioRisk: () => Promise<void>;
  fetchPositions: () => Promise<void>;
  fetchTrades: (limit?: number) => Promise<void>;
  fetchBacktests: () => Promise<void>;
  fetchBacktestResult: (id: string) => Promise<void>;
  fetchHealth: () => Promise<void>;
  fetchKillSwitch: () => Promise<void>;
  fetchStressTest: () => Promise<void>;
  fetchOHLCV: (symbol: string, timeframe?: string, limit?: number) => Promise<void>;
  fetchPressure: (symbol: string) => Promise<void>;

  // Actions — Mutations
  placeOrder: (data: {
    symbol: string;
    direction: string;
    quantity: number;
    order_type?: string;
    price?: number;
    stop_loss?: number;
    take_profit?: number;
  }) => Promise<{ order_id: string; status: string } | null>;
  runAgent: (data: {
    symbol: string;
    query?: string;
    timeframe?: string;
  }) => Promise<{ status: string; decision_action: string } | null>;
  submitBacktest: (data: {
    symbol: string;
    strategy: string;
    start_date: string;
    end_date: string;
    initial_capital?: number;
    commission?: number;
    slippage?: number;
  }) => Promise<string | null>;
  activateKillSwitch: (reason?: string) => Promise<boolean>;
  resetKillSwitch: () => Promise<boolean>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // UI State
  sidebarOpen: true,
  activePage: "dashboard",
  wsConnected: false,

  // Data State
  agents: [],
  portfolio: null,
  portfolioRisk: null,
  positions: [],
  trades: [],
  backtests: [],
  backtestResult: null,
  systemHealth: null,
  killSwitch: null,
  stressTest: null,
  ohlcvData: [],
  pressureData: null,

  // Loading States
  loadingAgents: false,
  loadingPortfolio: false,
  loadingPortfolioRisk: false,
  loadingPositions: false,
  loadingTrades: false,
  loadingBacktests: false,
  loadingBacktestResult: false,
  loadingHealth: false,
  loadingKillSwitch: false,
  loadingStressTest: false,
  loadingOHLCV: false,
  loadingPressure: false,

  // Error States
  errorAgents: null,
  errorPortfolio: null,
  errorPortfolioRisk: null,
  errorPositions: null,
  errorTrades: null,
  errorBacktests: null,
  errorBacktestResult: null,
  errorHealth: null,
  errorKillSwitch: null,
  errorStressTest: null,
  errorOHLCV: null,
  errorPressure: null,

  // Event Feed
  eventFeed: [],

  // UI Actions
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setActivePage: (page) => set({ activePage: page }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  addEvent: (event) =>
    set((s) => ({
      eventFeed: [event, ...s.eventFeed].slice(0, 100),
    })),
  clearEvents: () => set({ eventFeed: [] }),

  // Data Fetching
  fetchAgents: async () => {
    set({ loadingAgents: true, errorAgents: null });
    try {
      const result = await apiClient.getAgentStatus();
      const agents: AgentInfo[] = (result.agents || []).map((a) => ({
        ...a,
        status: a.registered ? "active" : "offline",
      }));
      set({ agents, loadingAgents: false });
    } catch (err) {
      set({
        errorAgents: err instanceof Error ? err.message : "Failed to fetch agents",
        loadingAgents: false,
      });
    }
  },

  fetchPortfolio: async () => {
    set({ loadingPortfolio: true, errorPortfolio: null });
    try {
      const data = await apiClient.getPortfolioSummary();
      set({ portfolio: data, loadingPortfolio: false });
    } catch (err) {
      set({
        errorPortfolio: err instanceof Error ? err.message : "Failed to fetch portfolio",
        loadingPortfolio: false,
      });
    }
  },

  fetchPortfolioRisk: async () => {
    set({ loadingPortfolioRisk: true, errorPortfolioRisk: null });
    try {
      const data = await apiClient.getPortfolioRisk();
      set({ portfolioRisk: data, loadingPortfolioRisk: false });
    } catch (err) {
      set({
        errorPortfolioRisk: err instanceof Error ? err.message : "Failed to fetch risk",
        loadingPortfolioRisk: false,
      });
    }
  },

  fetchPositions: async () => {
    set({ loadingPositions: true, errorPositions: null });
    try {
      const data = await apiClient.getPositions();
      set({ positions: data.positions || [], loadingPositions: false });
    } catch (err) {
      set({
        errorPositions: err instanceof Error ? err.message : "Failed to fetch positions",
        loadingPositions: false,
      });
    }
  },

  fetchTrades: async (limit = 50) => {
    set({ loadingTrades: true, errorTrades: null });
    try {
      const data = await apiClient.getTradeHistory(limit);
      set({ trades: data.trades || [], loadingTrades: false });
    } catch (err) {
      set({
        errorTrades: err instanceof Error ? err.message : "Failed to fetch trades",
        loadingTrades: false,
      });
    }
  },

  fetchBacktests: async () => {
    set({ loadingBacktests: true, errorBacktests: null });
    try {
      const data = await apiClient.listBacktests();
      set({ backtests: data.backtests || [], loadingBacktests: false });
    } catch (err) {
      set({
        errorBacktests: err instanceof Error ? err.message : "Failed to fetch backtests",
        loadingBacktests: false,
      });
    }
  },

  fetchBacktestResult: async (id: string) => {
    set({ loadingBacktestResult: true, errorBacktestResult: null });
    try {
      const data = await apiClient.getBacktestResult(id);
      set({ backtestResult: data, loadingBacktestResult: false });
    } catch (err) {
      set({
        errorBacktestResult: err instanceof Error ? err.message : "Failed to fetch result",
        loadingBacktestResult: false,
      });
    }
  },

  fetchHealth: async () => {
    set({ loadingHealth: true, errorHealth: null });
    try {
      const data = await apiClient.getHealth();
      set({ systemHealth: data, loadingHealth: false });
    } catch (err) {
      set({
        errorHealth: err instanceof Error ? err.message : "Failed to fetch health",
        loadingHealth: false,
      });
    }
  },

  fetchKillSwitch: async () => {
    set({ loadingKillSwitch: true, errorKillSwitch: null });
    try {
      const data = await apiClient.getKillSwitchStatus();
      set({ killSwitch: data, loadingKillSwitch: false });
    } catch (err) {
      set({
        errorKillSwitch: err instanceof Error ? err.message : "Failed",
        loadingKillSwitch: false,
      });
    }
  },

  fetchStressTest: async () => {
    set({ loadingStressTest: true, errorStressTest: null });
    try {
      const data = await apiClient.runStressTest();
      set({ stressTest: data, loadingStressTest: false });
    } catch (err) {
      set({
        errorStressTest: err instanceof Error ? err.message : "Failed",
        loadingStressTest: false,
      });
    }
  },

  fetchOHLCV: async (symbol: string, timeframe = "1d", limit = 100) => {
    set({ loadingOHLCV: true, errorOHLCV: null });
    try {
      const data = await apiClient.getOHLCV({ symbol, timeframe, limit });
      set({ ohlcvData: data.data || [], loadingOHLCV: false });
    } catch (err) {
      set({
        errorOHLCV: err instanceof Error ? err.message : "Failed",
        loadingOHLCV: false,
      });
    }
  },

  fetchPressure: async (symbol: string) => {
    set({ loadingPressure: true, errorPressure: null });
    try {
      const data = await apiClient.getPressure(symbol);
      set({ pressureData: data, loadingPressure: false });
    } catch (err) {
      set({
        errorPressure: err instanceof Error ? err.message : "Failed",
        loadingPressure: false,
      });
    }
  },

  // Mutations
  placeOrder: async (data) => {
    try {
      const result = await apiClient.placeOrder(data);
      get().addEvent({
        id: `order-${Date.now()}`,
        type: "order",
        message: `Order ${result.status}: ${result.direction} ${result.quantity} ${result.symbol}`,
        timestamp: new Date().toISOString(),
        severity: result.status === "FILLED" ? "success" : "warning",
      });
      // Refresh positions after order
      get().fetchPositions();
      get().fetchPortfolio();
      return result;
    } catch (err) {
      get().addEvent({
        id: `order-err-${Date.now()}`,
        type: "error",
        message: `Order failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
        severity: "error",
      });
      return null;
    }
  },

  runAgent: async (data) => {
    try {
      const result = await apiClient.runAgent(data);
      get().addEvent({
        id: `agent-${Date.now()}`,
        type: "agent",
        message: `Agent run ${result.status}: ${result.decision_action || "No action"} for ${result.symbol}`,
        timestamp: new Date().toISOString(),
        severity: result.status === "completed" ? "success" : "warning",
      });
      return result;
    } catch (err) {
      get().addEvent({
        id: `agent-err-${Date.now()}`,
        type: "error",
        message: `Agent run failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
        severity: "error",
      });
      return null;
    }
  },

  submitBacktest: async (data) => {
    try {
      const result = await apiClient.submitBacktest(data);
      get().addEvent({
        id: `bt-${Date.now()}`,
        type: "backtest",
        message: `Backtest queued: ${result.strategy} on ${result.symbol}`,
        timestamp: new Date().toISOString(),
        severity: "info",
      });
      get().fetchBacktests();
      return result.backtest_id;
    } catch (err) {
      get().addEvent({
        id: `bt-err-${Date.now()}`,
        type: "error",
        message: `Backtest failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
        severity: "error",
      });
      return null;
    }
  },

  activateKillSwitch: async (reason) => {
    try {
      await apiClient.activateKillSwitch(reason);
      get().fetchKillSwitch();
      get().addEvent({
        id: `ks-${Date.now()}`,
        type: "kill_switch",
        message: "KILL SWITCH ACTIVATED — All trading halted",
        timestamp: new Date().toISOString(),
        severity: "error",
      });
      return true;
    } catch {
      return false;
    }
  },

  resetKillSwitch: async () => {
    try {
      await apiClient.resetKillSwitch();
      get().fetchKillSwitch();
      get().addEvent({
        id: `ks-reset-${Date.now()}`,
        type: "kill_switch",
        message: "Kill switch reset — Trading resumed",
        timestamp: new Date().toISOString(),
        severity: "success",
      });
      return true;
    } catch {
      return false;
    }
  },
}));
