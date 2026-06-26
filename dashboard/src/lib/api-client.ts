const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, signal } = options;

  const config: RequestInit = {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    signal,
  };

  if (body) config.body = JSON.stringify(body);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  config.signal = controller.signal;

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    clearTimeout(timeout);
    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      throw new ApiError(`API Error: ${response.status} ${response.statusText}`, response.status, errorBody);
    }
    return response.json();
  } catch (error) {
    clearTimeout(timeout);
    if (error instanceof ApiError) throw error;
    throw new ApiError(error instanceof Error ? error.message : "Unknown error", 0, null);
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export const agentsApi = {
  run: (req: AgentRunRequest) => apiRequest<AgentRunResponse>("/api/agents/run", { method: "POST", body: req }),
  getStatus: () => apiRequest<AgentStatusResponse>("/api/agents/status"),
  getDecisions: () => apiRequest<Decision[]>("/api/agents/decisions"),
};

export const backtestApi = {
  run: (config: BacktestRunRequest) => apiRequest<{ id: string }>("/api/backtest/run", { method: "POST", body: config }),
  getResult: (id: string) => apiRequest<BacktestResult>(`/api/backtest/result/${id}`),
  getStrategies: () => apiRequest<Strategy[]>("/api/backtest/strategies"),
  getEngines: () => apiRequest<string[]>("/api/backtest/engines"),
  getFactors: () => apiRequest<FactorZoo[]>("/api/backtest/factors"),
};

export const tradingApi = {
  placeOrder: (req: PlaceOrderRequest) => apiRequest<PlaceOrderResponse>("/api/trading/order", { method: "POST", body: req }),
  getPositions: () => apiRequest<PositionsResponse>("/api/trading/positions"),
  getOrders: () => apiRequest<Order[]>("/api/trading/orders"),
  cancelOrder: (id: string) => apiRequest<{ success: boolean }>(`/api/trading/order/${id}`, { method: "DELETE" }),
  getExchanges: () => apiRequest<Exchange[]>("/api/trading/exchanges"),
};

export const marketApi = {
  getPrice: (symbol: string) => apiRequest<PriceResponse>(`/api/market/price/${symbol}`),
  getSentiment: () => apiRequest<MarketSentiment>("/api/market/sentiment"),
  getCandles: (symbol: string) => apiRequest<CandleStick[]>(`/api/market/candles/${symbol}`),
  getSignals: () => apiRequest<TradingSignal[]>("/api/market/signals"),
};

export const portfolioApi = {
  getSummary: () => apiRequest<PortfolioSummary>("/api/portfolio/summary"),
  getPerformance: () => apiRequest<PerformanceMetrics>("/api/portfolio/performance"),
  getEquityCurve: () => apiRequest<EquityCurveResponse>("/api/portfolio/equity-curve"),
  getRisk: () => apiRequest<RiskData>("/api/portfolio/risk"),
};

export const memoryApi = {
  search: (q: string, type?: string) => apiRequest<MemorySearchResponse>(`/api/memory/search?q=${encodeURIComponent(q)}${type ? `&type=${type}` : ""}`),
  store: (req: StoreMemoryRequest) => apiRequest<{ id: string }>("/api/memory/store", { method: "POST", body: req }),
  getEntry: (id: string) => apiRequest<MemoryEntry>(`/api/memory/entry/${id}`),
  deleteEntry: (id: string) => apiRequest<{ success: boolean }>(`/api/memory/entry/${id}`, { method: "DELETE" }),
};

export const colonyApi = {
  list: () => apiRequest<Colony[]>("/api/colony/list"),
  getDetail: (id: string) => apiRequest<ColonyDetail>(`/api/colony/${id}`),
  create: (req: ColonyCreateRequest) => apiRequest<Colony>("/api/colony/create", { method: "POST", body: req }),
  runTask: (id: string, task: string) => apiRequest<{ result: string }>(`/api/colony/${id}/run`, { method: "POST", body: { task } }),
};

export { ecosystemApi } from "./ecosystem";

export default apiRequest;

// ── Types ────────────────────────────────────────────────────────────

export type OrderSide = "buy" | "sell";
export type OrderType = "market" | "limit" | "stop" | "stop_limit";
export type OrderStatus = "pending" | "filled" | "active" | "canceled" | "rejected";
export type AgentStatus = "active" | "idle" | "warning" | "error" | "paused";
export type AgentEmotion = "curious" | "focused" | "confident" | "cautious" | "analytical" | "patient" | "excited" | "alert" | "thoughtful" | "neutral" | "decisive";
export type ExchangeType = "Equity" | "Crypto" | "Prediction" | "DeFi";
export type ExchangeStatus = "connected" | "disconnected" | "degraded";
export type ProviderStatus = "connected" | "disconnected" | "degraded";
export type ColonyStatus = "active" | "idle" | "degraded";
export type MemoryEntryType = "knowledge" | "session" | "vector" | "condenser" | "paging";
export type DecisionImpact = "high" | "medium" | "low";
export type RiskCheckStatus = "pass" | "warning" | "fail";

export interface MarketSymbol { symbol: string; price: number; change: number; volume: string; }
export interface SectorSentiment { name: string; sentiment: number; }
export interface MarketSentiment { overall: number; fear_greed: number; sectors: SectorSentiment[]; }
export interface PriceResponse { symbol: string; price: number; change: number; changePercent: number; timestamp: string; }
export interface CandleStick { time: string; open: number; high: number; low: number; close: number; }
export interface TradingSignal { id: number; time: string; agent: string; symbol: string; signal: "BUY" | "SELL" | "HOLD"; confidence: number; reason: string; }
export interface Order { id: string; symbol: string; side: OrderSide; type: OrderType; quantity: number; price: number; status: OrderStatus; time: string; exchange: string; }
export interface PlaceOrderRequest { symbol: string; side: OrderSide; type: OrderType; quantity: number; price?: number; stopPrice?: number; exchange?: string; }
export interface PlaceOrderResponse { orderId: string; status: OrderStatus; message: string; }
export interface Position { symbol: string; name: string; quantity: number; avgPrice: number; currentPrice: number; pnl: number; pnlPercent: number; weight: number; side: "long" | "short"; }
export interface PositionsResponse { positions: Position[]; }
export interface Exchange { id: string; name: string; type: ExchangeType; status: ExchangeStatus; }
export interface Agent { id: string; name: string; status: AgentStatus; emotion: AgentEmotion; action: string; lastDecision: string; icon: string; type?: string; }
export interface AgentRunRequest { symbol: string; agentId?: string; }
export interface AgentRunResponse { success: boolean; result: string; agentId: string; }
export interface AgentStatusResponse { agents: Agent[]; kill_switch_active: boolean; }
export interface Decision { id: number; time: string; agent: string; decision: string; impact: DecisionImpact; }
export interface EquityCurvePoint { date: string; value: number; }
export interface DrawdownCurvePoint { date: string; value: number; }
export interface MonteCarloResult { simulations: number; meanReturn: number; p5Return: number; p95Return: number; worstCase: number; bestCase: number; }
export interface BacktestResult { id: string; strategy: string; symbol: string; startDate: string; endDate: string; initialCapital: number; finalValue: number; totalReturn: number; sharpe: number; maxDrawdown: number; winRate: number; totalTrades: number; equityCurve: EquityCurvePoint[]; drawdownCurve: DrawdownCurvePoint[]; monteCarlo: MonteCarloResult; }
export interface BacktestRunRequest { strategy?: string; symbol?: string; startDate?: string; endDate?: string; initialCapital?: number; engine?: string; factors?: string[]; }
export interface Strategy { id: string; name: string; type: string; performance: number; sharpe: number; status: string; }
export interface FactorZoo { name: string; count: number; description: string; }
export interface PortfolioPosition { symbol: string; name: string; quantity: number; avgPrice: number; currentPrice: number; pnl: number; pnlPercent: number; weight: number; side: "long" | "short"; }
export interface AllocationBucket { name: string; value: number; color: string; }
export interface PortfolioSummary { totalValue: number; dayPnl: number; dayPnlPercent: number; totalPnl: number; totalPnlPercent: number; cashBalance: number; investedAmount: number; positions: PortfolioPosition[]; allocation: AllocationBucket[]; }
export interface PerformanceMetrics { sharpe: number; sortino: number; calmar: number; maxDrawdown: number; winRate: number; profitFactor: number; avgWin: number; avgLoss: number; totalTrades: number; avgHoldingPeriod: string; }
export interface EquityCurveResponse { points: EquityCurvePoint[]; }
export interface RiskCheck { id: number; name: string; status: RiskCheckStatus; value: string; limit: string; }
export interface RiskData { var95: number; var99: number; cvar95: number; maxDrawdown: number; currentDrawdown: number; kellyFraction: number; riskScore: number; checks: RiskCheck[]; correlationMatrix: number[][]; correlationLabels: string[]; }
export interface MemoryEntry { id: string; type: MemoryEntryType; key: string; content: string; timestamp: number; relevance: number; }
export interface StoreMemoryRequest { key: string; type: MemoryEntryType; content: string; }
export interface MemorySearchResponse { entries: MemoryEntry[]; total: number; }
export interface DataProvider { name: string; status: ProviderStatus; type: string; latency: string; }
export interface Colony { id: string; name: string; status: ColonyStatus; health: number; agents: number; capacity: number; schedule: string; }
export interface ColonyAgent { id: string; name: string; role: string; type: string; status: AgentStatus; lastActive: string; }
export interface ColonyDetail extends Colony { memberAgents: ColonyAgent[]; topology: string; }
export interface ColonyCreateRequest { name: string; description?: string; capacity?: number; schedule?: string; }
