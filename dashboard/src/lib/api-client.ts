const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    throw error;
  }
}

export interface TradeRequest {
  symbols: string[];
  provider?: string;
  deep_model?: string;
  quick_model?: string;
  trade_date?: string;
  paper?: boolean;
  metadata?: Record<string, unknown>;
}

export interface TradeResponse {
  status: string;
  symbols: string[];
  trade_date: string;
  confidence: number;
  risk_verdict: string;
  decisions: Record<string, unknown>[];
  signals: Record<string, unknown>[];
  agent_outputs: Record<string, unknown>;
  error?: string;
  timestamp: string;
}

export interface AgentInfo {
  name: string;
  role: string;
  description: string;
  status: string;
  tools: string[];
}

export interface AgentListResponse {
  agents: AgentInfo[];
  total: number;
}

export interface BacktestRequest {
  strategy: string;
  symbols?: string[];
  period?: string;
  initial_capital?: number;
  commission?: number;
  slippage?: number;
  market?: string;
}

export interface BacktestMetrics {
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_trade_pnl: number;
}

export interface BacktestResponse {
  status: string;
  strategy: string;
  symbols: string[];
  period: string;
  initial_capital: number;
  final_equity: number;
  metrics: BacktestMetrics;
  equity_curve_sample: number[];
  error?: string;
  timestamp: string;
}

export interface PositionInfo {
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  direction: string;
}

export interface PortfolioResponse {
  total_value: number;
  cash: number;
  positions: PositionInfo[];
  unrealized_pnl: number;
  realized_pnl: number;
  daily_pnl: number;
  weekly_pnl: number;
  allocation: Record<string, number>;
  risk_budget_used: number;
  timestamp: string;
}

export interface RiskCheckResponse {
  symbol: string;
  verdict: string;
  risk_level: string;
  per_trade_risk_pct: number;
  daily_loss_pct: number;
  weekly_loss_pct: number;
  drawdown_pct: number;
  position_concentration_pct: number;
  var_95?: number;
  cvar_95?: number;
  approved: boolean;
  veto_reason?: string;
  constitutional_limits: Record<string, unknown>;
  suggested_position_size?: number;
  suggested_stop_loss?: number;
  suggested_take_profit?: number;
  timestamp: string;
}

export const agentsApi = {
  run: (symbol: string) =>
    apiRequest<TradeResponse>("/api/v1/trade", { method: "POST", body: { symbols: [symbol] } }),
  getStatus: () => apiRequest<AgentListResponse>("/api/v1/agents"),
};

export const backtestApi = {
  run: (config: BacktestRequest) =>
    apiRequest<BacktestResponse>("/api/v1/backtest", { method: "POST", body: config }),
};

export const tradingApi = {
  placeOrder: (order: Record<string, unknown>) =>
    apiRequest<unknown>("/api/v1/trade", { method: "POST", body: { symbols: [order.symbol as string], ...order } }),
};

export const marketApi = {
  getPrice: (symbol: string) => apiRequest<unknown>(`/api/v1/risk/${symbol}`),
  getSentiment: () => apiRequest<unknown>("/api/v1/risk/BTC"),
};

export const portfolioApi = {
  getSummary: () => apiRequest<PortfolioResponse>("/api/v1/portfolio"),
};

export const riskApi = {
  getAssessment: (symbol: string) => apiRequest<RiskCheckResponse>(`/api/v1/risk/${symbol}`),
};

export default apiRequest;
